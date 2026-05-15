# 闲鱼选品工具 (Xianyu Product Research Tool)

按行业/类目查询闲鱼平台爆款商品，综合"想要数"和"发布时间"计算热度排序。

## 功能

- **分行业爆款榜** — 12 个类目 + 自定义行业，热度排序
- **关键词搜索** — 输入关键词实时爬取闲鱼搜索结果
- **一键爬取** — 首页每分类一键触发爬虫
- **数据导出** — CSV 导出 + 一键复刻商品信息
- **热度评分** — want_count / days_since_publish

## 技术栈

- **后端**: Python FastAPI + SQLAlchemy + SQLite
- **前端**: React 18 + TypeScript + Ant Design 5 + Recharts
- **爬虫**: Playwright (visible browser)

## 快速启动

```bash
# 1. 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

# 2. 前端
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173，登录 admin / admin123。

## 使用流程

1. **爬虫管理** → 新建任务 → 输入关键词 → Chrome 弹出自动爬取
2. **首页** → 点分类"一键爬取"批量获取数据
3. **爆款榜** → 按热度/发布时间筛选查看
4. **搜索** → 关键词搜索已有数据
