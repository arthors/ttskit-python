# 知乎技术文

## 标题
如何用 CosyVoice 3.0 搭建一套中文 TTS API 服务（完整记录）

## 正文

最近用 CosyVoice 3.0 跑通了一套中文 TTS API，从下载模型到上线收款，踩了不少坑，记录一下。

### 为什么要自己搞

市面上的中文 TTS API 要么贵（豆包大模型 ¥50/10 万字），要么缺方言，要么需要企业认证。CosyVoice 3.0 是阿里 FunAudioLLM 开源的语音合成模型，0.5B 参数，Apache 2.0 许可，支持 18+ 中文方言，完全可商用。

### 架构

```
用户 → ttskit.cc (香港轻量云 ¥45/月) → 任务队列 → GPU 推理 → 返回 WAV
```

- 前端：FastAPI + SQLite（注册、计费、API）
- 推理：CosyVoice 3.0 @ B200 GPU（RTF 0.6，比实时还快）
- 中转：Mac 跑 relay 桥接香港和 GPU
- 支付：ZPAY 支付宝个人接口（¥88 开户）

### 关键步骤

1. **下载模型**：ModelScope 直接拉，9GB。香港轻量云上跑 CPU 推理会炸内存，建议 GPU
2. **持久化推理**：模型常驻内存，用文件队列通信（不是每次请求都加载模型）
3. **异步 API**：TTS 接口立刻返回 job_id，客户端轮询拿结果

### 成本

| 项目 | 费用 |
|------|------|
| 香港服务器 | ¥45/月 |
| 域名 | ¥85/年 |
| 支付开户 | ¥88 一次性 |
| GPU | 自有 |

月成本不到 ¥50，毛利 95%+。

### 开源

代码全在 GitHub：[github.com/arthors/ttskit-python](https://github.com/arthors/ttskit-python)

如果对中文 TTS API 有需求可以试试：[ttskit.cc](https://ttskit.cc)，注册送 5000 字。
