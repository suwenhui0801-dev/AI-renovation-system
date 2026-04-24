# Render AI 解析户型 500 修复说明

本版本重点修复 `/api/ai/parse_floorplan` 在 Render 上返回 HTML 500 的问题。

## 修改内容

1. 后端 `/api/ai/parse_floorplan` 改为所有异常都返回 JSON，避免前端收到 `<html>Internal Server Error</html>`。
2. `call_volcengine_api()` 增加 25 秒主动超时与清晰错误信息，避免 Render/Gunicorn 默认 worker timeout 直接杀进程。
3. 新增 `compact_base64_image()`：调用视觉模型前压缩图片，降低多模态解析耗时。
4. 新增 `fallback_result`：AI 解析失败时返回安全兜底户型，页面不会崩。
5. 新增 `Procfile` 与 `render.yaml`，Render 推荐启动命令：
   `gunicorn app:app --workers 1 --threads 4 --timeout 180 --graceful-timeout 30 --bind 0.0.0.0:$PORT`
6. `requirements.txt` 增加 `Pillow` 用于图片压缩。

## Render 部署注意

如果 Render 后台已经手动填写 Start Command，请改成：

```bash
gunicorn app:app --workers 1 --threads 4 --timeout 180 --graceful-timeout 30 --bind 0.0.0.0:$PORT
```

然后执行 Clear build cache & deploy。
