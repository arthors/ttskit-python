"""
TTSKit API Server — FastAPI backend with auth + billing + TTS inference
"""
import os, json, hashlib, time, uuid, sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="TTSKit API", version="0.1.0")
DB = "ttskit.db"

# ---- DB ----
def init_db():
    db = sqlite3.connect(DB)
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT, api_key TEXT UNIQUE, credits INTEGER DEFAULT 1000, created_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY, api_key TEXT, chars INTEGER, endpoint TEXT, created_at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, api_key TEXT, amount_cents INTEGER, status TEXT, created_at TEXT)")
    db.commit()
    db.close()

init_db()

def db_exec(sql, params=(), fetch=False):
    db = sqlite3.connect(DB)
    cur = db.cursor()
    cur.execute(sql, params)
    if fetch:
        rows = cur.fetchall()
        db.close()
        return rows
    db.commit()
    db.close()

# ---- Models ----
class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class SpeakRequest(BaseModel):
    model: str = "cosyvoice-3.0"
    input: str
    voice: str = "default"
    speed: float = 1.0
    response_format: str = "wav"

# ---- Auth ----
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
    existing = db_exec("SELECT id FROM users WHERE email=?", (req.email,), fetch=True)
    if existing:
        raise HTTPException(400, "邮箱已注册")
    api_key = "ttskit-" + uuid.uuid4().hex[:24]
    db_exec("INSERT INTO users (email, password_hash, api_key, credits, created_at) VALUES (?,?,?,1000,?)",
            (req.email, hash_pw(req.password), api_key, datetime.now().isoformat()))
    return {"api_key": api_key, "credits": 1000, "message": "注册成功！获赠 1000 免费字数"}

@app.post("/api/login")
def login(req: LoginRequest):
    rows = db_exec("SELECT api_key, credits FROM users WHERE email=? AND password_hash=?",
                   (req.email, hash_pw(req.password)), fetch=True)
    if not rows:
        raise HTTPException(401, "邮箱或密码错误")
    return {"api_key": rows[0][0], "credits": rows[0][1]}

@app.get("/api/usage")
def usage(api_key: str = Header(alias="Authorization")):
    key = api_key.replace("Bearer ", "")
    user = get_user(key)
    if not user:
        raise HTTPException(401, "无效 API Key")
    lifecycle = db_exec("SELECT SUM(chars) FROM usage WHERE api_key=?", (key,), fetch=True)
    total = lifecycle[0][0] or 0
    return {"credits_remaining": user[2], "total_chars_used": total}

@app.post("/v1/audio/speech")
def speak(req: SpeakRequest, api_key: str = Header(alias="Authorization")):
    key = api_key.replace("Bearer ", "")
    user = get_user(key)
    if not user:
        raise HTTPException(401, "无效 API Key")
    chars = len(req.input)
    if user[2] < chars:
        raise HTTPException(402, f"字数不足：剩余 {user[2]}，需要 {chars}")
    # Deduct credits
    db_exec("UPDATE users SET credits = credits - ? WHERE api_key=?", (chars, key))
    db_exec("INSERT INTO usage (api_key, chars, endpoint, created_at) VALUES (?,?,?,?)",
            (key, chars, "speech", datetime.now().isoformat()))
    # TTS inference will be added here
    # For now return placeholder
    return JSONResponse({"message": f"处理 {chars} 字", "credits_remaining": user[2] - chars},
                        headers={"X-Credits-Remaining": str(user[2] - chars)})

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
        {"name": "免费", "chars": 1000, "price": 0},
        {"name": "入门", "chars": 100000, "price": 49},
        {"name": "专业", "chars": 500000, "price": 199},
        {"name": "企业", "chars": 2000000, "price": 699},
    ]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
