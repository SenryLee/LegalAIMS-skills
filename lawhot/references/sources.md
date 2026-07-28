# LawHOT 信源名单 v0.2（可落地）

机器可读完整表见同目录 [`sources.v1.yaml`](./sources.v1.yaml)。本文是给人看的执行版。

**更新日期**：2026-07-28  
**相对 v0.1**：拆细 OpenAI/Anthropic 研究子频道；补 NIST / EU AI Office / UK AISI / 版权局；Legaltech Hub、Import AI、Daily Papers；中文法研/智合等；**明确排除一切付费墙源**。

## 定位

- **主线 A · Law × AI**：监管、立法、诉讼、合规（AI 如何被法律规制）
- **主线 B · AI × Law**：LegalTech 产品、律所落地、司法智能化（AI 如何改变法律行业）
- **加权线 · Vendor Frontier**：OpenAI / Anthropic / Google DeepMind / Microsoft 等**研究、安全、政策**一手文（入库时过滤掉纯营销）

原则：**中英大致各半**；厂商源「少而精、高权重」；通用 AI 资讯强过滤，可与 [aihot](../../aihot/) 聚合层互补，避免重复全量抓取。

## 硬约束 · 不接入付费源

| 排除 | 原因 |
|---|---|
| Law.com Legaltech News | 付费墙重 |
| Bloomberg Law / Law360 | 订阅库 |
| The Information / SemiAnalysis 付费层 | 订阅 |
| Lexis / Westlaw 全文库 | 版权与授权 |
| 其他会员墙全文 | 只收公开标题/摘要+外链时另议 |

公开 RSS、官网、官方 PDF（System Card 等）、免费 API（CourtListener）可以进。

## P0 首批（建议先接通）

### 英文 · 法律垂直 / 监管 / 学术（约 22）

| 信源 | 接入 | 主线 | 说明 |
|---|---|---|---|
| Artificial Lawyer | RSS | A+B | Legal AI 主源 |
| Legal IT Insider | RSS | B | 老牌法律科技 |
| LawSites / LawNext | RSS | B | Bob Ambrogi |
| **Legaltech Hub** | 网页 | B | **v0.2 新增**；GenAI map / 调研 |
| Everlaw Blog | RSS | B | eDiscovery |
| Clio Blog | RSS | B | 滤营销 |
| Thomson Reuters Legal Posts | RSS | A+B | 关键词收窄 |
| IAPP News | 网页 | A | 隐私 × AI |
| FTC Press | RSS | A | 需过滤 |
| GovTech AI | RSS | A+B | 法院/州政府 AI |
| **NIST AI RMF / AIRC** | 网页 | A | **v0.2**；美方治理金标准 |
| **US AI Safety Institute** | 网页 | A | **v0.2** |
| **US Copyright Office · AI** | 网页 | A | **v0.2**；训练数据/版权 |
| EU AI Act / EC 政策页 | 网页 | A | |
| **EU AI Office** | 网页 | A | **v0.2**；实施细则 |
| **UK AISI** | 网页 | A | **v0.2**；独立评测 |
| OECD.AI | 网页 | A | |
| Stanford HAI News | 网页 | A | RSS 不稳，按网页 |
| **Stanford CodeX** | 网页 | A+B | **v0.2** |
| **Berkman Klein Center** | 网页 | A | **v0.2** |
| MIT Tech Review · AI | RSS | A | 需过滤；公开页 |
| arXiv cs.CY | RSS | A | 法律词过滤 |

Federal Register AI 仍在表中，**默认 P2**（噪声大）。

### 英文 · OpenAI / Anthropic 研究（重点拆细，约 14）

| 信源 | 接入 | 说明 |
|---|---|---|
| OpenAI News | RSS `openai.com/news/rss.xml` | 排除客户案例 |
| **OpenAI Research / Publications** | 网页 | **v0.2** |
| **OpenAI Safety & Responsibility** | 网页 | **v0.2** |
| **OpenAI System Cards** | 网页/PDF | **v0.2** |
| **OpenAI Preparedness Framework** | 网页 | **v0.2** |
| **OpenAI Model Spec** | 网页 | **v0.2** |
| **OpenAI Global Affairs / Policy** | 网页 | **v0.2** |
| Anthropic Newsroom | 网页 | 无 RSS |
| Anthropic Research | 网页 | 总入口 |
| **Anthropic Alignment Blog** | 网页 | **v0.2** `alignment.anthropic.com` |
| **Anthropic Economic Index** | 网页/PDF | **v0.2** |
| **Anthropic System Cards / Risk Reports** | 网页/PDF | **v0.2** |
| **Anthropic Policy / Societal Impact** | 网页 | **v0.2** |
| Anthropic Engineering | 网页 | P1 |

OpenAI Blog 兼容 RSS 仍为 P1（与 News 去重）。

### 英文 · 其他头部厂商 + 高信号 AI 动态

