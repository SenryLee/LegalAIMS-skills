# LawHOT 改造路径与内容中台方案

目标：**抄 aihot 的骨架，换法律 AI 的血肉**。  
本文件回答两件事：后续怎么改 skill / 中台；你需要准备什么来配合。

## 1. 和建议的落地切分

```
┌─────────────────────────────────────────────┐
│  A. Skill 包（本仓库 lawhot/）                 │
│     SKILL.md · references · install · RSS说明 │
│     = Agent 怎么问、调哪个 API、怎么写简报      │
└──────────────────▲──────────────────────────┘
                   │ 匿名只读 HTTPS
┌──────────────────┴──────────────────────────┐
│  B. 内容中台（你的服务器 / 域名）               │
│     抓取 → 清洗 → LLM 摘要打分 → 精选/热点/日报 │
│     对外：/api/v1/* · /feed/*.xml · 简易网页    │
└──────────────────▲──────────────────────────┘
                   │
┌──────────────────┴──────────────────────────┐
│  C. 信源层（sources.v1.yaml）                  │
│     RSS / 网页 / 公众号 /（可选）X / API        │
└─────────────────────────────────────────────┘
```

- **Skill 可以先写「合同」**（端点形状对齐 aihot），但**没有中台就没有实时资讯**。
- **中台是主工程**；信源表是中台的第一份配置。

## 2. 建议分三期，而不是一次做完

### 第 0 期 · 现在（已开始）

- [x] 信源注册表 `references/sources.v1.yaml`
- [x] 人类执行版 `references/sources.md`
- [ ] 你确认公众号 / 国产厂商 / 主线比例（见文末清单）

### 第 1 期 · MVP（可对外试用）

**中台最小闭环：**

1. 定时拉 P0 RSS + 少量网页源  
2. 归一化条目（title / url / publishedAt / source / lang / track）  
3. LLM：中文摘要 + 主线分类 + 0–100 分 + 「对律师/法务的一句话启示」  
4. 精选池 + 最近 7 天公开池  
5. 对外只读 API（先对齐 aihot 子集）：
   - `GET /api/v1/items`
   - `GET /api/v1/dailies/latest`（可先人工/半自动）
6. Skill：`SKILL.md` 只打上述 API，安全边界照抄 aihot  

**先不做：** hot-topics 多源聚合、snapshot 同步、周月报、全文站内阅读、X。

### 第 2 期 · 编辑部能力

- 热点多源（同一监管事件：官网 + IAPP + 中文解读）
- 微信公众号稳定接入
- Anthropic 等无 RSS 源的稳健网页抽取
- 日报自动化（每天固定北京时间）
- RSS 对外订阅（精选 / 日报）
- 简易精选网页（可选，Skill 可先不依赖网页）

### 第 3 期 · 增强

- selected snapshot/changes  
- 管辖标签（CN/US/EU/…）与法条引用核验提示  
- CourtListener / 付费库专题  
- 周报月报  

## 3. 内容中台「怎么做」——推荐技术形状

不必复刻 aihot 内部实现，对外合同尽量像，方便 Agent 生态复用心智。

| 模块 | 推荐做法 | 备注 |
|---|---|---|
| 运行环境 | 阿里云「法锤智能」ECS（深圳，Ubuntu 22.04，**2C2G**）+ Docker Compose；nginx 复用本机 | 详见 [`deploy/DNS.md`](./deploy/DNS.md)；内存紧，单栈部署 |
| 数据 | MVP 可用 SQLite 或限内存 Postgres；暂缓 Redis | 2G 机器先省资源，量上来再拆 |
| 抓取 | RSS 用标准解析；网页用站点适配器；公众号单独适配器 | 每源一个 connector，失败隔离 |
| 任务 | cron / 队列 worker，P0 源 15–60 分钟一轮 | 官方源可更频，媒体源更慢 |
| LLM | 你指定的 API（摘要/分类/打分） | 提示词要强调：非法律意见、数字回原文 |
| API | 匿名只读 JSON + ETag + Problem JSON | 直接借鉴 aihot v1 字段命名 |
| 前端 | MVP 可无；有余力再做精选列表 | Skill 优先 |

**目录级工作拆分（中台仓库，可另开 repo）：**

```text
connectors/     # rss_openai.py, web_anthropic.py, web_cac.py, wechat_*.py
pipeline/       # normalize → score → select → dedupe
api/            # FastAPI/Next Route handlers
jobs/           # daily report
skill-export/   # 生成/同步到本仓库 lawhot/
```

## 4. Skill 改造具体改什么（相对 aihot）

