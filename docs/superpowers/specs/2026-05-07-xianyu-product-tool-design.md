# 闲鱼选品工具 — 设计规格说明

## 概述

闲鱼选品工具是一个 Web 应用，帮助小团队按行业/类目查询闲鱼平台上的爆款商品。
综合"想要增速、价格优势、互动率、发布时间"四个维度计算爆款指数，支持闲鱼原生
类目和自定义行业标签两种浏览方式。

## 技术栈

- **后端**: Python FastAPI + SQLAlchemy 2.0 + Alembic + APScheduler
- **数据库**: PostgreSQL（商品/用户数据）+ Redis（排行榜缓存、爬虫去重）
- **爬虫**: httpx（L1 快速抓取）+ Playwright（L2 浏览器降级）
- **前端**: Vite + React + TypeScript + Ant Design + Recharts
- **部署**: docker-compose 管理 PostgreSQL + Redis，Python 和前端单独部署

## 架构

```
┌─────────────┐     ┌──────────────────────────────────┐
│  React SPA  │────▶│  FastAPI (API + 静态文件服务)      │
│  (Nginx/    │     │                                   │
│   Vite)     │     │  ┌──────────┐  ┌───────────────┐  │
└─────────────┘     │  │ 爬虫调度  │  │  爆款评分引擎  │  │
                    │  │ (httpx + │  │               │  │
                    │  │  Playwright│  │  多维加权排序  │  │
                    │  │  降级)    │  │               │  │
                    │  └──────────┘  └───────────────┘  │
                    │          │            │           │
                    │     ┌────┴────────────┴─────┐     │
                    │     │  PostgreSQL + Redis    │     │
                    │     └────────────────────────┘     │
                    └──────────────────────────────────┘
```

单 FastAPI 进程：API 路由 + APScheduler 定时爬虫调度 + 评分计算，无需额外的
Worker 进程。

## 用户系统

小团队共享模式，简单账号密码登录（JWT），无复杂权限。一个团队一个数据库，
所有成员共享数据视图。

## 数据模型

### products（商品表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| xianyu_id | VARCHAR | 闲鱼商品 ID，去重用 |
| title | VARCHAR(500) | 商品标题 |
| price | DECIMAL | 售价（元） |
| original_price | DECIMAL | 原价（如有） |
| images | JSONB | 图片 URL 列表 |
| seller_name | VARCHAR | 卖家昵称 |
| seller_level | VARCHAR | 卖家信用等级 |
| want_count | INT | 想要数 |
| view_count | INT | 浏览量 |
| category | VARCHAR | 闲鱼类目 |
| tags | JSONB | 自定义行业标签 |
| publish_time | TIMESTAMP | 发布时间 |
| fetched_at | TIMESTAMP | 抓取时间 |

### hot_scores（爆款评分表）

| 字段 | 类型 | 说明 |
|------|------|------|
| product_id | FK → products | |
| score | FLOAT | 综合爆款指数 (0-100) |
| want_velocity | FLOAT | 想要增速（每小时增量） |
| price_advantage | FLOAT | 价格优势分 |
| engagement_rate | FLOAT | 互动率 |
| calculated_at | TIMESTAMP | 计算时间 |

### users（用户表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | VARCHAR(50) | 唯一 |
| password_hash | VARCHAR(255) | bcrypt 哈希 |
| created_at | TIMESTAMP | |

### crawl_tasks（爬取任务表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| keyword | VARCHAR(200) | 搜索关键词 |
| category | VARCHAR(100) | 行业/类目 |
| status | VARCHAR(20) | pending/running/done/failed |
| items_found | INT | 本次抓取商品数 |
| level | VARCHAR(10) | L1/L2/L3 使用的策略 |
| error | TEXT | 错误信息 |
| started_at/ended_at | TIMESTAMP | |

## 爆款评分公式

```
hot_score = want_velocity×0.4 + price_advantage×0.25 + engagement_rate×0.2 + freshness×0.15
```

每个维度归一化到 0-100：

- **want_velocity**: (本次想要数 - 上次想要数) ÷ 间隔小时数，按品类分位数归一化
- **price_advantage**: 同品类均价 ÷ 该商品价格，截断到 [0.5, 2.0] 后归一化
- **engagement_rate**: want_count ÷ view_count，按品类分位数归一化
- **freshness**: 24h 内 = 100，24h-3d = 80，3d-7d = 50，>7d = 20