| 信源 | 接入 | 说明 |
|---|---|---|
| Google DeepMind Blog | RSS | 研究向过滤 |
| Google Blog · AI | RSS | 滤营销 |
| Microsoft Research | RSS | 法律/Copilot 收窄 |
| **Import AI (Jack Clark)** | 网页/newsletter | **v0.2 P0**；研究周报 |
| **Hugging Face Daily Papers** | 网页 | **v0.2 P0**；法律词过滤 |
| Meta AI Blog | 网页 | P1；开源许可 |
| Hugging Face Blog | RSS | P1 |
| Mistral News | 网页 | P1 |

### 中文 · 官方 / 权威

| 信源 | 接入 | 说明 |
|---|---|---|
| 国家网信办 cac.gov.cn | 网页 | 核心监管原文 |
| 最高人民法院 court.gov.cn | 网页 | 司法 AI / 案例 |
| 工信部 miit.gov.cn | 网页 | 产业+标准 |
| 中国人大网 npc.gov.cn | 网页 | 立法 |
| 司法部 moj.gov.cn | 网页 | 需国内网络 |
| 中国政府网 gov.cn | 网页 | 多部门规章入口 |
| 法治日报 / 法制网 | 网页 | 权威报道 |
| 中国法院网 | 网页 | 智慧法院 |
| **中国司法大数据研究院 / 司法大数据服务网** | 网页 | **v0.2 P0** |
| 最高检 spp.gov.cn | 网页 | P1；数字检察 |
| 市监总局 / TC260 | 网页 | P1；标准 |

### 中文 · 公众号 P0（需补 `__biz`）

| 公众号 | 主线 | 备注 |
|---|---|---|
| 数字法律研究 | A | 工作日要闻 |
| 数字治理全球洞察 | A | 全球治理译文 |
| 中国政法大学人工智能法研究院 | A | 立法/学术 |
| 人大未来法治研究院 | A+B | 活动通知降权 |
| 网信中国 | A | 与官网去重 |
| 最高人民法院 | A+B | 与官网去重 |

P1：中国民商法律网（强过滤）、**智合**（网页+公众号，滤软文）。

### 中文 · 行业 / 媒体（P1）

| 信源 | 说明 |
|---|---|
| 正义网 | 数字检察 |
| 安全内参 | 法律交叉过滤 |
| 智合 | LegalTech 行业动态 |
| LexisNexis 中国法律洞察 | 公开博客，摘要+外链 |
| 机器之心 / 量子位 | **强过滤**法律/监管交叉 |

## P1 扩展（稳定后接通）

- **监管**：UK ICO AI、EDPB、CNIL、CoE AI、USPTO/EPO AI  
- **智库/评测**：Ada Lovelace、METR、FLI、Stanford CRFM/HELM、SSRN Legal AI  
- **LegalTech 厂商**（滤营销）：Harvey、Legora、Relativity、iManage、NetDocuments、Lexis Insights  
- **实务协会**：ABA Journal Tech、ILTA、Legal Dive  
- **通用 AI**：TechCrunch AI、The Decoder、The Batch、HN 关键词 API  
- **国产厂商**：智谱、Kimi、DeepSeek、通义（研究/安全向）

## P2 观察池

- Above the Law、White House 全站 RSS（噪声大）  
- CourtListener（**AI 案件专题**，非日报主源）  
- UNESCO AI Ethics、G7 Hiroshima 公开材料、ISO 42001 间接动态  
- Wired / Ars 等通用科技（强过滤）  
- xAI、百川、讯飞、智源等观察性厂商/机构  

## 刻意不做

- 付费墙 / 订阅库全文  
- 公众号爆文榜、二手搬运号  
- 通用 AI 全量刷屏（用过滤 + aihot 互补）  
- CourtListener 全量案件当日进精选  

## 仍待你补全的字段

写在 YAML 的 `needs_wechat_id` / `needs_x_access` / `needs_url`：

1. **微信公众号** `__biz`（或现成抓取通道）  
2. **X API** 是否开通（账号包已写在 `zh-x-priority-accounts`）  
3. **国产厂商栏目 URL** 定点（智谱研究页等）  
4. 日报默认 **A:B ≈ 55:45**，厂商研究占精选上限约 **15%**——若要改请说  

## 接入优先级（工程顺序）

> **出境约束**：阿里云深圳机默认难访境外站。P0 英文约占一半，**无代理时不要假定能抓到**。详见 [`../deploy/EGRESS.md`](../deploy/EGRESS.md)。

1. **国内 P0**（官网网页 + 公众号 + 法研）——深圳机可直连  
2. **境外 P0 RSS**（需 HTTP 代理或海外 fetcher）  
3. **OpenAI RSS + Anthropic/OpenAI 研究子频道网页**（代理；厂商加权）  
4. **NIST / EU AI Office / UK AISI / 版权局** 网页  
5. **Import AI + Daily Papers + arXiv**（代理；过滤）  
6. P1 厂商博客 / 智库 / 中文媒体  
7. X / CourtListener 专题（二期）  

## 统计（约数）

| 层级 | 约数 |
|---|---|
| P0 | ~55 |
| P1 | ~40 |
| P2 | ~15 |
| **合计** | **~110** |

完整字段、过滤规则与 seed 说明以 [`sources.v1.yaml`](./sources.v1.yaml) 为准。
