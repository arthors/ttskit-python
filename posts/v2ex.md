# V2EX 帖子

## 标题
我做了中文 TTS API，比 Fish Audio 便宜 3 倍，注册送 5000 字

## 正文

上周在找一个中文 TTS API 给我的项目加语音功能，发现市场上的选项：

| 平台 | 10 万字价格 | 方言 | 门槛 |
|------|-----------|------|------|
| 豆包大模型语音合成 | ¥50 | 粤语 | 企业实名 |
| Fish Audio | ~¥28 | 无 | 信用卡 |
| MiniMax | ¥200 | 无 | API key |
| 阿里云百炼 | ~¥30 | 粤语四川话 | 企业认证 |
| **TTSKit** | **¥9.9** | **18+ 方言** | **邮箱** |

我觉得不应该这么贵，就自己做了一个：[ttskit.cc](https://ttskit.cc)

**技术栈**：CosyVoice 3.0（阿里开源，Apache 2.0）+ FastAPI + B200 GPU 推理

**特点**：
- 🇨🇳 中文普通话 + 粤语、四川话、东北话等 18+ 方言
- 🎤 10 秒音频即可克隆声音
- 🔌 OpenAI 兼容 API（一行代码从 ElevenLabs 迁移）
- 🆓 注册送 5000 免费字数，够生成 10 段语音

**价格**：
- 免费：5000 字/月
- 入门：¥9.9/10 万字
- 专业：¥49/50 万字
- 企业：¥199/200 万字

**快速开始**：
```python
from ttskit import TTSKit
tts = TTSKit(api_key="你的 key")
tts.speak("你好世界", output="hello.wav")
```

GitHub：[github.com/arthors/ttskit-python](https://github.com/arthors/ttskit-python)

欢迎试用，反馈直接提 issue 🙏
