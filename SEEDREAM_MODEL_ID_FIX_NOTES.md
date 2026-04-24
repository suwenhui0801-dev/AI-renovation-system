# AI 模型调用逻辑修正说明

本次修改按最新要求重新固定三个模型的调用关系，并且全部使用 Render 环境变量中的 **model ID 字符串** 调用。

## 当前调用关系

1. 普通语音输入
   - 调用：`ARK_MODEL`
   - 用途：把语音识别出来的口语文本整理成系统可执行的中文指令。

2. AI 生成户型图
   - 调用：`DOUBAO_SEEDREAM_MODEL`
   - 用途：根据用户输入的装修/户型需求生成户型参考图。
   - 接口：`/images/generations`

3. 应用户型图 / AI 解析户型图
   - 调用：`DOUBAO_SEED_MODEL`
   - 用途：读取上传或生成的户型图，并解析成项目内部使用的 rooms / furnitures / openings JSON。
   - 接口：`/chat/completions`

## Render 环境变量建议

```text
ARK_API_KEY=你的普通语言模型 Key
ARK_MODEL=普通语音输入模型 model ID
DOUBAO_SEED_MODEL=应用户型图/AI解析户型图模型 model ID
DOUBAO_SEEDREAM_MODEL=AI生成户型图/文生图模型 model ID
VOLCENGINE_API_KEY_CHAT=聊天/解析 Key
VOLCENGINE_API_KEY_IMAGE=文生图 Key
VOLCENGINE_API_BASE=https://ark.cn-beijing.volces.com/api/v3
VOLCENGINE_TIMEOUT=120
```

## 关键代码位置

- `normalize_voice_command_with_llm()`：读取 `ARK_MODEL`
- `call_volcengine_image_api()`：读取 `DOUBAO_SEEDREAM_MODEL`
- `parse_floorplan()`：读取 `DOUBAO_SEED_MODEL`

Render 推荐 Start Command：

```bash
gunicorn app:app --workers 1 --threads 4 --timeout 180 --graceful-timeout 30 --bind 0.0.0.0:$PORT
```
