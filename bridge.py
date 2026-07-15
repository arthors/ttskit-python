"""TTS HTTP Bridge — Mac :8899 → B200 daemon"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, time, subprocess

B200 = '/mnt/c/Windows/System32/OpenSSH/ssh.exe -o StrictHostKeyChecking=no -i C:/Users/718265/gpu_key -p 7020 root@10.81.80.198'

def b200(cmd):
    r = subprocess.run([
        'sshpass', '-p', '1234', 'ssh', '-o', 'StrictHostKeyChecking=no',
        '-p', '2222', 'root@localhost',
        f"{B200} '{cmd}' 2>/dev/null"
    ], capture_output=True, text=True, timeout=60)
    return r.stdout.strip()

class Handler(BaseHTTPRequestHandler):
    def _ok(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200); self.end_headers()
            self.wfile.write(b'ok')

    def do_POST(self):
        if self.path != '/tts': self.send_error(404); return
        length = int(self.headers.get('Content-Length', 0))
        req = json.loads(self.rfile.read(length))
        text = req['text']; jid = req['jid']
        
        import base64
        payload = base64.b64encode(json.dumps({'text': text}).encode()).decode()
        b200(f"echo {payload} | base64 -d > /tmp/tts_reqs/{jid}.json")
        
        for _ in range(30):
            time.sleep(0.5)
            raw = b200(f"cat /tmp/tts_res/{jid}.json 2>/dev/null || echo ''")
            for line in raw.split('\n'):
                if line.startswith('{'):
                    try:
                        resp = json.loads(line)
                        if resp.get('status') == 'ok':
                            self._ok(resp); return
                    except: pass
        self.send_error(504, 'timeout')

HTTPServer(('127.0.0.1', 8899), Handler).serve_forever()
