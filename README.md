# TTSKit — 最便宜的中文 TTS API

[![PyPI](https://img.shields.io/badge/pypi-ttskit-blue)](https://pypi.org/project/ttskit)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Model](https://img.shields.io/badge/model-CosyVoice%203.0-orange)](https://github.com/FunAudioLLM/CosyVoice)

基于 **CosyVoice 3.0** 的中文文本转语音 API，比竞品便宜 3-16 倍。

## 为什么选 TTSKit

|  | TTSKit | ElevenLabs | Fish Audio | MiniMax |
|--|--------|------------|------------|---------|
| 千字价格 | **¥0.5** | ¥8 | ¥1.5 | ¥2 |
| 中文质量 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 语音克隆 | ✅ 10s 即克 | ✅ | ✅ | ✅ |
| 开源模型 | ✅ | ❌ | ✅ | ❌ |
| 方言支持 | ✅ 18+ 方言 | ❌ | ❌ | ❌ |
| 免费额度 | ✅ 每月 1000 字 | ❌ | ❌ | ❌ |

## 快速开始

```bash
pip install ttskit
```

```python
from ttskit import TTSKit

tts = TTSKit(api_key="your-key")

# 基础合成
tts.speak("你好，欢迎使用 TTSKit", output="hello.wav")

# 语音克隆
tts.clone("这是一段克隆的声音", reference_audio="my_voice.wav", output="cloned.wav")

# 列出可用声音
voices = tts.voices()

# 查询用量
usage = tts.usage()
```

## API 文档

完整文档请访问 [ttskit.cc/docs](https://ttskit.cc/docs)

### 接口

| 端点 | 说明 |
|------|------|
| `POST /v1/audio/speech` | 文字转语音 |
| `GET /v1/audio/voices` | 声音列表 |
| `GET /v1/usage` | 用量查询 |

### OpenAI 兼容

```python
import openai
client = openai.OpenAI(base_url="https://api.ttskit.cc/v1", api_key="your-key")
client.audio.speech.create(model="cosyvoice-3.0", input="你好世界", voice="default")
```

## 特性

- 🇨🇳 **中文原生** — 普通话 + 18+ 方言（粤语、四川话、东北话...）
- 🎤 **语音克隆** — 10 秒音频即可克隆任意声音
- ⚡ **低延迟** — 流式生成，秒级响应
- 🔌 **OpenAI 兼容** — 一行代码从 ElevenLabs 迁移
- 🆓 **免费额度** — 每月首 1000 字免费
- 📦 **开源** — 基于 CosyVoice 3.0，Apache 2.0 许可

## 获取 API Key

注册 [ttskit.cc](https://ttskit.cc) 获取免费 API key。

## License

Apache 2.0
