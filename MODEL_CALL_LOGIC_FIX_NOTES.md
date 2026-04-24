# AI 模型调用逻辑修复说明

## 已修复的调用关系

1. 普通语音输入
   - 环境变量：`ARK_MODEL`
   - 调用接口：`/chat/completions`
   - 代码位置：`normalize_voice_command_with_llm()`

2. AI 生成户型图
   - 环境变量：`DOUBAO_SEEDREAM_MODEL`
   - 调用接口：`/images/generations`
   - 代码位置：`call_volcengine_image_api()`

3. 应用户型图 / AI 解析户型图
   - 环境变量：`DOUBAO_SEED_MODEL`
   - 调用接口：`/chat/completions`
   - 代码位置：`parse_floorplan()`

## 这次截图报错的原因

报错里的模型是 `doubao-seedream-5-0-260128`，但这个模型是文生图模型，只支持图片生成接口，不支持聊天/视觉解析接口。

应用户型图会把户型图片发给模型解析成 JSON，所以必须使用 `DOUBAO_SEED_MODEL`，并且这个模型需要支持图片理解/视觉聊天能力。

## Render 环境变量填写规则

```env
ARK_MODEL=普通语音输入模型的 model ID
DOUBAO_SEEDREAM_MODEL=doubao-seedream-5-0-260128
DOUBAO_SEED_MODEL=支持图片理解/视觉聊天的 Doubao Seed 模型 model ID
VOLCENGINE_API_BASE=https://ark.cn-beijing.volces.com/api/v3
VOLCENGINE_TIMEOUT=120
```

不要把 `doubao-seedream-5-0-260128` 填到 `DOUBAO_SEED_MODEL`。
