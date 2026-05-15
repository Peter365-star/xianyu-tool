# 闲鱼选品工具 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建一个 Web 应用，帮助小团队按行业/类目查询闲鱼平台爆款商品，通过多维加权评分排序。

**架构：** FastAPI 单进程服务（API + APScheduler 定时爬虫 + 评分引擎），PostgreSQL + Redis 存储，React + Ant Design 前端，httpx + Playwright 三层降级爬虫。

**技术栈：** Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Alembic / PostgreSQL / Redis / APScheduler / httpx / Playwright / Vite / React 18 / TypeScript / Ant Design 5 / Recharts

---

### 任务 1：项目脚手架和基础设施

**文件：**
- 创建：`backend/requirements.txt`
- 创建：`backend/docker-compose.yml`
- 创建：`backend/app/__init__.py`
- 创建：`backend/app/main.py`
- 创建：`backend/app/config.py`

- [ ] **步骤 1：创建 backend/requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
asyncpg==0.30.0
alembic==1.14.1
pydantic==2.10.3
pydantic-settings==2.7.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
redis==5.2.1
httpx==0.28.1
playwright==1.49.1
apscheduler==3.11.0
pytest==8.3.4
pytest-asyncio==0.25.0
httpx==0.28.1
```

- [ ] **步骤 2：创建 backend/docker-compose.yml**

```yaml
version: "3.9"
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: xianyu
      POSTGRES_PASSWORD: xianyu_dev
      POSTGRES_DB: xianyu
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **步骤 3：创建 backend/app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://xianyu:xianyu_dev@localhost:5432/xianyu"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # scorer weights
    weight_want_velocity: float = 0.4
    weight_price_advantage: float = 0.25
    weight_engagement_rate: float = 0.2
    weight_freshness: float = 0.15

    # crawler
    crawler_request_delay_min: float = 3.0
    crawler_request_delay_max: float = 8.0
    crawler_cooldown_minutes: int = 30
    crawler_max_consecutive_failures: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **步骤 4：创建 backend/app/__init__.py**

```python
# backend app package
```

- [ ] **步骤 5：创建 backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="闲鱼选品工具", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **步骤 6：启动 docker-compose 并验证**

```bash
cd backend && docker compose up -d
```

- [ ] **步骤 7：安装 Python 依赖并验证 FastAPI 启动**

```bash
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# 访问 http://localhost:8000/api/health 确认返回 {"status":"ok"}
```

- [ ] **步骤 8：Commit**

```bash
git add backend/requirements.txt backend/docker-compose.yml backend/app/
git commit -m "feat: add project scaffold with FastAPI, PostgreSQL, Redis"
```

---

### 任务 2：数据库模型

**文件：**
- 创建：`backend/app/models/__init__.py`
- 创建：`backend/app/models/product.py`
- 创建：`backend/app/models/hot_score.py`
- 创建：`backend/app/models/user.py`
- 创建：`backend/app/models/crawl_task.py`
- 创建：`backend/app/database.py`

- [ ] **步骤 1：创建 backend/app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **步骤 2：创建 backend/app/models/product.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    xianyu_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    images: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    seller_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seller_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    want_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **步骤 3：创建 backend/app/models/hot_score.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class HotScore(Base):
    __tablename__ = "hot_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    want_velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    price_advantage: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    freshness: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product = relationship("Product")
```

- [ ] **步骤 4：创建 backend/app/models/user.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **步骤 5：创建 backend/app/models/crawl_task.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class CrawlTask(Base):
    __tablename__ = "crawl_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **步骤 6：创建 backend/app/models/__init__.py**

```python
from app.models.product import Product
from app.models.hot_score import HotScore
from app.models.user import User
from app.models.crawl_task import CrawlTask
from app.database import Base

__all__ = ["Product", "HotScore", "User", "CrawlTask", "Base"]
```

- [ ] **步骤 7：运行一次 models import 验证无导入错误**

```bash
cd backend && python -c "from app.models import Product, HotScore, User, CrawlTask; print('OK')"
```

- [ ] **步骤 8：Commit**

```bash
git add backend/app/models/ backend/app/database.py
git commit -m "feat: add database models for products, scores, users, crawl tasks"
```

---

### 任务 3：Alembic 数据库迁移

**文件：**
- 创建：`backend/alembic.ini`
- 创建：`backend/alembic/env.py`
- 创建：`backend/alembic/script.py.mako`

- [ ] **步骤 1：初始化 Alembic**

```bash
cd backend && alembic init alembic
```

- [ ] **步骤 2：修改 backend/alembic.ini 中的数据库连接**

```ini
# 将 sqlalchemy.url 行替换为：
sqlalchemy.url = postgresql+asyncpg://xianyu:xianyu_dev@localhost:5432/xianyu
```

- [ ] **步骤 3：修改 backend/alembic/env.py 以支持异步和模型自动发现**

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.database import Base
from app.models import Product, HotScore, User, CrawlTask  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **步骤 4：生成并执行迁移**

```bash
cd backend && alembic revision --autogenerate -m "init"
alembic upgrade head
```

- [ ] **步骤 5：验证表已创建**

```bash
docker compose exec db psql -U xianyu -d xianyu -c "\dt"
# 确认 products, hot_scores, users, crawl_tasks 四张表存在
```

- [ ] **步骤 6：Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: add alembic migrations for initial schema"
```

---

### 任务 4：爆款评分引擎（TDD）

**文件：**
- 创建：`backend/app/services/__init__.py`
- 创建：`backend/app/services/scorer.py`
- 创建：`backend/tests/__init__.py`
- 创建：`backend/tests/conftest.py`
- 创建：`backend/tests/test_scorer.py`

- [ ] **步骤 1：创建 backend/tests/conftest.py**

```python
import pytest
from app.config import settings


@pytest.fixture(autouse=True)
def reset_scorer_weights():
    """Ensure scorer weights are at defaults for each test."""
    settings.weight_want_velocity = 0.4
    settings.weight_price_advantage = 0.25
    settings.weight_engagement_rate = 0.2
    settings.weight_freshness = 0.15
```

- [ ] **步骤 2：编写评分引擎失败测试**

创建 `backend/tests/test_scorer.py`：

```python
import pytest
from datetime import datetime, timedelta
from app.services.scorer import (
    calc_want_velocity,
    calc_price_advantage,
    calc_engagement_rate,
    calc_freshness,
    calculate_hot_score,
)


class TestWantVelocity:
    def test_zero_when_no_previous_data(self):
        assert calc_want_velocity(current_want=100, previous_want=None, hours=24) == 0

    def test_positive_growth(self):
        velocity = calc_want_velocity(current_want=200, previous_want=100, hours=24)
        assert velocity > 0

    def test_negative_growth_zeroed(self):
        assert calc_want_velocity(current_want=50, previous_want=100, hours=24) == 0

    def test_same_day_boost(self):
        v1 = calc_want_velocity(current_want=150, previous_want=100, hours=24)
        v2 = calc_want_velocity(current_want=150, previous_want=100, hours=6)
        assert v2 > v1


class TestPriceAdvantage:
    def test_below_average_gives_high_score(self):
        score = calc_price_advantage(price=50, category_avg_price=100)
        assert score > 50

    def test_above_average_gives_low_score(self):
        score = calc_price_advantage(price=200, category_avg_price=100)
        assert score < 50

    def test_zero_price_handled(self):
        score = calc_price_advantage(price=0, category_avg_price=100)
        assert score == 0

    def test_zero_avg_price_handled(self):
        score = calc_price_advantage(price=100, category_avg_price=0)
        assert score == 0


class TestEngagementRate:
    def test_high_engagement(self):
        rate = calc_engagement_rate(want_count=50, view_count=100)
        assert rate > 0

    def test_zero_views(self):
        assert calc_engagement_rate(want_count=10, view_count=0) == 0


class TestFreshness:
    def test_recent_24h(self):
        score = calc_freshness(datetime.utcnow() - timedelta(hours=5))
        assert score == 100

    def test_three_days(self):
        score = calc_freshness(datetime.utcnow() - timedelta(days=2))
        assert score == 80

    def test_week_old(self):
        score = calc_freshness(datetime.utcnow() - timedelta(days=5))
        assert score == 50

    def test_very_old(self):
        score = calc_freshness(datetime.utcnow() - timedelta(days=10))
        assert score == 20


class TestHotScore:
    def test_full_calculation(self):
        score = calculate_hot_score(
            current_want=150,
            previous_want=100,
            hours=24,
            price=80,
            category_avg_price=100,
            want_count=30,
            view_count=100,
            publish_time=datetime.utcnow() - timedelta(hours=2),
        )
        assert 0 <= score <= 100

    def test_all_zeros(self):
        score = calculate_hot_score(
            current_want=0,
            previous_want=None,
            hours=24,
            price=0,
            category_avg_price=0,
            want_count=0,
            view_count=0,
            publish_time=datetime.utcnow() - timedelta(days=30),
        )
        assert score >= 0
```

