# 出境访问约束（阿里云大陆机）

## 结论

深圳 ECS **默认不能稳定访问中国大陆以外网站**。  
这对 LawHOT 影响很大：当前 P0 里约 **一半是境外 RSS/网页**（Artificial Lawyer、OpenAI、Federal Register、DeepMind…）。  
**不解决出境，英文信源表就只是“设计”，不是“可抓”。**

大陆源（网信办、最高法、公众号等）不受影响。

## 影响面

| 能力 | 无出境时 | 说明 |
|---|---|---|
| 境外 RSS / 官网 | ❌ 基本失败 | MVP 英文精选会空或极少 |
| Anthropic 等网页抓取 | ❌ | 同上 |
| 中文官网 / 公众号 | ✅ | 应用国内 connector |
| Docker / GitHub 拉取 | ⚠️ 常卡 | 已用镜像绕过一部分 |
| 境外 LLM API（OpenAI 等） | ⚠️/❌ | 建议国内模型或走代理 |
| 对外提供 `hot.fachuiai.com` API | ✅ | 入站与出站无关 |

## 三种解法（按推荐顺序）

### 方案 A · 抓取走 HTTP 代理（最省事，推荐）

再准备一台**有出境能力的小 VPS**（香港/海外 1 核即可），只做正向代理。  
大陆 `lawhot` 容器仅给 **fetcher** 配：

```bash
# /opt/lawhot/repo/lawhot/deploy/.env
LAWHOT_HTTP_PROXY=http://user:pass@YOUR_PROXY_HOST:7890
LAWHOT_HTTPS_PROXY=http://user:pass@YOUR_PROXY_HOST:7890
# 国内源不要走代理
LAWHOT_NO_PROXY=localhost,127.0.0.1,.cn,cac.gov.cn,court.gov.cn,gov.cn,miit.gov.cn
```

- API / 数据库 / nginx 仍在阿里云（延迟低、备案友好）
- 只有抓取流量出代理
- 成本通常远低于整机迁海外

### 方案 B · 海外 Fetcher + 大陆 API（更干净）

```text
[海外小机] 定时抓取英文源 → POST 推送到
[阿里云 hot.fachuiai.com] /admin/ingest-push（鉴权）
         ↓
      SQLite/API/Skill
```

- 大陆机永不主动访问境外
- 推送接口需 `LAWHOT_ADMIN_TOKEN`，防冒灌
- 适合你后面信源变多、代理不稳定时

### 方案 C · 先做「中文 MVP」，英文后置（权宜）

无代理时先只开：

- 网信办 / 最高法 / 政府网 / 法治日报
- 核心法律 AI 公众号

英文源保持在 `sources.v1.yaml` 但 `enabled: false`，等 A/B 就绪再开。  
**可以上线 Skill，但定位变成「中国法律 AI 资讯」而非「全球」。**

## 不建议的做法

- 指望 RSS 源“刚好有国内镜像”——法律垂直源几乎没有
- 整站迁到海外 VPS：国内访问与合规/备案更麻烦，主站 `fachuiai.com` 已在阿里云
- 在 2C2G 上跑复杂翻墙客户端与中台抢内存——用独立小代理更稳

## 和信源表的关系

- **信源名单仍然有效**：它描述“该追谁”，不绑定“谁去抓”
- **落地时多一列运行时标签**：`egress: domestic | overseas`
- 抓取调度：`domestic` 直连；`overseas` 必须经 proxy 或海外 worker

## 你需要拍板的一句话

1. **有境外代理/小 VPS** → 走方案 A（推荐），全球源可按原表推进  
2. **暂时没有** → 先方案 C 上中文 MVP，同时准备代理  
3. **愿意拆服务** → 方案 B  

没有出境能力时，不必改品牌方向，但要改 **抓取拓扑**，不能假设深圳机直连 OpenAI Blog。
