"""TTSKit API Server — async TTS via job polling, doesn't block workers"""
import os, json, hashlib, time, uuid, sqlite3, urllib.parse
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="TTSKit API", version="0.2.0")
DB = "ttskit.db"

def init_db():
    db = sqlite3.connect(DB)
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT, api_key TEXT UNIQUE, credits INTEGER DEFAULT 5000, created_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY, api_key TEXT, chars INTEGER, endpoint TEXT, created_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, api_key TEXT, amount_cents INTEGER, status TEXT, created_at TEXT)")
    db.commit(); db.close()

init_db()
# Create demo user for anonymous web testing
if not db_exec("SELECT id FROM users WHERE api_key='ttskit-demo'", fetch=True):
    db_exec("INSERT INTO users (email, password_hash, api_key, credits, created_at) VALUES ('demo@ttskit.cc','demo','ttskit-demo',99999999,'2026-01-01T00:00:00')")

def db_exec(sql, params=(), fetch=False):
    db = sqlite3.connect(DB)
    cur = db.cursor(); cur.execute(sql, params)
    if fetch: rows = cur.fetchall(); db.close(); return rows
    db.commit(); db.close()

class RegisterRequest(BaseModel):
    email: str; password: str

class LoginRequest(BaseModel):
    email: str; password: str

class SpeakRequest(BaseModel):
    model: str = "cosyvoice-3.0"
    input: str; voice: str = "default"
    speed: float = 1.0; response_format: str = "wav"

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def get_user(api_key: str):
    rows = db_exec("SELECT id, email, credits FROM users WHERE api_key=?", (api_key,), fetch=True)
    return rows[0] if rows else None

# ---- Routes ----
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse("static/index.html")

@app.post("/api/register")
def register(req: RegisterRequest):
    if db_exec("SELECT id FROM users WHERE email=?", (req.email,), fetch=True):
        raise HTTPException(400, "邮箱已注册")
    api_key = "ttskit-" + uuid.uuid4().hex[:24]
    db_exec("INSERT INTO users (email, password_hash, api_key, credits, created_at) VALUES (?,?,?,5000,?)",
            (req.email, hash_pw(req.password), api_key, datetime.now().isoformat()))
    return {"api_key": api_key, "credits": 5000, "message": "注册成功！获赠 5000 免费字数"}

@app.post("/api/login")
def login(req: LoginRequest):
    rows = db_exec("SELECT api_key, credits FROM users WHERE email=? AND password_hash=?",
                   (req.email, hash_pw(req.password)), fetch=True)
    if not rows: raise HTTPException(401, "邮箱或密码错误")
    return {"api_key": rows[0][0], "credits": rows[0][1]}

@app.get("/api/usage")
def usage(api_key: str = Header(alias="Authorization")):
    key = api_key.replace("Bearer ", "")
    user = get_user(key)
    if not user: raise HTTPException(401, "无效 API Key")
    total = db_exec("SELECT SUM(chars) FROM usage WHERE api_key=?", (key,), fetch=True)
    return {"credits_remaining": user[2], "total_chars_used": total[0][0] or 0}

@app.post("/v1/audio/speech")
def speak(req: SpeakRequest, api_key: str = Header(alias="Authorization")):
    key = api_key.replace("Bearer ", "")
    user = get_user(key)
    if not user: raise HTTPException(401, "无效 API Key")
    chars = len(req.input)
    if user[2] < chars: raise HTTPException(402, f"字数不足：剩余 {user[2]}，需要 {chars}")
    
    job_id = uuid.uuid4().hex
    db_exec("UPDATE users SET credits = credits - ? WHERE api_key=?", (chars, key))
    db_exec("INSERT INTO usage (api_key, chars, endpoint, created_at) VALUES (?,?,?,?)",
            (key, chars, "speech", datetime.now().isoformat()))
    
    os.makedirs("/opt/ttskit/jobs", exist_ok=True)
    os.makedirs("/opt/ttskit/wav", exist_ok=True)
    with open(f"/opt/ttskit/jobs/{job_id}.job", "w") as f:
        f.write(req.input)
    
    return {"job_id": job_id, "status": "queued", "credits_remaining": user[2] - chars}

