"""
TTSKit Relay v2 — file-based queue between HK and B200 daemon
"""
import time, json, os, subprocess, base64, tempfile, uuid

HK = "47.242.6.136"
HK_PW = "ZAQWSX123@@"

B200_REQ = "/tmp/tts_reqs"
B200_RES = "/tmp/tts_res"
HK_JOBS = "/opt/ttskit/jobs"
HK_WAV = "/opt/ttskit/wav"

def ssh_b200(cmd):
    inner = cmd.replace("'", "'\"'\"'")
    return subprocess.run([
        "sshpass", "-p", "1234", "ssh", "-o", "StrictHostKeyChecking=no",
        "-p", "2222", "root@localhost",
        f"/mnt/c/Windows/System32/OpenSSH/ssh.exe -o StrictHostKeyChecking=no -i C:/Users/718265/gpu_key -p 7020 root@10.81.80.198 '{inner}'"
    ], capture_output=True, text=True, timeout=30).stdout.strip()

def ssh_hk(cmd):
    return subprocess.run([
        "sshpass", "-p", HK_PW, "ssh", "-o", "StrictHostKeyChecking=no",
        f"root@{HK}", cmd
    ], capture_output=True, text=True, timeout=30).stdout.strip()

def main():
    print("TTSKit Relay v2 — file queue mode")
    print(f"  HK: {HK} | B200: daemon on GPU 1")
    
    # Ensure dirs
    ssh_b200(f"mkdir -p {B200_REQ} {B200_RES}")
    ssh_hk(f"mkdir -p {HK_JOBS} {HK_WAV}")
    
    while True:
        # Check for pending jobs on HK
        jobs = ssh_hk(f"ls {HK_JOBS}/*.job 2>/dev/null || echo ''")
        
        for line in jobs.split('\n'):
            if not line.strip():
                continue
            job_file = line.strip()
            job_id = os.path.basename(job_file).replace('.job', '')
            
            # Skip if already processing
            status = ssh_hk(f"cat {HK_JOBS}/{job_id}.status 2>/dev/null || echo ''")
            if status.strip():
                continue
            
            # Mark processing
            ssh_hk(f"echo p > {HK_JOBS}/{job_id}.status")
            
            # Read text
            text = ssh_hk(f"cat {job_file}")
            if not text:
                ssh_hk(f"echo f > {HK_JOBS}/{job_id}.status")
                continue
            
            # Send to B200
            print(f"[{job_id}] Processing: {text[:30]}...")
            b64_payload = base64.b64encode(json.dumps({"text": text}).encode()).decode()
            ssh_b200(f"echo {b64_payload} | base64 -d > {B200_REQ}/{job_id}.json")
            
            # Wait for response
            for _ in range(60):
                time.sleep(0.5)
                res = ssh_b200(f"cat {B200_RES}/{job_id}.json 2>/dev/null || echo ''")
                if res and '"status":"ok"' in res:
                    resp = json.loads(res)
                    wav_data = base64.b64decode(resp['wav_base64'])
                    
                    # Upload WAV to HK
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                        f.write(wav_data)
                        tmp_wav = f.name
                    
                    subprocess.run([
                        "sshpass", "-p", HK_PW, "scp", "-o", "StrictHostKeyChecking=no",
                        tmp_wav, f"root@{HK}:{HK_WAV}/{job_id}.wav"
                    ], capture_output=True, timeout=20)
                    os.unlink(tmp_wav)
                    
                    ssh_hk(f"echo d > {HK_JOBS}/{job_id}.status")
                    print(f"[{job_id}] DONE")
                    break
                elif res and '"status":"err"' in res:
                    ssh_hk(f"echo f > {HK_JOBS}/{job_id}.status")
                    print(f"[{job_id}] FAIL")
                    break
            else:
                ssh_hk(f"echo t > {HK_JOBS}/{job_id}.status")
                print(f"[{job_id}] TIMEOUT")
        
        time.sleep(2)

if __name__ == "__main__":
    main()
