"""TTSKit Relay v2 — file-based queue between HK and B200 daemon"""
import time, json, os, subprocess, base64, tempfile

HK = "47.242.6.136"
HK_PW = "ZAQWSX123@@"
B200_REQ = "/tmp/tts_reqs"
B200_RES = "/tmp/tts_res"
HK_JOBS = "/opt/ttskit/jobs"
HK_WAV = "/opt/ttskit/wav"

# --- Fixed SSH helpers (stderr=DEVNULL for clean output) ---
def b200(cmd):
    inner = cmd.replace("'", "'\"'\"'")
    r = subprocess.run([
        "sshpass", "-p", "1234", "ssh", "-o", "StrictHostKeyChecking=no",
        "-p", "2222", "root@localhost",
        f"/mnt/c/Windows/System32/OpenSSH/ssh.exe -o StrictHostKeyChecking=no -i C:/Users/718265/gpu_key -p 7020 root@10.81.80.198 '{inner}' 2>/dev/null"
    ], capture_output=True, text=True, timeout=30)
    return r.stdout.strip()

def hk(cmd):
    r = subprocess.run([
        "sshpass", "-p", HK_PW, "ssh", "-o", "StrictHostKeyChecking=no",
        f"root@{HK}", cmd
    ], capture_output=True, text=True, timeout=30)
    return r.stdout.strip()

def extract_json(text):
    """Extract the first JSON object from SSH output"""
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('{'):
            try:
                json.loads(line)
                return line
            except:
                pass
    return text

# --- Main loop ---
def main():
    print("TTSKit Relay v2")
    b200(f"mkdir -p {B200_REQ} {B200_RES}")
    hk(f"mkdir -p {HK_JOBS} {HK_WAV}")
    
    while True:
        jlist = hk(f"ls {HK_JOBS}/*.job 2>/dev/null || echo ''")
        for jf in jlist.split('\n'):
            jf = jf.strip()
            if not jf: continue
            jid = os.path.basename(jf).replace('.job', '')
            
            s = hk(f"cat {HK_JOBS}/{jid}.status 2>/dev/null || echo ''")
            if s.strip(): continue
            
            hk(f"echo p > {HK_JOBS}/{jid}.status")
            text = hk(f"cat {jf}")
            if not text: hk(f"echo f > {HK_JOBS}/{jid}.status"); continue
            
            print(f"[{jid}] {text[:30]}...")
            payload = base64.b64encode(json.dumps({"text": text}).encode()).decode()
            b200(f"echo {payload} | base64 -d > {B200_REQ}/{jid}.json")
            
            for _ in range(60):
                time.sleep(0.5)
                raw = b200(f"cat {B200_RES}/{jid}.json 2>/dev/null || echo ''")
                jraw = extract_json(raw)
                if not jraw: continue
                try:
                    resp = json.loads(jraw)
                except: continue
                
                if resp.get('status') == 'ok':
                    wav = base64.b64decode(resp['wav_base64'])
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                        f.write(wav); tmp = f.name
                    # Upload to .tmp first with retry
                    for retry in range(3):
                        r = subprocess.run(["sshpass", "-p", HK_PW, "scp", "-o", "StrictHostKeyChecking=no",
                                           "-o", "ConnectTimeout=10", tmp,
                                           f"root@{HK}:{HK_WAV}/{jid}.wav.tmp"],
                                          capture_output=True, timeout=60)
                        if r.returncode == 0:
                            break
                        time.sleep(1)  # faster polling
                    hk(f"mv {HK_WAV}/{jid}.wav.tmp {HK_WAV}/{jid}.wav && echo d > {HK_JOBS}/{jid}.status")
                    os.unlink(tmp)
                    print(f"[{jid}] DONE")
                    break
                elif resp.get('status') == 'err':
                    hk(f"echo f > {HK_JOBS}/{jid}.status")
                    print(f"[{jid}] FAIL: {resp.get('msg','')}")
                    break
            else:
                hk(f"echo t > {HK_JOBS}/{jid}.status")
                print(f"[{jid}] TIMEOUT")
        time.sleep(1)  # faster polling

if __name__ == "__main__":
    main()