权重通过 `config.py` 配置，可调整。

## API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录获取 JWT |
| GET | `/api/categories` | 获取闲鱼类目 + 自定义行业标签列表 |
| GET | `/api/products/search` | 搜索/筛选商品（?keyword=&category=&industry=&page=&sort=） |
| GET | `/api/products/hot` | 爆款排行榜（?category=&industry=&limit=50） |
| GET | `/api/products/:id` | 商品详情 + 评分历史 |
| POST | `/api/crawl/trigger` | 手动触发爬取（body: keyword, category） |
| GET | `/api/crawl/status` | 最近爬取任务列表 |

## 前端页面

| 路由 | 页面 | 核心功能 |
|------|------|---------|
| `/` | 首页仪表盘 | 各行业爆款概览卡片、最近爬取状态 |
| `/search` | 搜索页 | 关键词输入 + 行业/类目筛选 + 排序 + 商品卡片列表 |
| `/hot/:industry` | 行业爆款榜 | 排行榜表格 + 价格分布图 + 想要增量曲线 |
| `/tasks` | 爬虫管理 | 触发爬取、查看任务历史、重跑失败任务 |

## 爬虫策略

### 三层降级

```
L1: httpx 直接请求闲鱼移动端搜索页（m. 域名），解析返回的商品数据
    └── 正常情况处理 90% 请求

L2: Playwright 无头 Chromium，模拟真实用户行为
    └── 触发条件：L1 返回空、检测验证码、连续 3 次失败

L3: 冷却 + 重试
    └── 连续 5 次失败 → 冷却 30 分钟 → 继续
```

### 反爬手段

- UA 轮换池（20+ 移动端 User-Agent）
- 请求间隔随机 3-8 秒
- Redis 记录关键词抓取频率，同一关键词 15 分钟内不重复请求
- 不登录、不碰用户隐私、仅抓公开搜索页数据

## 定时任务

通过 APScheduler 内嵌在 FastAPI 进程：

- **每日定时爬取**: 每天 8:00、14:00、20:00 自动对配置的热门关键词列表执行爬取
- **爆款评分重算**: 每次爬取完成后自动触发评分重算
- **老旧数据清理**: 每天 3:00 清理 30 天前的评分记录

## 错误处理

- API 层：全局异常中间件，统一返回 `{error: string, code: int}` 格式
- 爬虫层：L1→L2→L3 自动降级，每次降级记录日志
- 前端：API 请求失败展示 Ant Design Message 提示，表格/列表有 Loading/Empty/Error 三态

## 测试策略

- 后端：pytest + httpx AsyncClient 测试 API 路由，pytest-asyncio 测试爬虫逻辑
- 评分引擎：单元测试覆盖四个维度和边界情况（价格为 0、浏览量为 0 等）
- 前端：Vite 默认测试框架，关键页面渲染测试 + API mock
- 爬虫测试用录制的 HTML fixture，不发起真实网络请求

## 项目结构

```
xianyu-tool/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── product.py
│   │   │   ├── hot_score.py
│   │   │   ├── user.py
│   │   │   └── crawl_task.py
│   │   ├── schemas/
│   │   │   ├── product.py
│   │   │   ├── user.py
│   │   │   └── crawl.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── products.py
│   │   │   ├── categories.py
│   │   │   └── crawl.py
│   │   ├── services/
│   │   │   ├── scorer.py
│   │   │   ├── crawler.py
│   │   │   └── category.py
│   │   ├── crawlers/
│   │   │   ├── base.py
│   │   │   ├── httpx_crawler.py
│   │   │   └── playwright_crawler.py
│   │   └── tasks/
│   │       └── scheduler.py
│   ├── alembic/
│   │   └── versions/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── docker-compose.yml
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Search.tsx
│   │   │   ├── HotRanking.tsx
│   │   │   └── Tasks.tsx
│   │   ├── components/
│   │   │   ├── ProductCard.tsx
│   │   │   ├── HotTable.tsx
│   │   │   ├── TrendChart.tsx
│   │   │   └── Layout.tsx
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
└── docs/
    └── superpowers/specs/
        └── 2026-05-07-xianyu-product-tool-design.md
```
