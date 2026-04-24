# AI 装修模拟系统（Web 版）

这是一个基于 Flask + HTML/CSS/JavaScript + Three.js 的 AI 装修模拟系统，支持 2D 平面编辑、3D 视图预览、家具/房间/门窗编辑、语音输入、AI 生成户型参考图，以及根据户型图自动解析并应用到当前视图。

## 主要功能

- 2D 平面户型编辑：支持房间、家具、门窗的添加、移动、删除和基础属性修改。
- 3D 视图同步：根据 2D 数据实时渲染室内模型。
- 普通语音输入：把语音识别文本整理成可执行的装修指令。
- AI 生成户型图：根据文字需求生成户型参考图。
- 应用户型图：读取上传或生成的户型图，解析为 rooms / furnitures / openings，并映射到 2D / 3D 视图。
- 本地导入/导出配置：支持保存和恢复当前装修方案。

## 本地运行

安装依赖：

```bash
pip install -r requirements.txt
```

启动项目：

```bash
python app.py
```

浏览器访问：

```text
http://localhost:5000
```

## Render 部署

推荐 Start Command：

```bash
gunicorn app:app --workers 1 --threads 4 --timeout 180 --graceful-timeout 30 --bind 0.0.0.0:$PORT
```

Build Command：

```bash
pip install -r requirements.txt
```

## AI 模型环境变量

本项目调用火山方舟模型时，全部使用环境变量里的 **model ID 字符串**，不要填写模型中文名称。

```text
ARK_API_KEY=你的普通语音输入模型 Key
ARK_MODEL=普通语音输入模型 model ID

VOLCENGINE_API_KEY_CHAT=聊天/解析 Key
VOLCENGINE_API_KEY_IMAGE=文生图 Key
VOLCENGINE_API_BASE=https://ark.cn-beijing.volces.com/api/v3
VOLCENGINE_TIMEOUT=120

DOUBAO_SEED_MODEL=应用户型图/AI解析户型图模型 model ID
DOUBAO_SEEDREAM_MODEL=AI生成户型图/文生图模型 model ID
```

## 当前模型调用关系

| 功能 | 使用的环境变量 | 调用方式 |
|---|---|---|
| 普通语音输入 | `ARK_MODEL` | `/chat/completions` |
| AI 生成户型图 | `DOUBAO_SEEDREAM_MODEL` | `/images/generations` |
| 应用户型图 / AI 解析户型图 | `DOUBAO_SEED_MODEL` | `/chat/completions` |

说明：

- `ARK_MODEL` 只负责普通语音输入指令标准化。
- `DOUBAO_SEEDREAM_MODEL` 只负责 AI 生成户型参考图。
- `DOUBAO_SEED_MODEL` 负责应用户型图，也就是把户型图片解析成项目可用的 JSON 布局数据。

## 关键代码位置

- `app.py`
  - `normalize_voice_command_with_llm()`：普通语音输入，读取 `ARK_MODEL`
  - `call_volcengine_image_api()`：AI 生成户型图，读取 `DOUBAO_SEEDREAM_MODEL`
  - `parse_floorplan()`：应用户型图 / AI 解析户型图，读取 `DOUBAO_SEED_MODEL`
- `static/app.js`
  - 调用 `/api/ai/generate_floorplan`
  - 调用 `/api/ai/parse_floorplan`
- `templates/index.html`
  - 页面结构与按钮区域
- `static/style.css`
  - 页面样式与按钮样式

## 注意事项

1. Render 环境变量必须填写 model ID，不要填写模型名称。
2. 如果应用户型图超时，可以把 `VOLCENGINE_TIMEOUT` 设置为 `120` 或更高，并使用上面的 gunicorn timeout 启动命令。
3. 项目压缩包中不包含真实 API Key，部署时需要在 Render 的 Environment 中手动配置。


### 本次模型调用逻辑修复说明

本版本已经在 `app.py` 中强制区分三类模型调用：

| 功能 | 环境变量 | API |
|---|---|---|
| 普通语音输入 | `ARK_MODEL` | `/chat/completions` |
| AI 生成户型图 | `DOUBAO_SEEDREAM_MODEL` | `/images/generations` |
| 应用户型图 / AI 解析户型图 | `DOUBAO_SEED_MODEL` | `/chat/completions`，需要支持图片理解 |

注意：`doubao-seedream-5-0-260128` 这类 Seedream 文生图模型只能放在 `DOUBAO_SEEDREAM_MODEL`，不能放在 `DOUBAO_SEED_MODEL`。如果把 Seedream 填到 `DOUBAO_SEED_MODEL`，应用户型图会出现 `does not support this api`，因为解析户型图走的是聊天/视觉解析接口，不是文生图接口。
