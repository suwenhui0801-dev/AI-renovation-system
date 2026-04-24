# Seedream 模型 ID 调用修正说明

本次修改按最新要求调整 AI 模型调用关系：

1. `DOUBAO_SEEDREAM_MODEL` 作为视觉/文生图模型的 **model ID** 使用。
   - `AI生成户型图` 调用 `DOUBAO_SEEDREAM_MODEL`。
   - `应用户型 / 解析户型图` 也调用 `DOUBAO_SEEDREAM_MODEL`。

2. `DOUBAO_SEED_MODEL` 保留为普通语言模型配置，不再用于户型图视觉解析。

3. `call_volcengine_api()` 的超时配置统一读取：
   - `VOLCENGINE_TIMEOUT=120`
   - 默认值也改为 `120` 秒。

4. Render 推荐 Start Command：

```bash
gunicorn app:app --workers 1 --threads 4 --timeout 180 --graceful-timeout 30 --bind 0.0.0.0:$PORT
```

5. Render 环境变量建议：

```text
ARK_API_KEY=你的普通语言模型 Key
ARK_MODEL=deepseek-v3-2-251201
DOUBAO_SEED_MODEL=普通语言模型 model ID
DOUBAO_SEEDREAM_MODEL=视觉/文生图模型 model ID
VOLCENGINE_API_KEY_CHAT=聊天/解析 Key
VOLCENGINE_API_KEY_IMAGE=文生图/视觉 Key
VOLCENGINE_API_BASE=https://ark.cn-beijing.volces.com/api/v3
VOLCENGINE_TIMEOUT=120
```

注意：代码引用的是 Render 环境变量里的 **model ID 字符串**，不是模型中文名称。