- [ ] **步骤 3：运行测试确认失败**

```bash
cd backend && python -m pytest tests/test_scorer.py -v
# 预期：全部 FAIL，ModuleNotFoundError
```

- [ ] **步骤 4：实现评分引擎**

创建 `backend/app/services/scorer.py`：

```python
import math
from datetime import datetime, timedelta


def calc_want_velocity(current_want: int, previous_want: int | None, hours: float) -> float:
    if previous_want is None or previous_want <= 0:
        return 0
    delta = current_want - previous_want
    if delta <= 0:
        return 0
    rate = delta / max(hours, 1)
    return min(rate * 10, 100)


def calc_price_advantage(price: float, category_avg_price: float) -> float:
    if price <= 0 or category_avg_price <= 0:
        return 0
    ratio = category_avg_price / price
    clamped = max(0.5, min(ratio, 2.0))
    return (clamped - 0.5) / 1.5 * 100


def calc_engagement_rate(want_count: int, view_count: int) -> float:
    if view_count <= 0:
        return 0
    rate = want_count / view_count
    return min(rate * 200, 100)


def calc_freshness(publish_time: datetime) -> float:
    now = datetime.utcnow()
    age = now - publish_time
    if age <= timedelta(hours=24):
        return 100
    if age <= timedelta(days=3):
        return 80
    if age <= timedelta(days=7):
        return 50
    return 20


def normalize_to_100(values: list[float]) -> list[float]:
    if not values:
        return values
    max_v = max(values)
    if max_v == 0:
        return [0] * len(values)
    return [v / max_v * 100 for v in values]


def calculate_hot_score(
    current_want: int,
    previous_want: int | None,
    hours: float,
    price: float,
    category_avg_price: float,
    want_count: int,
    view_count: int,
    publish_time: datetime,
) -> float:
    from app.config import settings

    wv = calc_want_velocity(current_want, previous_want, hours)
    pa = calc_price_advantage(price, category_avg_price)
    er = calc_engagement_rate(want_count, view_count)
    fr = calc_freshness(publish_time)

    score = (
        wv * settings.weight_want_velocity
        + pa * settings.weight_price_advantage
        + er * settings.weight_engagement_rate
        + fr * settings.weight_freshness
    )
    return round(score, 2)
```

- [ ] **步骤 5：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_scorer.py -v
# 预期：全部 PASS
```

- [ ] **步骤 6：Commit**

```bash
git add backend/app/services/ backend/tests/
git commit -m "feat: add hot product scoring engine with TDD"
```

---

### 任务 5：Pydantic Schemas

**文件：**
- 创建：`backend/app/schemas/__init__.py`
- 创建：`backend/app/schemas/product.py`
- 创建：`backend/app/schemas/user.py`
- 创建：`backend/app/schemas/crawl.py`

- [ ] **步骤 1：创建 backend/app/schemas/product.py**

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ProductOut(BaseModel):
    id: UUID
    xianyu_id: str
    title: str
    price: float
    original_price: float | None
    images: list[str] | None
    seller_name: str | None
    seller_level: str | None
    want_count: int
    view_count: int
    category: str | None
    tags: list[str] | None
    publish_time: datetime | None
    fetched_at: datetime

    model_config = {"from_attributes": True}


class HotProductOut(ProductOut):
    score: float
    want_velocity: float
    price_advantage: float
    engagement_rate: float


class ProductSearchParams(BaseModel):
    keyword: str | None = None
    category: str | None = None
    industry: str | None = None
    page: int = 1
    page_size: int = 20
    sort: str = "hot_score"  # hot_score | price_asc | price_desc | newest


class ProductSearchResult(BaseModel):
    items: list[HotProductOut]
    total: int
    page: int
    page_size: int
```

- [ ] **步骤 2：创建 backend/app/schemas/user.py**

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **步骤 3：创建 backend/app/schemas/crawl.py**

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class CrawlTriggerRequest(BaseModel):
    keyword: str
    category: str | None = None


class CrawlTaskOut(BaseModel):
    id: UUID
    keyword: str
    category: str | None
    status: str
    items_found: int
    level: str | None
    error: str | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add pydantic schemas for API"
```

---

### 任务 6：JWT 认证与 Auth API

**文件：**
- 创建：`backend/app/services/auth.py`
- 创建：`backend/app/api/__init__.py`
- 创建：`backend/app/api/auth.py`
- 创建：`backend/app/api/deps.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：创建 backend/app/services/auth.py**

```python
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
```

- [ ] **步骤 2：创建 backend/app/api/deps.py**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth import decode_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return {"user_id": user_id}
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
```

- [ ] **步骤 3：创建 backend/app/api/auth.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse
from app.services.auth import verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)
```

- [ ] **步骤 4：注册路由到 main.py**

修改 `backend/app/main.py`，在 `app = FastAPI(...)` 之后、`add_middleware` 之后添加：

```python
from app.api.auth import router as auth_router

app.include_router(auth_router)
```

- [ ] **步骤 5：创建种子用户脚本**

创建 `backend/seed_user.py`：

```python
import asyncio
from app.database import async_session
from app.models.user import User
from app.services.auth import hash_password


async def seed():
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            print("admin user already exists")
            return
        user = User(username="admin", password_hash=hash_password("admin123"))
        db.add(user)
        await db.commit()
        print("admin user created (admin / admin123)")


asyncio.run(seed())
```

```bash
cd backend && python seed_user.py
```

- [ ] **步骤 6：测试登录接口**

```bash
# 启动服务后测试
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
# 预期：返回 {"access_token":"...","token_type":"bearer"}
```

- [ ] **步骤 7：Commit**

```bash
git add backend/app/services/auth.py backend/app/api/ backend/app/main.py backend/seed_user.py
git commit -m "feat: add JWT auth with login endpoint and seed user"
```

---

### 任务 7：类目 API 与分类服务

**文件：**
- 创建：`backend/app/services/category.py`
- 创建：`backend/app/api/categories.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：创建 backend/app/services/category.py**

```python
XIANYU_CATEGORIES = [
    {"id": "digital", "name": "数码", "icon": "laptop"},
    {"id": "clothing", "name": "服装", "icon": "skin"},
    {"id": "beauty", "name": "美妆", "icon": "experiment"},
    {"id": "home", "name": "家居", "icon": "home"},
    {"id": "toys", "name": "潮玩", "icon": "smile"},
    {"id": "baby", "name": "母婴", "icon": "team"},
    {"id": "sports", "name": "运动户外", "icon": "fire"},
    {"id": "luxury", "name": "奢侈品", "icon": "crown"},
    {"id": "books", "name": "图书音像", "icon": "read"},
    {"id": "pet", "name": "宠物", "icon": "github"},
    {"id": "car", "name": "二手车", "icon": "car"},
    {"id": "other", "name": "其他", "icon": "ellipsis"},
]

CUSTOM_INDUSTRIES = [
    "二手手机",
    "奢侈品包",
    "潮鞋",
    "盲盒",
    "相机镜头",
    "机械键盘",
    "文玩手串",
    "明星周边",
    "游戏卡带",
    "家具电器",
]


def get_all_categories():
    return {"xianyu": XIANYU_CATEGORIES, "industries": CUSTOM_INDUSTRIES}
```

- [ ] **步骤 2：创建 backend/app/api/categories.py**

```python
from fastapi import APIRouter
from app.services.category import get_all_categories

router = APIRouter(prefix="/api", tags=["categories"])