@app.get("/v1/audio/speech/{job_id}")
def speak_status(job_id: str):
    status_path = f"/opt/ttskit/jobs/{job_id}.status"
    if os.path.exists(status_path):
        with open(status_path) as f:
            s = f.read().strip()
        if s == 'd':
            wav_path = f"/opt/ttskit/wav/{job_id}.wav"
            if os.path.exists(wav_path) and os.path.getsize(wav_path) > 100:
                return FileResponse(wav_path, media_type="audio/wav")
        if s == 'f': raise HTTPException(500, "生成失败")
        if s in ('p', 'd'):
            return {"job_id": job_id, "status": "processing"}
    raise HTTPException(404, "等待中...")

@app.get("/v1/audio/voices")
def voices():
    return {"voices": [
        {"id": "default", "name": "默认女声", "language": "zh"},
        {"id": "male-1", "name": "标准男声", "language": "zh"},
        {"id": "sichuan", "name": "四川话", "language": "zh-sichuan"},
        {"id": "cantonese", "name": "粤语", "language": "zh-yue"},
    ]}

@app.get("/api/pricing")
def pricing():
    return {"plans": [
        {"name": "免费", "chars": 5000, "price": 0},
        {"name": "入门", "chars": 100000, "price": 9.9},
        {"name": "专业", "chars": 500000, "price": 49},
        {"name": "企业", "chars": 2000000, "price": 199},
    ]}

# ---- Payment (ZPAY) ----

ZPAY_PID = ""  # 审核通过后填
ZPAY_KEY = ""  # 审核通过后填
ZPAY_CID = "20731"
ZPAY_API = "https://zpayz.cn/mapi.php"

def zpay_sign(params):
    """MD5 sign sorted params + key"""
    keys = sorted(k for k in params if k not in ('sign','sign_type') and params[k] != '')
    s = '&'.join(f'{k}={params[k]}' for k in keys) + ZPAY_KEY
    return hashlib.md5(s.encode()).hexdigest()

@app.post("/api/pay/create")
def pay_create(plan: str = "entry", api_key: str = Header(alias="Authorization")):
    key = api_key.replace("Bearer ", "")
    user = get_user(key)
    if not user: raise HTTPException(401, "无效 API Key")
    
    plans = {"entry": ("入门", 9.9, 100000), "pro": ("专业", 49, 500000), "enterprise": ("企业", 199, 2000000)}
    if plan not in plans: raise HTTPException(400, "无效套餐")
    name, price, chars = plans[plan]
    
    oid = datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:8]
    
    # Save order
    db_exec("INSERT INTO orders (api_key, amount_cents, status, created_at) VALUES (?,?,'pending',?)",
            (key, int(price*100), datetime.now().isoformat()))
    
    params = {
        "pid": ZPAY_PID, "cid": ZPAY_CID, "type": "alipay",
        "out_trade_no": oid, "notify_url": "https://ttskit.cc/api/pay/notify",
        "return_url": "https://ttskit.cc", "name": f"TTSKit {name}版 {chars//10000}万字",
        "money": str(price), "param": f"{key}|{plan}|{chars}",
        "sign_type": "MD5"
    }
    params["sign"] = zpay_sign(params)
    
    r = __import__('requests').post(ZPAY_API, data=params, timeout=10)
    d = r.json()
    if d.get('code') == 1:
        return {"pay_url": d.get('payurl') or d.get('qrcode'), "order_id": oid}
    raise HTTPException(500, d.get('msg', '支付创建失败'))

@app.post("/api/pay/notify")
async def pay_notify(request: Request):
    form = await request.form()
    data = dict(form)
    
    # Verify sign
    sign = data.pop('sign', '')
    sign_type = data.pop('sign_type', '')
    if sign != zpay_sign(data):
        return "sign error"
    
    if data.get('trade_status') == 'TRADE_SUCCESS':
        param = data.get('param', '')
        parts = param.split('|')
        if len(parts) == 3:
            apikey, plan, chars = parts
            db_exec("UPDATE users SET credits = credits + ? WHERE api_key=?", (int(chars), apikey))
            db_exec("UPDATE orders SET status='paid' WHERE api_key=? AND status='pending'", (apikey,))
    
    return "success"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
