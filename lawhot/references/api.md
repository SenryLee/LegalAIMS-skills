# LawHOT v1 API 参考

Base URL：`https://hot.fachuiai.com`  
匿名只读，无需 API Key。OpenAPI：`/openapi.json`

字段与路由刻意对齐 aihot v1 心智，便于 Agent 复用；差异见文末。

## GET /api/v1/items

| 参数 | 合同 |
|---|---|
| `mode` | `selected` \| `all`；默认 `selected` |
| `window` | `24h` \| `7d`；默认 `7d` |
| `by` | `timeline` \| `published`；默认 `timeline` |
| `category` | `regulation` \| `litigation` \| `legaltech` \| `practice` \| `insight` \| `vendor` |
| `q` | 2—200 字 |
| `limit` | 1—100；默认 50 |
| `cursor` | 上一页 `page.nextCursor` 原样回传 |

每条 item 关键字段：`id`、`title`、`originalTitle`、`summary`、`source.name`、`links.lawhot`、`links.original`、`publishedAt`、`discoveredAt`、`category`、`score`、`selected`。  
兼容：响应可同时带 `links.aihot`（值与 `links.lawhot` 相同），旧提示词误用也不至于断链。

## GET /api/v1/hot-topics

当前多源热点列表（MVP 可能条目较少）。保持返回顺序。

## 日报

```text
GET /api/v1/dailies?limit=7
GET /api/v1/dailies/latest
GET /api/v1/dailies/{YYYY-MM-DD}
```

## 与 aihot 的主要差异

- 主机与品牌：`hot.fachuiai.com` / LawHOT
- 分类体系换成法律向六类
- 主站内链接字段名为 `links.lawhot`
- MVP 暂无 `/api/v1/selected/snapshot|changes`
