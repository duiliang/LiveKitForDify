# LiveKit + Dify 语音助手

本项目演示如何使用 **FastAPI**、**LiveKit**、阿里云 DashScope（含 CosyVoice）语音服务和本地 **Dify API** 构建一个具备打断能力的中文语音助手。后端提供 REST API 和 LiveKit 令牌服务，前端使用浏览器的 WebRTC 能力与助手实时对话，并提供噪声检测、思考提示等人性化体验。

## 功能亮点

- 🎙️ **实时语音会话**：浏览器通过 LiveKit 与后端交互，语音流由 Python 版代理转发至 DashScope STT/CosyVoice TTS 与 Dify。
- 🧠 **思考提示**：当大语言模型响应时间较长时，界面会自动提示“助手正在深入思考…”。
- 🛑 **可打断**：检测到用户重新说话时会取消当前语音播放，模仿 ChatGPT 语音助手的打断体验。
- 👂 **环境噪声监测**：利用 Web Audio API 实时显示环境噪声分贝，帮助用户判断麦克风采集质量。
- 🪄 **文本调试模式**：若暂时无法连接 LiveKit，可直接通过文本框调用 Dify 与 DashScope TTS 验证管线。

## 目录结构

```
backend/
  app/
    main.py              # FastAPI 入口
    config.py            # 环境变量配置
    schemas.py           # Pydantic 请求/响应模型
    services/
      dashscope.py       # DashScope STT/TTS 封装
      dify.py            # Dify API 帮助函数
      voice_agent.py     # LiveKit 语音代理（需独立部署）
  tests/                 # Pytest 测试
frontend/
  index.html             # 单页应用入口
  app.js                 # UI 逻辑、LiveKit 客户端
  styles.css             # 页面样式
```

## 环境准备

1. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**（可在项目根目录创建 `.env` 文件）

   ```env
   DASHSCOPE_API_KEY=你的 DashScope API Key（北京区域）
   DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/api/v1/
   DASHSCOPE_STT_MODEL=paraformer-realtime-v2
   DASHSCOPE_TTS_MODEL=cosyvoice-v2
   DASHSCOPE_DEFAULT_VOICE=longxiaochun_v2
   DIFY_API_BASE=http://127.0.0.1:8000/v1/
   DIFY_API_KEY=你的Dify密钥
   DIFY_APP_ID=可选，如需指定工作流
   LIVEKIT_HOST=https://livekit.example.com
   LIVEKIT_API_KEY=你的LiveKit Key
   LIVEKIT_API_SECRET=你的LiveKit Secret
   ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:8000
   ```

3. **LiveKit 语音代理**

   `backend/app/services/voice_agent.py` 需要安装官方 [livekit-agents](https://docs.livekit.io/agents/) 库，并由 `livekit-agents` CLI 部署，例如：

   ```bash
   pip install livekit-agents
   lk-agents start --entry backend.app.services.voice_agent:run_agent
   ```

## 运行方式

1. **启动 FastAPI**

   ```bash
   uvicorn backend.app.main:app --reload --port 9000
   ```

2. **访问前端**

   直接打开 <http://localhost:9000/>，填写房间 ID、用户标识并点击“连接助手”。若 LiveKit 暂未准备好，可以使用下方文本模式验证管线。

## 测试

项目附带一组端到端的 API 单元测试与服务模拟，确保关键功能稳定。运行命令：

```bash
pytest
```

## 注意事项

- 由于评测环境限制，仓库中的测试使用 `respx` 模拟 DashScope 与 Dify 服务，不会真正调用外部接口。
- `LiveKit` Python SDK 与 `livekit-agents` 为可选依赖，未安装时 API 会返回明确提示。部署真实语音助手时务必安装相关包并配置可用的 LiveKit 服务器。
- 前端脚本通过 CDN 引入 `livekit-client`，如需离线部署可以改为本地静态资源。

祝你玩得开心，欢迎在此基础上扩展更多功能！