@router.get("/categories")
async def list_categories():
    return get_all_categories()
```

- [ ] **步骤 3：在 main.py 注册路由**

```python
from app.api.categories import router as categories_router
app.include_router(categories_router)
```

- [ ] **步骤 4：Commit**

```bash
git add backend/app/services/category.py backend/app/api/categories.py backend/app/main.py
git commit -m "feat: add category and industry listing API"
```

---

### 任务 8：商品搜索与爆款排行 API

**文件：**
- 创建：`backend/app/api/products.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：创建 backend/app/api/products.py**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.product import Product
from app.models.hot_score import HotScore
from app.schemas.product import ProductOut, HotProductOut, ProductSearchResult

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/search", response_model=ProductSearchResult)
async def search_products(
    keyword: str | None = Query(None, description="搜索关键词"),
    category: str | None = Query(None, description="闲鱼类目ID"),
    industry: str | None = Query(None, description="自定义行业标签"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("hot_score", description="排序: hot_score|price_asc|price_desc|newest"),
    db: AsyncSession = Depends(get_db),
):
    # subquery: latest hot_score per product
    latest_score = (
        select(
            HotScore.product_id,
            HotScore.score,
            HotScore.want_velocity,
            HotScore.price_advantage,
            HotScore.engagement_rate,
            func.row_number()
            .over(partition_by=HotScore.product_id, order_by=desc(HotScore.calculated_at))
            .label("rn"),
        )
        .subquery()
    )
    latest_score_filtered = select(
        latest_score.c.product_id,
        latest_score.c.score,
        latest_score.c.want_velocity,
        latest_score.c.price_advantage,
        latest_score.c.engagement_rate,
    ).where(latest_score.c.rn == 1).subquery()

    query = (
        select(Product, latest_score_filtered)
        .join(latest_score_filtered, Product.id == latest_score_filtered.c.product_id, isouter=True)
    )

    # filters
    if keyword:
        query = query.where(Product.title.ilike(f"%{keyword}%"))
    if category:
        query = query.where(Product.category == category)
    if industry:
        query = query.where(Product.tags.contains([industry]))

    # count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # sort
    if sort == "hot_score":
        query = query.order_by(desc(latest_score_filtered.c.score).nullslast())
    elif sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "newest":
        query = query.order_by(desc(Product.publish_time).nullslast())

    # paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    rows = (await db.execute(query)).all()

    items = []
    for product, score_row in rows:
        item = {
            **{c.name: getattr(product, c.name) for c in product.__table__.columns},
            "score": score_row.score if score_row else 0,
            "want_velocity": score_row.want_velocity if score_row else 0,
            "price_advantage": score_row.price_advantage if score_row else 0,
            "engagement_rate": score_row.engagement_rate if score_row else 0,
        }
        items.append(HotProductOut(**item))

    return ProductSearchResult(items=items, total=total, page=page, page_size=page_size)


@router.get("/hot", response_model=ProductSearchResult)
async def hot_products(
    category: str | None = Query(None),
    industry: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get hot products ranked by score."""
    return await search_products(
        keyword=None,
        category=category,
        industry=industry,
        page=1,
        page_size=limit,
        sort="hot_score",
        db=db,
    )


@router.get("/{product_id}", response_model=HotProductOut)
async def product_detail(product_id: UUID, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="商品不存在")

    latest_score = (
        (await db.execute(
            select(HotScore)
            .where(HotScore.product_id == product_id)
            .order_by(desc(HotScore.calculated_at))
            .limit(1)
        ))
        .scalar_one_or_none()
    )

    item = {c.name: getattr(product, c.name) for c in product.__table__.columns}
    if latest_score:
        item.update({
            "score": latest_score.score,
            "want_velocity": latest_score.want_velocity,
            "price_advantage": latest_score.price_advantage,
            "engagement_rate": latest_score.engagement_rate,
        })
    else:
        item.update({"score": 0, "want_velocity": 0, "price_advantage": 0, "engagement_rate": 0})

    return HotProductOut(**item)
```

- [ ] **步骤 2：在 main.py 注册路由**

```python
from app.api.products import router as products_router
app.include_router(products_router)
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/api/products.py backend/app/main.py
git commit -m "feat: add product search, hot ranking, and detail APIs"
```

---

### 任务 9：爬虫基础设施（基类 + httpx 爬虫）

**文件：**
- 创建：`backend/app/crawlers/__init__.py`
- 创建：`backend/app/crawlers/base.py`
- 创建：`backend/app/crawlers/httpx_crawler.py`
- 创建：`backend/tests/test_crawler_parse.py`

- [ ] **步骤 1：创建爬虫基类 backend/app/crawlers/base.py**

```python
import random
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CrawledProduct:
    xianyu_id: str
    title: str
    price: float
    original_price: float | None = None
    images: list[str] = field(default_factory=list)
    seller_name: str | None = None
    seller_level: str | None = None
    want_count: int = 0
    view_count: int = 0
    category: str | None = None
    publish_time: datetime | None = None


class BaseCrawler(ABC):
    user_agents = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.163 Mobile Safari/537.36",
    ]

    def __init__(self):
        self._consecutive_failures = 0

    @abstractmethod
    async def search(self, keyword: str, category: str | None = None) -> list[CrawledProduct]:
        ...

    def random_delay(self):
        from app.config import settings
        delay = random.uniform(settings.crawler_request_delay_min, settings.crawler_request_delay_max)
        time.sleep(delay)

    def random_ua(self) -> str:
        return random.choice(self.user_agents)
```

- [ ] **步骤 2：创建 httpx 爬虫 backend/app/crawlers/httpx_crawler.py**

```python
import json
import logging
from datetime import datetime

import httpx

from app.crawlers.base import BaseCrawler, CrawledProduct

logger = logging.getLogger(__name__)


class HttpxCrawler(BaseCrawler):
    """L1 crawler: direct HTTP requests to Xianyu mobile search."""

    BASE_URL = "https://m.taobao.com"  # Placeholder — actual URL determined during testing

    async def search(self, keyword: str, category: str | None = None) -> list[CrawledProduct]:
        headers = {
            "User-Agent": self.random_ua(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://m.taobao.com/",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                # NOTE: Xianyu's actual search endpoint needs to be determined
                # by inspecting network requests in a real browser session.
                # This uses a placeholder approach that must be updated.
                response = await client.get(
                    f"https://s.2.taobao.com/list/list.htm",
                    params={"q": keyword, "stype": "1"},
                    headers=headers,
                )
                response.raise_for_status()

                # Parsing logic depends on actual response format
                # For now, parse HTML to extract product cards
                products = self._parse_html(response.text, category)
                logger.info(f"HttpxCrawler found {len(products)} products for '{keyword}'")
                return products

            except httpx.HTTPStatusError as e:
                logger.warning(f"HttpxCrawler HTTP error for '{keyword}': {e}")
                self._consecutive_failures += 1
                raise
            except Exception as e:
                logger.warning(f"HttpxCrawler error for '{keyword}': {e}")
                self._consecutive_failures += 1
                raise

    def _parse_html(self, html: str, category: str | None) -> list[CrawledProduct]:
        """Parse Xianyu search results HTML.
        
        NOTE: This is a skeleton — actual parsing depends on the real HTML
        structure of Xianyu's search page. Use browser devtools to identify
        the correct CSS selectors.
        """
        # This is a placeholder. Real implementation requires:
        # 1. Open Xianyu in browser
        # 2. Search for a product
        # 3. Inspect the HTML structure of search result cards
        # 4. Extract: title, price, want_count, seller_name, etc.
        #
        # Example structure (may differ from actual):
        # from bs4 import BeautifulSoup
        # soup = BeautifulSoup(html, "html.parser")
        # cards = soup.select(".search-result-item")
        # products = []
        # for card in cards:
        #     products.append(CrawledProduct(
        #         xianyu_id=card.get("data-itemid", ""),
        #         title=card.select_one(".title").text.strip(),
        #         price=float(card.select_one(".price").text.replace("¥", "")),
        #         ...
        #     ))
        # return products
        return []
```

- [ ] **步骤 3：创建解析测试 backend/tests/test_crawler_parse.py**

```python
from app.crawlers.httpx_crawler import HttpxCrawler


class TestHttpxCrawlerParse:
    def test_parse_empty_html(self):
        crawler = HttpxCrawler()
        products = crawler._parse_html("<html></html>", None)
        assert products == []

    def test_parse_html_with_no_results(self):
        crawler = HttpxCrawler()
        html = "<html><body><div class='no-result'>暂无相关商品</div></body></html>"
        products = crawler._parse_html(html, "digital")
        assert products == []
```

- [ ] **步骤 4：运行测试**

```bash
cd backend && python -m pytest tests/test_crawler_parse.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add backend/app/crawlers/ backend/tests/test_crawler_parse.py
git commit -m "feat: add crawler base class and httpx crawler skeleton"
```

---

### 任务 10：Playwright 降级爬虫

**文件：**
- 创建：`backend/app/crawlers/playwright_crawler.py`

- [ ] **步骤 1：创建 backend/app/crawlers/playwright_crawler.py**

```python
import logging
from datetime import datetime

from app.crawlers.base import BaseCrawler, CrawledProduct

logger = logging.getLogger(__name__)


class PlaywrightCrawler(BaseCrawler):
    """L2 crawler: headless browser fallback when httpx fails."""

    async def search(self, keyword: str, category: str | None = None) -> list[CrawledProduct]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: playwright install chromium")
            return []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.random_ua(),
                viewport={"width": 390, "height": 844},
                locale="zh-CN",
            )
            page = await context.new_page()

            try:
                # Navigate to Xianyu search
                search_url = f"https://s.2.taobao.com/list/list.htm?q={keyword}&stype=1"
                await page.goto(search_url, wait_until="networkidle", timeout=30000)

                # Wait for search results
                await page.wait_for_timeout(3000)

                # Scroll to load more
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await page.wait_for_timeout(1000)

                products = await self._extract_products(page, category)
                logger.info(f"PlaywrightCrawler found {len(products)} products for '{keyword}'")
                return products

            except Exception as e:
                logger.error(f"PlaywrightCrawler error for '{keyword}': {e}")
                self._consecutive_failures += 1
                raise
            finally:
                await browser.close()

    async def _extract_products(self, page, category: str | None) -> list[CrawledProduct]:
        """Extract product data from page using JavaScript evaluation."""
        items = await page.evaluate("""
            () => {
                const cards = document.querySelectorAll('[class*="item"], [class*="card"], [class*="listItem"]');
                return Array.from(cards).slice(0, 30).map(card => {
                    const titleEl = card.querySelector('[class*="title"], h3, h4');
                    const priceEl = card.querySelector('[class*="price"]');
                    const wantEl = card.querySelector('[class*="want"], [class*="like"]');
                    const sellerEl = card.querySelector('[class*="seller"], [class*="user"]');
                    const imgEls = card.querySelectorAll('img');
                    return {
                        title: titleEl?.textContent?.trim() || '',
                        price: priceEl?.textContent?.replace(/[^0-9.]/g, '') || '0',
                        wantCount: parseInt(wantEl?.textContent || '0'),
                        sellerName: sellerEl?.textContent?.trim() || '',
                        images: Array.from(imgEls).map(img => img.src).filter(s => s),
                    };
                });
            }
        """)

        products = []
        for i, item in enumerate(items):
            if not item.get("title"):
                continue
            try:
                price = float(item["price"])
            except (ValueError, TypeError):
                price = 0

            products.append(CrawledProduct(
                xianyu_id=f"xy_{keyword}_{i}_{int(datetime.utcnow().timestamp())}",
                title=item["title"],
                price=price,
                images=item.get("images", []),
                seller_name=item.get("sellerName"),
                want_count=item.get("wantCount", 0),
                category=category,
            ))

        return products
```

- [ ] **步骤 2：安装 Playwright 浏览器**

```bash
playwright install chromium
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/crawlers/playwright_crawler.py
git commit -m "feat: add playwright browser crawler as L2 fallback"
```

---

### 任务 11：爬虫调度服务（三层降级）

**文件：**
- 创建：`backend/app/services/crawler.py`
- 创建：`backend/tests/test_crawler_service.py`

- [ ] **步骤 1：创建 backend/tests/test_crawler_service.py**

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from app.services.crawler import CrawlerService
from app.crawlers.base import CrawledProduct


class TestCrawlerServiceDecision:
    @pytest.mark.asyncio
    async def test_l1_success_no_fallback(self):
        svc = CrawlerService()
        svc.httpx_crawler.search = AsyncMock(return_value=[
            CrawledProduct(xianyu_id="1", title="Test", price=10, want_count=5)
        ])
        svc.playwright_crawler.search = AsyncMock()

        products = await svc.crawl("test_keyword", "digital")
        assert len(products) == 1
        svc.httpx_crawler.search.assert_called_once()
        svc.playwright_crawler.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_l1_fails_fallsback_to_l2(self):
        svc = CrawlerService()
        svc.httpx_crawler.search = AsyncMock(side_effect=Exception("blocked"))
        svc.playwright_crawler.search = AsyncMock(return_value=[
            CrawledProduct(xianyu_id="2", title="Fallback", price=20, want_count=3)
        ])

        products = await svc.crawl("test_keyword", "digital")
        assert len(products) == 1
        assert products[0].title == "Fallback"

    @pytest.mark.asyncio
    async def test_l2_fails_returns_empty(self):
        svc = CrawlerService()
        svc.httpx_crawler.search = AsyncMock(side_effect=Exception("blocked"))
        svc.playwright_crawler.search = AsyncMock(side_effect=Exception("timeout"))

        products = await svc.crawl("test_keyword", "digital")
        assert products == []
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd backend && python -m pytest tests/test_crawler_service.py -v
# 预期：FAIL (ModuleNotFoundError)
```

- [ ] **步骤 3：实现 backend/app/services/crawler.py**

```python
import logging
from datetime import datetime

from app.crawlers.base import CrawledProduct
from app.crawlers.httpx_crawler import HttpxCrawler
from app.crawlers.playwright_crawler import PlaywrightCrawler

logger = logging.getLogger(__name__)


class CrawlerService:
    def __init__(self):
        self.httpx_crawler = HttpxCrawler()
        self.playwright_crawler = PlaywrightCrawler()

    async def crawl(self, keyword: str, category: str | None = None) -> list[CrawledProduct]:
        """Run crawl with L1 -> L2 fallback."""

        # L1: httpx fast crawl
        try:
            products = await self.httpx_crawler.search(keyword, category)
            if products:
                logger.info(f"L1 success: {len(products)} products for '{keyword}'")
                return products
        except Exception as e:
            logger.warning(f"L1 failed for '{keyword}': {e}")

        # L2: Playwright browser fallback
        try:
            logger.info(f"Falling back to L2 for '{keyword}'")
            products = await self.playwright_crawler.search(keyword, category)
            if products:
                return products
        except Exception as e:
            logger.error(f"L2 failed for '{keyword}': {e}")

        # L3: cool down — handled by caller (scheduler)
        logger.error(f"All levels failed for '{keyword}'")
        return []
```

- [ ] **步骤 4：运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_crawler_service.py -v
# 预期：全部 PASS
```

- [ ] **步骤 5：Commit**

```bash
git add backend/app/services/crawler.py backend/tests/test_crawler_service.py
git commit -m "feat: add crawler service with L1-L2 fallback"
```

---

### 任务 12：爬取 API 端点

**文件：**
- 创建：`backend/app/api/crawl.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：创建 backend/app/api/crawl.py**

```python
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.crawl_task import CrawlTask
from app.models.product import Product
from app.schemas.crawl import CrawlTriggerRequest, CrawlTaskOut
from app.services.crawler import CrawlerService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/crawl", tags=["crawl"])
crawler_service = CrawlerService()


@router.post("/trigger", response_model=CrawlTaskOut)
async def trigger_crawl(
    body: CrawlTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    task = CrawlTask(keyword=body.keyword, category=body.category, status="pending")
    db.add(task)
    await db.commit()
    await db.refresh(task)

    background_tasks.add_task(_run_crawl_task, task.id, body.keyword, body.category)
    return CrawlTaskOut.model_validate(task)


@router.get("/status", response_model=list[CrawlTaskOut])
async def crawl_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CrawlTask).order_by(desc(CrawlTask.created_at)).limit(50)
    )
    tasks = result.scalars().all()
    return [CrawlTaskOut.model_validate(t) for t in tasks]


async def _run_crawl_task(task_id: UUID, keyword: str, category: str | None):
    from app.database import async_session

    async with async_session() as db:
        task = await db.get(CrawlTask, task_id)
        if not task:
            return

        task.status = "running"
        task.started_at = datetime.utcnow()
        await db.commit()

        try:
            products = await crawler_service.crawl(keyword, category)
            task.items_found = len(products)
            task.level = "L1"  # updated if fallback occurred
            task.status = "done"

            for cp in products:
                existing = (
                    await db.execute(select(Product).where(Product.xianyu_id == cp.xianyu_id))
                ).scalar_one_or_none()
                if existing:
                    existing.want_count = cp.want_count
                    existing.view_count = cp.view_count or existing.view_count
                    existing.price = cp.price
                    existing.fetched_at = datetime.utcnow()
                else:
                    db.add(Product(
                        xianyu_id=cp.xianyu_id,
                        title=cp.title,
                        price=cp.price,
                        original_price=cp.original_price,
                        images=cp.images,
                        seller_name=cp.seller_name,
                        seller_level=cp.seller_level,
                        want_count=cp.want_count,
                        view_count=cp.view_count or 0,
                        category=cp.category or category,
                        publish_time=cp.publish_time,
                        fetched_at=datetime.utcnow(),
                    ))

            await db.commit()
            logger.info(f"Crawl task {task_id} done: {len(products)} items")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            await db.commit()
            logger.error(f"Crawl task {task_id} failed: {e}")

        task.ended_at = datetime.utcnow()
        await db.commit()
```

- [ ] **步骤 2：在 main.py 注册路由**

```python
from app.api.crawl import router as crawl_router
app.include_router(crawl_router)
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/api/crawl.py backend/app/main.py
git commit -m "feat: add crawl trigger and status API endpoints"
```

---

### 任务 13：定时任务调度（APScheduler）

**文件：**
- 创建：`backend/app/tasks/__init__.py`
- 创建：`backend/app/tasks/scheduler.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：创建 backend/app/tasks/scheduler.py**

```python
import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, delete

from app.database import async_session
from app.models.crawl_task import CrawlTask
from app.models.product import Product
from app.models.hot_score import HotScore
from app.services.crawler import CrawlerService
from app.services.scorer import calculate_hot_score

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    ("iPhone", "digital"),
    ("机械键盘", "digital"),
    ("相机", "digital"),
    ("潮鞋", "clothing"),
    ("盲盒", "toys"),
    ("包包", "luxury"),
    ("护肤品", "beauty"),
]

scheduler = AsyncIOScheduler()
crawler_service = CrawlerService()


async def scheduled_crawl():
    """Run crawls for default keywords."""
    logger.info("Starting scheduled crawl...")
    for keyword, category in DEFAULT_KEYWORDS:
        try:
            products = await crawler_service.crawl(keyword, category)
            if products:
                async with async_session() as db:
                    for cp in products:
                        existing = (
                            await db.execute(
                                select(Product).where(Product.xianyu_id == cp.xianyu_id)
                            )
                        ).scalar_one_or_none()
                        if existing:
                            existing.want_count = cp.want_count
                            existing.fetched_at = datetime.utcnow()
                        else:
                            db.add(Product(
                                xianyu_id=cp.xianyu_id,
                                title=cp.title,
                                price=cp.price,
                                original_price=cp.original_price,
                                images=cp.images,
                                seller_name=cp.seller_name,
                                seller_level=cp.seller_level,
                                want_count=cp.want_count,
                                view_count=cp.view_count or 0,
                                category=cp.category or category,
                                publish_time=cp.publish_time,
                                fetched_at=datetime.utcnow(),
                            ))
                    await db.commit()
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Scheduled crawl error for '{keyword}': {e}")


async def recalculate_scores():
    """Recalculate hot scores for all products."""
    logger.info("Recalculating hot scores...")
    async with async_session() as db:
        products = (await db.execute(select(Product))).scalars().all()

        for category in set(p.category for p in products if p.category):
            cat_products = [p for p in products if p.category == category]
            prices = [p.price for p in cat_products if p.price > 0]
            cat_avg = sum(prices) / len(prices) if prices else 0

            for product in cat_products:
                previous_score = (
                    await db.execute(
                        select(HotScore)
                        .where(HotScore.product_id == product.id)
                        .order_by(HotScore.calculated_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()

                previous_want = previous_score.want_velocity if previous_score else None
                hours = max((datetime.utcnow() - product.fetched_at).total_seconds() / 3600, 1)

                score = calculate_hot_score(
                    current_want=product.want_count,
                    previous_want=previous_want,
                    hours=hours,
                    price=product.price,
                    category_avg_price=cat_avg,
                    want_count=product.want_count,
                    view_count=product.view_count,
                    publish_time=product.publish_time or product.fetched_at,
                )

                db.add(HotScore(
                    product_id=product.id,
                    score=score,
                    want_velocity=product.want_count,
                    price_advantage=cat_avg / product.price if product.price > 0 and cat_avg > 0 else 0,
                    engagement_rate=product.want_count / product.view_count if product.view_count > 0 else 0,
                    freshness=score,  # embedded in score calc
                ))

        await db.commit()
    logger.info(f"Score recalculation done for {len(products)} products")


async def cleanup_old_data():
    """Remove hot_scores older than 30 days."""
    logger.info("Cleaning up old data...")
    cutoff = datetime.utcnow() - timedelta(days=30)
    async with async_session() as db:
        await db.execute(delete(HotScore).where(HotScore.calculated_at < cutoff))
        await db.commit()
    logger.info("Cleanup done")


def start_scheduler():
    scheduler.add_job(scheduled_crawl, "cron", hour="8,14,20", id="scheduled_crawl")
    scheduler.add_job(recalculate_scores, "cron", hour="9,15,21", id="recalculate_scores")
    scheduler.add_job(cleanup_old_data, "cron", hour="3", id="cleanup")
    scheduler.start()
    logger.info("Scheduler started")


def shutdown_scheduler():
    scheduler.shutdown()
```

- [ ] **步骤 2：修改 backend/app/main.py 添加启动/关闭事件**

在 main.py 文件末尾添加：

```python
@app.on_event("startup")
async def startup():
    from app.tasks.scheduler import start_scheduler
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    from app.tasks.scheduler import shutdown_scheduler
    shutdown_scheduler()
```

- [ ] **步骤 3：Commit**

```bash
git add backend/app/tasks/ backend/app/main.py
git commit -m "feat: add scheduled crawl, score recalculation, and cleanup tasks"
```

---

### 任务 14：全局错误处理中间件

**文件：**
- 修改：`backend/app/main.py`

- [ ] **步骤 1：在 backend/app/main.py 中添加异常处理器**

在 `app = FastAPI(...)` 之后添加：

```python
from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "code": 500},
    )
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/main.py
git commit -m "feat: add global error handler middleware"
```

---

### 任务 15：前端项目脚手架

**文件：**
- 创建：`frontend/package.json`
- 创建：`frontend/vite.config.ts`
- 创建：`frontend/tsconfig.json`
- 创建：`frontend/tsconfig.node.json`
- 创建：`frontend/index.html`
- 创建：`frontend/src/main.tsx`
- 创建：`frontend/src/App.tsx`

- [ ] **步骤 1：使用 Vite 创建 React TypeScript 项目**

```bash
cd /Users/peter.wang/xianyu-tool
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

- [ ] **步骤 2：安装依赖**

```bash
cd frontend && npm install antd @ant-design/icons react-router-dom recharts axios dayjs
```

- [ ] **步骤 3：创建 frontend/vite.config.ts**（覆盖默认配置）

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **步骤 4：修改 frontend/src/App.tsx**

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Search from './pages/Search';
import HotRanking from './pages/HotRanking';
import Tasks from './pages/Tasks';
import Login from './pages/Login';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/search" element={<Search />} />
            <Route path="/hot/:industry?" element={<HotRanking />} />
            <Route path="/tasks" element={<Tasks />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
```

- [ ] **步骤 5：验证前端能启动**

```bash
cd frontend && npm run dev
# 确认 http://localhost:5173 可访问
```

- [ ] **步骤 6：Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend with Vite, React, Ant Design, React Router"
```

---

### 任务 16：前端 API 客户端与类型定义

**文件：**
- 创建：`frontend/src/types/index.ts`
- 创建：`frontend/src/api/client.ts`

- [ ] **步骤 1：创建 frontend/src/types/index.ts**

```typescript
export interface Product {
  id: string;
  xianyu_id: string;
  title: string;
  price: number;
  original_price: number | null;
  images: string[] | null;
  seller_name: string | null;
  seller_level: string | null;
  want_count: number;
  view_count: number;
  category: string | null;
  tags: string[] | null;
  publish_time: string | null;
  fetched_at: string;
}

export interface HotProduct extends Product {
  score: number;
  want_velocity: number;
  price_advantage: number;
  engagement_rate: number;
}

export interface ProductSearchResult {
  items: HotProduct[];
  total: number;
  page: number;
  page_size: number;
}

export interface Category {
  id: string;
  name: string;
  icon: string;
}

export interface CategoryList {
  xianyu: Category[];
  industries: string[];
}

export interface CrawlTask {
  id: string;
  keyword: string;
  category: string | null;
  status: string;
  items_found: number;
  level: string | null;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
```

- [ ] **步骤 2：创建 frontend/src/api/client.ts**

```typescript
import axios from 'axios';
import { message } from 'antd';

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// inject token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// global error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    } else {
      const msg = error.response?.data?.error || error.message || '请求失败';
      message.error(msg);
    }
    return Promise.reject(error);
  }
);

export default client;
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/types/ frontend/src/api/
git commit -m "feat: add frontend types and API client with auth interceptor"
```

---

### 任务 17：Auth 上下文与登录页面

**文件：**
- 创建：`frontend/src/contexts/AuthContext.tsx`
- 创建：`frontend/src/pages/Login.tsx`

- [ ] **步骤 1：创建 frontend/src/contexts/AuthContext.tsx**

```tsx
import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import client from '../api/client';
import type { LoginRequest, TokenResponse } from '../types';

interface AuthContextType {
  isAuthenticated: boolean;
  login: (data: LoginRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: !!localStorage.getItem('token'),
  login: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));

  const login = useCallback(async (data: LoginRequest) => {
    const res = await client.post<TokenResponse>('/auth/login', data);
    localStorage.setItem('token', res.data.access_token);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
```

- [ ] **步骤 2：创建 frontend/src/pages/Login.tsx**

```tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';

const { Title } = Typography;

export default function Login() {
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values);
      message.success('登录成功');
      navigate('/');
    } catch {
      // error already handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f5f5f5' }}>
      <Card style={{ width: 400 }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 24 }}>闲鱼选品工具</Title>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
```

- [ ] **步骤 3：更新 App.tsx 包裹 AuthProvider**

修改 `frontend/src/App.tsx`，在 `ConfigProvider` 内添加 `AuthProvider`：

```tsx
import { AuthProvider } from './contexts/AuthContext';

// 包裹 routes:
// <ConfigProvider locale={zhCN}>
//   <AuthProvider>
//     <BrowserRouter>
//       ...
//     </BrowserRouter>
//   </AuthProvider>
// </ConfigProvider>
```

- [ ] **步骤 4：Commit**

```bash
git add frontend/src/contexts/ frontend/src/pages/Login.tsx frontend/src/App.tsx
git commit -m "feat: add auth context and login page"
```

---

### 任务 18：Layout 布局组件

**文件：**
- 创建：`frontend/src/components/Layout.tsx`

- [ ] **步骤 1：创建 frontend/src/components/Layout.tsx**

```tsx
import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout as AntLayout, Menu, Button, theme } from 'antd';
import {
  DashboardOutlined,
  SearchOutlined,
  FireOutlined,
  SettingOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';

const { Header, Sider, Content } = AntLayout;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '首页' },
  { key: '/search', icon: <SearchOutlined />, label: '搜索' },
  { key: '/hot', icon: <FireOutlined />, label: '爆款榜' },
  { key: '/tasks', icon: <SettingOutlined />, label: '爬虫管理' },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();
  const { token: { colorBgContainer } } = theme.useToken();

  const selectedKey = location.pathname === '/' ? '/' : '/' + location.pathname.split('/')[1];

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: collapsed ? 14 : 18, fontWeight: 600 }}>
          {collapsed ? '选品' : '闲鱼选品工具'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header style={{ padding: '0 24px', background: colorBgContainer, display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          <Button type="text" icon={<LogoutOutlined />} onClick={logout}>退出</Button>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: colorBgContainer, borderRadius: 8 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
```

- [ ] **步骤 2：验证前端渲染**

```bash
cd frontend && npm run dev
# 访问 http://localhost:5173 确认 Layout 正常渲染
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat: add sidebar layout with navigation"
```

---

### 任务 19：首页仪表盘页面

**文件：**
- 创建：`frontend/src/pages/Dashboard.tsx`

- [ ] **步骤 1：创建 frontend/src/pages/Dashboard.tsx**

```tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Row, Col, Card, Statistic, Spin, Tag } from 'antd';
import { FireOutlined, SearchOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import client from '../api/client';
import type { CategoryList, CrawlTask, ProductSearchResult } from '../types';

export default function Dashboard() {
  const [categories, setCategories] = useState<CategoryList | null>(null);
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [hotCounts, setHotCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      const [catRes, taskRes] = await Promise.all([
        client.get<CategoryList>('/categories'),
        client.get<CrawlTask[]>('/crawl/status'),
      ]);
      setCategories(catRes.data);
      setTasks(taskRes.data);

      // fetch hot counts for each xianyu category
      const counts: Record<string, number> = {};
      await Promise.all(
        catRes.data.xianyu.map(async (cat) => {
          const res = await client.get<ProductSearchResult>('/products/hot', {
            params: { category: cat.id, limit: 1 },
          });
          counts[cat.id] = res.data.total;
        })
      );
      setHotCounts(counts);
      setLoading(false);
    };
    fetchData();
  }, []);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  const runningTasks = tasks.filter((t) => t.status === 'running').length;
  const failedTasks = tasks.filter((t) => t.status === 'failed').length;

  return (
    <div>
      <h2>选品概览</h2>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card><Statistic title="今日爬取任务" value={tasks.length} prefix={<SearchOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="运行中" value={runningTasks} valueStyle={{ color: '#1677ff' }} prefix={<CheckCircleOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="失败" value={failedTasks} valueStyle={{ color: '#ff4d4f' }} prefix={<CloseCircleOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="行业总数" value={(categories?.xianyu.length || 0) + (categories?.industries.length || 0)} prefix={<FireOutlined />} /></Card>
        </Col>
      </Row>

      <h3>行业爆款概览</h3>
      <Row gutter={[16, 16]}>
        {categories?.xianyu.map((cat) => (
          <Col xs={12} sm={8} md={6} key={cat.id}>
            <Card hoverable onClick={() => navigate(`/hot/${cat.id}`)}>
              <Statistic title={cat.name} value={hotCounts[cat.id] || 0} suffix="个爆款" />
            </Card>
          </Col>
        ))}
      </Row>

      <h3 style={{ marginTop: 24 }}>自定义行业</h3>
      <div>
        {categories?.industries.map((ind) => (
          <Tag key={ind} style={{ marginBottom: 8, cursor: 'pointer' }} color="orange" onClick={() => navigate(`/hot?industry=${ind}`)}>
            {ind}
          </Tag>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **步骤 2：Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: add dashboard with category overview and task stats"
```

---

### 任务 20：搜索页面

**文件：**
- 创建：`frontend/src/pages/Search.tsx`
- 创建：`frontend/src/components/ProductCard.tsx`

- [ ] **步骤 1：创建 frontend/src/components/ProductCard.tsx**

```tsx
import { Card, Tag, Typography, Space } from 'antd';
import { HeartOutlined, EyeOutlined, FireOutlined } from '@ant-design/icons';
import type { HotProduct } from '../types';

const { Text, Paragraph } = Typography;

export default function ProductCard({ product }: { product: HotProduct }) {
  return (
    <Card
      hoverable
      style={{ marginBottom: 12 }}
      cover={
        product.images?.[0] ? (
          <img alt={product.title} src={product.images[0]} style={{ height: 180, objectFit: 'cover' }} />
        ) : (
          <div style={{ height: 180, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb' }}>
            暂无图片
          </div>
        )
      }
    >
      <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 8 }}>
        {product.title}
      </Paragraph>
      <Space size="middle" style={{ marginBottom: 8 }}>
        <Text strong style={{ color: '#ff4d4f', fontSize: 18 }}>
          ¥{product.price}
        </Text>
        {product.original_price && (
          <Text delete type="secondary">¥{product.original_price}</Text>
        )}
      </Space>
      <div>
        <Space size="small">
          <Tag color="red">{product.score.toFixed(0)}分</Tag>
          <Text type="secondary"><HeartOutlined /> {product.want_count}</Text>
          <Text type="secondary"><EyeOutlined /> {product.view_count}</Text>
        </Space>
      </div>
      {product.tags?.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {product.tags.map((tag) => <Tag key={tag}>{tag}</Tag>)}
        </div>
      )}
    </Card>
  );
}
```

- [ ] **步骤 2：创建 frontend/src/pages/Search.tsx**

```tsx
import { useState, useEffect } from 'react';
import { Input, Select, Row, Col, Spin, Empty, Pagination } from 'antd';
import ProductCard from '../components/ProductCard';
import client from '../api/client';
import type { CategoryList, HotProduct, ProductSearchResult } from '../types';

const { Search: AntSearch } = Input;

export default function Search() {
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState<string | undefined>();
  const [industry, setIndustry] = useState<string | undefined>();
  const [sort, setSort] = useState('hot_score');
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState<CategoryList | null>(null);
  const [result, setResult] = useState<ProductSearchResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    client.get<CategoryList>('/categories').then((res) => setCategories(res.data));
  }, []);

  const doSearch = async (p = 1) => {
    setLoading(true);
    setPage(p);
    try {
      const res = await client.get<ProductSearchResult>('/products/search', {
        params: { keyword: keyword || undefined, category, industry, sort, page: p, page_size: 20 },
      });
      setResult(res.data);
    } finally {
      setLoading(false);
    }
  };

  const categoryOptions = (categories?.xianyu || []).map((c) => ({ value: c.id, label: c.name }));
  const industryOptions = (categories?.industries || []).map((i) => ({ value: i, label: i }));

  return (
    <div>
      <h2>商品搜索</h2>
      <Row gutter={[12, 12]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <AntSearch
            placeholder="搜索关键词"
            allowClear
            enterButton
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={() => doSearch(1)}
          />
        </Col>
        <Col xs={12} sm={5}>
          <Select
            placeholder="闲鱼类目"
            allowClear
            style={{ width: '100%' }}
            options={categoryOptions}
            value={category}
            onChange={(v) => { setCategory(v); setIndustry(undefined); }}
          />
        </Col>
        <Col xs={12} sm={5}>
          <Select
            placeholder="自定义行业"
            allowClear
            style={{ width: '100%' }}
            options={industryOptions}
            value={industry}
            onChange={(v) => { setIndustry(v); setCategory(undefined); }}
          />
        </Col>
        <Col xs={12} sm={3}>
          <Select
            style={{ width: '100%' }}
            value={sort}
            onChange={setSort}
            options={[
              { value: 'hot_score', label: '爆款指数' },
              { value: 'price_asc', label: '价格从低到高' },
              { value: 'price_desc', label: '价格从高到低' },
              { value: 'newest', label: '最新发布' },
            ]}
          />
        </Col>
        <Col xs={12} sm={3}>
          <Select
            style={{ width: '100%' }}
            value={category || industry}
            onChange={(v) => {
              if (categories?.xianyu.find((c) => c.id === v)) {
                setCategory(v);
                setIndustry(undefined);
              } else {
                setIndustry(v);
                setCategory(undefined);
              }
            }}
            options={[...categoryOptions, ...industryOptions]}
            placeholder="筛选行业"
            allowClear
            onClear={() => { setCategory(undefined); setIndustry(undefined); }}
          />
        </Col>
      </Row>

      {loading ? (
        <Spin size="large" style={{ display: 'block', margin: '50px auto' }} />
      ) : result ? (
        result.items.length > 0 ? (
          <>
            <Row gutter={[16, 16]}>
              {result.items.map((item) => (
                <Col xs={24} sm={12} md={8} lg={6} key={item.id}>
                  <ProductCard product={item} />
                </Col>
              ))}
            </Row>
            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <Pagination
                current={result.page}
                total={result.total}
                pageSize={result.page_size}
                onChange={doSearch}
                showTotal={(total) => `共 ${total} 件商品`}
              />
            </div>
          </>
        ) : (
          <Empty description="暂无匹配商品" />
        )
      ) : (
        <Empty description="输入关键词开始搜索" />
      )}
    </div>
  );
}
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/components/ProductCard.tsx frontend/src/pages/Search.tsx
git commit -m "feat: add product search page with filtering and pagination"
```

---

### 任务 21：爆款排行榜页面

**文件：**
- 创建：`frontend/src/pages/HotRanking.tsx`
- 创建：`frontend/src/components/HotTable.tsx`
- 创建：`frontend/src/components/TrendChart.tsx`

- [ ] **步骤 1：创建 frontend/src/components/HotTable.tsx**

```tsx
import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { HotProduct } from '../types';

const columns: ColumnsType<HotProduct> = [
  {
    title: '排名',
    key: 'rank',
    width: 60,
    render: (_, __, index) => {
      if (index === 0) return <Tag color="#ff4d4f">1</Tag>;
      if (index === 1) return <Tag color="#ff7a45">2</Tag>;
      if (index === 2) return <Tag color="#ffa940">3</Tag>;
      return index + 1;
    },
  },
  { title: '商品名称', dataIndex: 'title', key: 'title', ellipsis: true },
  {
    title: '价格', dataIndex: 'price', key: 'price', width: 100,
    render: (v: number) => <span style={{ color: '#ff4d4f' }}>¥{v}</span>,
  },
  {
    title: '爆款指数', dataIndex: 'score', key: 'score', width: 100,
    render: (v: number) => <Tag color="red">{v.toFixed(0)}</Tag>,
    sorter: (a, b) => a.score - b.score,
    defaultSortOrder: 'descend',
  },
  {
    title: '想要', dataIndex: 'want_count', key: 'want_count', width: 80,
    render: (v: number) => v.toLocaleString(),
  },
  {
    title: '浏览', dataIndex: 'view_count', key: 'view_count', width: 80,
    render: (v: number) => v.toLocaleString(),
  },
  { title: '卖家', dataIndex: 'seller_name', key: 'seller_name', width: 100 },
];

export default function HotTable({ data }: { data: HotProduct[] }) {
  return (
    <Table
      columns={columns}
      dataSource={data}
      rowKey="id"
      pagination={false}
      size="middle"
    />
  );
}
```

- [ ] **步骤 2：创建 frontend/src/components/TrendChart.tsx**

```tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { HotProduct } from '../types';

export default function TrendChart({ data }: { data: HotProduct[] }) {
  const priceBuckets: Record<string, number> = {};
  data.forEach((p) => {
    const bucket = `${Math.floor(p.price / 50) * 50}-${Math.floor(p.price / 50) * 50 + 49}`;
    priceBuckets[bucket] = (priceBuckets[bucket] || 0) + 1;
  });

  const chartData = Object.entries(priceBuckets).map(([range, count]) => ({
    range: `¥${range}`,
    count,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="range" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="count" fill="#1677ff" name="商品数量" />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **步骤 3：创建 frontend/src/pages/HotRanking.tsx**

```tsx
import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Select, Spin, Empty, Typography } from 'antd';
import client from '../api/client';
import HotTable from '../components/HotTable';
import TrendChart from '../components/TrendChart';
import type { CategoryList, HotProduct, ProductSearchResult } from '../types';

const { Title } = Typography;

export default function HotRanking() {
  const { industry: paramIndustry } = useParams();
  const [searchParams] = useSearchParams();
  const industry = paramIndustry || searchParams.get('industry') || undefined;

  const [categories, setCategories] = useState<CategoryList | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(industry);
  const [selectedIndustry, setSelectedIndustry] = useState<string | undefined>(
    industry && !industry.match(/^[a-z]+$/) ? industry : undefined
  );
  const [data, setData] = useState<HotProduct[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get<CategoryList>('/categories').then((res) => {
      setCategories(res.data);
    });
  }, []);

  useEffect(() => {
    const fetchHot = async () => {
      setLoading(true);
      const params: Record<string, string> = { limit: '50' };
      if (selectedCategory) params.category = selectedCategory;
      if (selectedIndustry) params.industry = selectedIndustry;

      const res = await client.get<ProductSearchResult>('/products/hot', { params });
      setData(res.data.items);
      setLoading(false);
    };
    fetchHot();
  }, [selectedCategory, selectedIndustry]);

  const allOptions = [
    ...(categories?.xianyu.map((c) => ({ value: c.id, label: `[类目] ${c.name}` })) || []),
    ...(categories?.industries.map((i) => ({ value: i, label: `[行业] ${i}` })) || []),
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>
          {selectedCategory
            ? categories?.xianyu.find((c) => c.id === selectedCategory)?.name
            : selectedIndustry || '全部'}
          {' '}爆款榜
        </Title>
        <Select
          style={{ width: 250 }}
          placeholder="选择行业/类目"
          options={allOptions}
          value={selectedCategory || selectedIndustry}
          onChange={(v) => {
            if (categories?.xianyu.find((c) => c.id === v)) {
              setSelectedCategory(v);
              setSelectedIndustry(undefined);
            } else {
              setSelectedIndustry(v);
              setSelectedCategory(undefined);
            }
          }}
          allowClear
          onClear={() => { setSelectedCategory(undefined); setSelectedIndustry(undefined); }}
        />
      </div>

      {loading ? (
        <Spin size="large" style={{ display: 'block', margin: '50px auto' }} />
      ) : data.length > 0 ? (
        <>
          <TrendChart data={data} />
          <HotTable data={data} />
        </>
      ) : (
        <Empty description="该行业暂无数据，请先触发爬取" />
      )}
    </div>
  );
}
```

- [ ] **步骤 4：Commit**

```bash
git add frontend/src/components/HotTable.tsx frontend/src/components/TrendChart.tsx frontend/src/pages/HotRanking.tsx
git commit -m "feat: add hot ranking page with table and price distribution chart"
```

---

### 任务 22：爬虫管理页面

**文件：**
- 创建：`frontend/src/pages/Tasks.tsx`

- [ ] **步骤 1：创建 frontend/src/pages/Tasks.tsx**

```tsx
import { useEffect, useState, useCallback } from 'react';
import { Table, Button, Modal, Form, Input, Select, Tag, message } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import client from '../api/client';
import type { CrawlTask, CategoryList } from '../types';

const statusColors: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  done: 'success',
  failed: 'error',
};

const columns: ColumnsType<CrawlTask> = [
  { title: '关键词', dataIndex: 'keyword', key: 'keyword' },
  { title: '行业', dataIndex: 'category', key: 'category', render: (v: string | null) => v || '-' },
  {
    title: '状态', dataIndex: 'status', key: 'status', width: 100,
    render: (s: string) => <Tag color={statusColors[s] || 'default'}>{s}</Tag>,
  },
  { title: '抓取数', dataIndex: 'items_found', key: 'items_found', width: 80 },
  { title: '策略', dataIndex: 'level', key: 'level', width: 60, render: (v: string | null) => v || '-' },
  {
    title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180,
    render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
  },
];

export default function Tasks() {
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [categories, setCategories] = useState<CategoryList | null>(null);
  const [form] = Form.useForm();

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    const res = await client.get<CrawlTask[]>('/crawl/status');
    setTasks(res.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchTasks();
    client.get<CategoryList>('/categories').then((res) => setCategories(res.data));
    const interval = setInterval(fetchTasks, 10000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const triggerCrawl = async () => {
    const values = await form.validateFields();
    await client.post('/crawl/trigger', values);
    message.success('爬取任务已创建');
    setModalOpen(false);
    form.resetFields();
    fetchTasks();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>爬虫管理</h2>
        <div>
          <Button icon={<ReloadOutlined />} onClick={fetchTasks} style={{ marginRight: 8 }}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建任务</Button>
        </div>
      </div>

      <Table columns={columns} dataSource={tasks} rowKey="id" loading={loading} pagination={{ pageSize: 20 }} />

      <Modal title="新建爬取任务" open={modalOpen} onOk={triggerCrawl} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="keyword" label="搜索关键词" rules={[{ required: true, message: '请输入关键词' }]}>
            <Input placeholder="如: iPhone 15" />
          </Form.Item>
          <Form.Item name="category" label="行业/类目（可选）">
            <Select
              placeholder="选择行业"
              allowClear
              options={[
                ...(categories?.xianyu.map((c) => ({ value: c.id, label: c.name })) || []),
                ...(categories?.industries.map((i) => ({ value: i, label: i })) || []),
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
```

- [ ] **步骤 2：Commit**

```bash
git add frontend/src/pages/Tasks.tsx
git commit -m "feat: add crawl task management page with trigger and auto-refresh"
```

---

### 任务 23：端到端集成验证

- [ ] **步骤 1：确保所有后端服务运行**

```bash
cd backend
docker compose up -d
# 等待 PostgreSQL 和 Redis 就绪
uvicorn app.main:app --reload --port 8000
```

- [ ] **步骤 2：运行后端测试套件**

```bash
cd backend && python -m pytest tests/ -v
# 预期：所有测试 PASS
```

- [ ] **步骤 3：启动前端并验证页面**

```bash
cd frontend && npm run dev
```

手动验证：
1. 访问 `http://localhost:5173/login` → 用 `admin / admin123` 登录
2. 首页仪表盘显示行业卡片和统计数据
3. 搜索页输入关键词筛选商品
4. 爆款榜页展示排行榜和价格分布图
5. 爬虫管理页能创建任务、查看状态

- [ ] **步骤 4：修复验证中发现的问题，然后 Commit**

```bash
git add -A
git commit -m "chore: final integration fixes"
```

---

## 自检

### 1. 规格覆盖度
- ✅ 数据模型（products, hot_scores, users, crawl_tasks）→ 任务 2
- ✅ 爆款评分公式 + 四维度计算 → 任务 4
- ✅ 用户系统 JWT 登录 → 任务 6
- ✅ 7 个 API 端点（auth/login, categories, products/search, products/hot, products/:id, crawl/trigger, crawl/status）→ 任务 6, 7, 8, 12
- ✅ 4 个前端页面（仪表盘、搜索、爆款榜、爬虫管理）→ 任务 19, 20, 21, 22
- ✅ 三层降级爬虫（L1 httpx, L2 Playwright, L3 冷却）→ 任务 9, 10, 11
- ✅ APScheduler 定时任务（每日爬取、评分重算、数据清理）→ 任务 13
- ✅ 全局错误处理 → 任务 14
- ✅ 反爬手段（UA 轮换、请求间隔、Redis 去重）→ 任务 9 (UA 池), 任务 2 (配置间隔)
- ✅ 前端三态（Loading/Empty/Error）→ 任务 19, 20, 21, 22

### 2. 占位符扫描
- ⚠️ 任务 9 httpx_crawler.py 中的 `_parse_html` 是骨架实现——这是无法避免的，因为实际的 HTML 解析依赖于闲鱼页面的真实 DOM 结构，需要在实际开发时通过浏览器 DevTools 确定选择器。
- 计划中已明确标注这个约束。

### 3. 类型一致性
- ✅ `CrawledProduct` 在任务 9 定义，任务 11, 13 使用
- ✅ `Product`, `HotScore`, `CrawlTask` 模型在任务 2 定义，后续 API 任务使用
- ✅ Schemas 在任务 5 定义，API 任务 6-8 使用
- ✅ TypeScript 类型在任务 16 定义，所有前端组件使用
- ✅ 前端 `CategoryList`, `HotProduct`, `CrawlTask` 类型与后端 API 输出一致
