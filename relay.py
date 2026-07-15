"""
TTSKit Relay — bridges HK FastAPI ↔ B200 GPU inference
Runs on Mac. Polls HK for pending TTS jobs, sends to B200, uploads WAV back.
"""
import time, json, os, subprocess, base64, tempfile, hashlib
from datetime import datetime

HK = "47.242.6.136"
HK_PW = "ZAQWSX123@@"
B200_CMD = "echo '{payload}' | python3 /home/sailin/tts_server.py"
JOB_DIR = "/opt/ttskit/jobs"
WAV_DIR = "/opt/ttskit/wav"

os.makedirs("ttskit_jobs", exist_ok=True)

def ssh_b200(cmd):
    """Send command to B200 via WSL tunnel"""
    inner = cmd.replace("'", "'\"'\"'")
    result = subprocess.run([
        "sshpass", "-p", "1234", "ssh", "-o", "StrictHostKeyChecking=no",
        "-p", "2222", "root@localhost",
        f"/mnt/c/Windows/System32/OpenSSH/ssh.exe -o StrictHostKeyChecking=no -i C:/Users/718265/gpu_key -p 7020 root@10.81.80.198 '{inner}'"
    ], capture_output=True, text=True, timeout=60)
    return result.stdout.strip()

def ssh_hk(cmd):
    """Send command to HK server"""
    result = subprocess.run([
        "sshpass", "-p", HK_PW, "ssh", "-o", "StrictHostKeyChecking=no",
        f"root@{HK}", cmd
    ], capture_output=True, text=True, timeout=30)
    return result.stdout.strip()

def run_job(job_id, text):
    """Process a single TTS job"""
    payload = json.dumps({"text": text})
    print(f"[{datetime.now()}] Processing job {job_id}: {text[:30]}...")
    
    raw = ssh_b200(f"cd /home/sailin/CosyVoice && {B200_CMD.format(payload=payload)}")
    
    # Extract JSON response - skip model loading logs
    for line in raw.split('\n'):
        line = line.strip()
        if line.startswith('{') and '"status"' in line:
            try:
                resp = json.loads(line)
                if resp.get('status') == 'ok':
                    wav_b64 = resp['wav_base64']
                    wav_data = base64.b64decode(wav_b64)
                    # Upload to HK
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                        f.write(wav_data)
                        wav_path = f.name
                    
                    result = subprocess.run([
                        "sshpass", "-p", HK_PW, "scp", "-o", "StrictHostKeyChecking=no",
                        wav_path, f"root@{HK}:{WAV_DIR}/{job_id}.wav"
                    ], capture_output=True, timeout=30)
                    os.unlink(wav_path)
                    
                    if result.returncode == 0:
                        # Mark job as done
                        ssh_hk(f"echo 'done' > {JOB_DIR}/{job_id}.status")
                        print(f"[{datetime.now()}] Job {job_id} COMPLETE")
                        return True
            except Exception as e:
                print(f"Parse error: {e}")
    
    # Mark failed
    ssh_hk(f"echo 'failed' > {JOB_DIR}/{job_id}.status")
    print(f"[{datetime.now()}] Job {job_id} FAILED")
    return False

def main():
    print(f"[{datetime.now()}] TTSKit Relay started")
    print(f"  HK: {HK}")
    print(f"  B200: 10.81.80.198 (via WSL tunnel)")
    print()
    
    while True:
        # List pending jobs
        jobs = ssh_hk(f"ls {JOB_DIR}/*.job 2>/dev/null || echo 'none'")
        
        if jobs.strip() == 'none' or not jobs.strip():
            time.sleep(2)
            continue
        
        for job_file in jobs.strip().split('\n'):
            job_file = job_file.strip()
            if not job_file:
                continue
            job_id = job_file.split('/')[-1].replace('.job', '')
            
            # Check if already processing
            status = ssh_hk(f"cat {JOB_DIR}/{job_id}.status 2>/dev/null || echo 'none'")
            if status.strip() != 'none':
                continue
            
            ssh_hk(f"echo 'processing' > {JOB_DIR}/{job_id}.status")
            
            # Read job text
            text = ssh_hk(f"cat {job_file}")
            if text:
                run_job(job_id, text)
        
        time.sleep(3)

if __name__ == "__main__":
    main()