| aihot | LawHOT 应对 |
|---|---|
| 域名 `aihot.virxact.com` | 你的新域名，如 `lawhot.example.com` |
| 分类 `ai-models/.../tip` | `regulation` / `litigation` / `legaltech` / `practice` / `insight` / `vendor` |
| 输出「AI 圈重点」 | 「法律 AI 重点」+ **启示句** + 管辖提示 |
| 触发词 AI 日报/OpenAI | 法律 AI / AI Act / 智慧法院 / LegalTech… |
| 安全边界 | 额外：**不得给出法律意见**；条文/判词强制回原文 |

Skill 文件预计：

```text
lawhot/
  SKILL.md
  README.md
  agents/openai.yaml
  references/api.md
  references/errors.md
  references/sources.md          # 已有
  references/sources.v1.yaml     # 已有
  install.sh                     # 二期
```

**注意：** 在中台 API 未上线前，不要发布「假装能查实时资讯」的 Skill；可先保持本目录为「筹备包」。

## 5. 你需要提供 / 确认的清单

### 必须有（否则中台空转）

| 项 | 为什么 | 建议 |
|---|---|---|
| **服务器** | 跑抓取、DB、API | ✅ 已定：阿里云 `47.119.184.45`（法锤智能，2C2G）。Workbench 免密由你操作，我出一键脚本 |
| **域名** | Skill/API 稳定入口、HTTPS | ✅ 主域 `fachuiai.com` 已占用工作台 → 资讯用 **`hot.fachuiai.com`**（见 [`deploy/DNS.md`](./deploy/DNS.md)） |
| **DNS / 安全组** | 解析与 80/443 | 你加 `hot` A 记录 + 放行 80/443 |
| **HTTPS 证书** | Agent/浏览器信任 | 复用本机 nginx + certbot 签 `hot.fachuiai.com` |
| **LLM API Key** | 摘要、分类、打分、日报 | 指定厂商与月预算上限 |
| **信源确认** | 尤其是微信 `__biz`、国产厂商取舍 | 见 `sources.md` |

### 强烈建议有

| 项 | 为什么 |
|---|---|
| **对象存储 / 备份** | 日报与快照备份 |
| **监控告警** | 抓取失败、API 5xx（邮箱/飞书机器人） |
| **内容免责声明文案** | 站点与 Skill 页脚：「资讯聚合，非法律意见」 |
| **ICP / 合规** | 若对国内公众提供 Web；纯内网/个人 Agent 可另议 |

### 可选（二期再定）

| 项 | 为什么 |
|---|---|
| X API 或第三方转发 | 厂商/监管账号一手快讯 |
| 微信稳定抓取方案 | 自建 / 第三方；涉及稳定性与合规，需你拍板 |
| 单独中台 git 仓库 | 与 skills 仓库解耦，更干净 |
| 品牌名 / Logo / 简介 | 网页与 Skill `display_name` |

### 我不需要你现在就给的

- aihot 的源码或数据库  
- 付费法律数据库账号（P2）  
- 完整前端设计稿（MVP 可纯 API + Skill）

## 6. 推荐协作节奏（你 ↔ Agent）

1. **你**：DNS 添加 `hot.fachuiai.com`、安全组放行 80/443；确认 LLM 与公众号清单  
2. **我**：定 API 合同草案 + Skill `SKILL.md` 骨架（base URL = `https://hot.fachuiai.com`）  
3. **我**：写出中台 MVP + `deploy/one-click.sh`；**你在 Workbench 粘贴执行**  
4. **你**：抽 2–3 天人工过精选，校准打分与主线比例  
5. **我**：接通日报 + 正式 Skill 安装包；用公网 URL 验收  

## 7. 风险与边界（提前说清）

- **法律域容错更低**：摘要出错的成本高于普通 AI 资讯；必须「回原文」与非法律意见声明。  
- **公众号/官网版权**：默认摘要+链接，不镜像全文；付费源不进公开 RSS 全文。  
- **中英文时效差**：监管原文常「中文官媒慢、英文评论快」——沿用 aihot 的 timeline/published 双口径。  
- **不要寄生 aihot API 做法律站**：源不对，关键词过滤救不了垂直度。

## 8. 下一步我可以立刻做的（等你回复清单后）

当你提供第 5 节「必须有」里能定的几项后，下一刀建议是：

1. 写 `lawhot/SKILL.md` 骨架（分类、触发词、输出模板、安全边界）  
2. 写 `references/api.md` 合同（可与 aihot 字段对齐，换 base URL）  
3. 你完成 `hot.fachuiai.com` DNS 后，我交付中台 MVP + Workbench 一键脚本  

域名与服务器细则：[`deploy/DNS.md`](./deploy/DNS.md)。信源待确认项仍见 `sources.md`。
