# 错误与重试

请求失败时读取本文件。先保护用户问题原意，再考虑重试；不得靠放宽参数或换数据源伪装成功。

## v1 应用错误

标准错误为 `application/problem+json`：

```json
{
  "type": "/problems/invalid-request",
  "title": "Invalid request",
  "status": 400,
  "detail": "Human-readable explanation",
  "code": "invalid_request",
  "requestId": "req_123"
}
```

按稳定 `code` 分支：

- `invalid_request`：修正明确参数；不要自动改成另一个问题。
- `invalid_cursor`：停止分页并说明书签无效；不能丢掉 cursor 后回到第一页。
- `rate_limited`：遵守 `Retry-After`，串行重试。
- `temporarily_unavailable`：有限退避后告诉用户暂不可用。

## 重试

- `400／404`：除日报 latest 按 API 参考查一次索引外，不盲目重试。
- `429`：按 `Retry-After`；没有则等 60 秒。
- `5xx` 或超时：最多重试 2 次，指数退避。
- 仍失败：说明 LawHOT 暂不可用；不得用训练记忆冒充实时数据。

持久轮询使用 `If-None-Match`；`304` 表示未变化，保留已有数据。
