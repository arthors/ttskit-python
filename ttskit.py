"""
TTSKit Python SDK — 最便宜的中文 TTS API
==========================================
基于 CosyVoice 3.0，支持中文普通话 / 方言 / 语音克隆。

Usage:
    from ttskit import TTSKit
    tts = TTSKit(api_key="your-key")
    tts.speak("你好世界", output="hello.wav")
"""

import os
import json
import time
import base64
import requests
from typing import Optional, List, Dict, BinaryIO


class TTSKit:
    """TTSKit API 客户端"""

    BASE_URL = "https://api.ttskit.cc/v1"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("TTSKIT_API_KEY")
        if not self.api_key:
            raise ValueError("API key required: set TTSKIT_API_KEY env var or pass api_key=")
        self.base_url = base_url or self.BASE_URL
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "ttskit-python/0.1.0",
        })

    # ---- Core API ----

    def speak(self, text: str, *, voice: str = "default", speed: float = 1.0,
              output: Optional[str] = None, format: str = "wav") -> bytes:
        """文字转语音，返回音频 bytes"""
        resp = self._session.post(f"{self.base_url}/audio/speech", json={
            "model": "cosyvoice-3.0",
            "input": text,
            "voice": voice,
            "speed": speed,
            "response_format": format,
        }, timeout=60)
        resp.raise_for_status()
        audio = resp.content
        if output:
            with open(output, "wb") as f:
                f.write(audio)
        return audio

    def speak_stream(self, text: str, **kwargs) -> bytes:
        """流式合成，返回完整音频"""
        return self.speak(text, **kwargs)

    def voices(self) -> List[Dict]:
        """列出可用声音"""
        return self._session.get(f"{self.base_url}/audio/voices").json()["voices"]

    def clone(self, text: str, reference_audio: str, *, output: Optional[str] = None) -> bytes:
        """语音克隆：用参考音频的声音读新文本"""
        with open(reference_audio, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        resp = self._session.post(f"{self.base_url}/audio/speech", json={
            "model": "cosyvoice-3.0",
            "input": text,
            "voice": "clone",
            "reference_audio": b64,
            "response_format": "wav",
        }, timeout=60)
        resp.raise_for_status()
        audio = resp.content
        if output:
            with open(output, "wb") as f:
                f.write(audio)
        return audio

    def usage(self) -> Dict:
        """查询用量"""
        return self._session.get(f"{self.base_url}/usage").json()

    # ---- Openai-Compatible ----

    def chat_completions_create(self, **kwargs) -> Dict:
        """OpenAI-compatible chat/completions (audio output)"""
        return self._session.post(f"{self.base_url}/chat/completions", json=kwargs, timeout=60).json()


# ---- CLI ----
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m ttskit '你好世界'")
        sys.exit(1)
    tts = TTSKit()
    text = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "output.wav"
    tts.speak(text, output=out)
    print(f"Saved to {out}")
