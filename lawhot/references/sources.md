# LawHOT 信源名单 v0.1（可落地）

机器可读完整表见同目录 [`sources.v1.yaml`](./sources.v1.yaml)。本文是给人看的执行版：先接什么、怎么接、你需要补什么。

## 定位

- **主线 A · Law × AI**：监管、立法、诉讼、合规（AI 如何被法律规制）
- **主线 B · AI × Law**：LegalTech 产品、律所落地、司法智能化（AI 如何改变法律行业）
- **加权线 · Vendor Frontier**：OpenAI / Anthropic / Google DeepMind / Microsoft 等**研究、安全、政策**一手文（你点名的重点；入库时过滤掉纯营销）

原则：**中英大致各半**；厂商源「少而精、高权重」，不拿通用 AI 资讯刷屏。

## P0 首批（建议先接通这批）

### 英文 · 法律垂直 / 监管（约 15）

| 信源 | 接入 | 主线 | 状态（2026-07-25） |
|---|---|---|---|
| Artificial Lawyer | RSS | A+B | ✅ feed 可用 |
| Legal IT Insider | RSS | B | ✅ |
| LawSites / LawNext | RSS | B | ✅ |
| Everlaw Blog | RSS | B | ✅ |
| Clio Blog | RSS | B | ✅（滤营销） |
| Thomson Reuters Legal Posts | RSS | A+B | ✅（关键词收窄） |
| IAPP News | 网页 | A | 网页 OK，RSS 无 |
| US Federal Register（AI） | RSS | A | ✅ |
| FTC Press | RSS | A | ✅（需过滤） |
| GovTech AI | RSS | A+B | ✅ |
| Stanford HAI News | 网页 | A | RSS 名存实亡，按网页 |
| MIT Tech Review · AI | RSS | A | ✅（需过滤） |
| EU AI Act / EC 政策页 | 网页 | A | ✅ |
| OECD.AI | 网页 | A | ✅ |
| arXiv cs.CY | RSS | A | ✅（法律词过滤） |

### 英文 · 头部厂商（重点，约 7）

| 信源 | 接入 | 说明 |
|---|---|---|
| OpenAI News | RSS `openai.com/news/rss.xml` | 排除客户案例 |
| Anthropic Newsroom | 网页 | **无 RSS**，必须网页抓 |
| Anthropic Research | 网页 | 安全/对齐/政策研究 |
| Google DeepMind Blog | RSS | 研究向过滤 |
| Google Blog · AI | RSS | 滤营销 |
| Microsoft Research | RSS | 法律/Copilot 相关收窄 |
| Hugging Face Blog | RSS（可作 P1） | 开源治理相关优先 |

Anthropic Engineering、Mistral News 放 P1。

### 中文 · 官方 / 权威（约 7）

| 信源 | 接入 | 说明 |
|---|---|---|
| 国家网信办 cac.gov.cn | 网页 | 核心监管原文 |
| 最高人民法院 court.gov.cn | 网页 | 司法 AI / 案例 |
| 工信部 miit.gov.cn | 网页 | 产业+标准合规 |
| 中国人大网 npc.gov.cn | 网页 | 立法；建议国内机抓 |
| 司法部 moj.gov.cn | 网页 | 需国内网络复验 |
| 中国政府网 gov.cn | 网页 | 多部门规章入口 |
| 法治日报 / 法制网 | 网页 | 权威报道 |

### 中文 · 公众号 P0（约 6，需你补 `__biz`）

| 公众号 | 主线 | 备注 |
|---|---|---|
| 数字法律研究 | A | 工作日要闻，优先 |
| 数字治理全球洞察 | A | 全球治理译文 |
| 中国政法大学人工智能法研究院 | A | 立法/学术 |
| 人大未来法治研究院 | A+B | 活动通知降权 |
| 网信中国 | A | 与官网去重 |
| 最高人民法院 | A+B | 与官网去重 |

P1 候选：中国民商法律网（强过滤）、以及你日常在看的 2–4 个法律科技号（表里留了占位）。

## 刻意不进 P0 的

- Law.com / Bloomberg Law 等**付费墙重**源 → P2，有预算再谈授权
- CourtListener 全量案件 → P2 专题，不做日报主源
- 通用 TechCrunch / The Decoder 全量 → 只作 P1 且强过滤
- 公众号爆文榜、二手搬运号 → 不做

## 你需要尽快确认/补全的字段

写在 YAML 的 `awaiting_owner` / `needs_wechat_id` 上，汇总如下：

1. **微信公众号**：每个号的准确名称 + `__biz`（或你现成的抓取通道）
2. **中文 LegalTech 媒体号**：你认为值得追的 2–4 个（我故意留空，避免我替你选营销号）
3. **国产厂商优先级**：智谱 / Kimi / DeepSeek / 通义 / 百度 / 商汤……保留哪些进 Vendor Frontier
4. **X 账号**：是否要上 X（要 API 成本）；若上，中英各给 3–5 个必追账号
5. **双主线比例**：建议日报默认 **A:B ≈ 55:45**，厂商研究单独最多占精选 15%——若你有不同偏好请说

## 接入优先级（工程顺序）

> **出境约束**：阿里云深圳机默认难访境外站。P0 英文 RSS/网页约占一半，**无代理时不要假定能抓到**。详见 [`../deploy/EGRESS.md`](../deploy/EGRESS.md)。

1. **先接通国内 P0**（官网网页 + 公众号）——深圳机可直连  
2. **再接通境外 P0 RSS**（需 HTTP 代理或海外 fetcher）  
3. **OpenAI RSS + Anthropic 网页**（同样走代理；厂商加权）  
4. **过滤后的通用科技媒体 + arXiv**（代理）  
5. X / CourtListener / 付费库（二期）
