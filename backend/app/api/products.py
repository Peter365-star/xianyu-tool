from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.models.hot_score import HotScore
from app.schemas.product import HotProductOut, ProductSearchResult

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/search", response_model=ProductSearchResult)
def search_products(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="闲鱼类目ID"),
    industry: Optional[str] = Query(None, description="自定义行业标签"),
    source: Optional[str] = Query(None, description="数据来源: one_click|manual"),
    time_filter: Optional[str] = Query(None, description="时间筛选: 7d|15d|30d"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("hotness", description="排序: hotness|hot_score|price_asc|price_desc|newest"),
    db: Session = Depends(get_db),
):
    from app.services.scorer import calc_hotness, calc_days_ago

    query = select(Product)

    if keyword:
        query = query.where(Product.title.ilike(f"%{keyword}%"))
    if category:
        query = query.where(Product.category == category)
    if industry:
        query = query.where(Product.tags.contains([industry]))
    if source:
        query = query.where(Product.source == source)

    # Time filter
    if time_filter:
        days = int(time_filter.replace("d", ""))
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.where(Product.publish_time >= cutoff)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Fetch all matching products (for hotness sorting, we need to sort in Python)
    all_rows = db.execute(query).scalars().all()

    # Compute hotness and days_ago for each product
    scored = []
    for product in all_rows:
        days_ago = calc_days_ago(product.publish_time)
        hotness = calc_hotness(product.want_count, product.publish_time)
        scored.append((product, hotness, days_ago))

    # Sort
    if sort == "hotness":
        scored.sort(key=lambda x: x[1], reverse=True)
    elif sort == "hot_score":
        scored.sort(key=lambda x: x[1], reverse=True)  # same as hotness for now
    elif sort == "price_asc":
        scored.sort(key=lambda x: x[0].price)
    elif sort == "price_desc":
        scored.sort(key=lambda x: x[0].price, reverse=True)
    elif sort == "newest":
        scored.sort(key=lambda x: x[0].publish_time or datetime.min, reverse=True)

    # Paginate
    offset = (page - 1) * page_size
    page_items = scored[offset:offset + page_size]

    items = []
    for product, hotness, days_ago in page_items:
        item = {
            **{c.name: getattr(product, c.name) for c in product.__table__.columns},
            "score": round(hotness, 2),
            "want_velocity": 0,
            "price_advantage": 0,
            "engagement_rate": 0,
            "days_ago": days_ago,
            "hotness": round(hotness, 2),
        }
        items.append(HotProductOut(**item))

    return ProductSearchResult(items=items, total=total, page=page, page_size=page_size)


@router.get("/hot", response_model=ProductSearchResult)
def hot_products(
    category: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    source: Optional[str] = Query(None, description="数据来源: one_click|manual"),
    time_filter: Optional[str] = Query(None, description="时间筛选: 7d|15d|30d"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return search_products(
        keyword=None,
        category=category,
        industry=industry,
        source=source,
        time_filter=time_filter,
        page=1,
        page_size=limit,
        sort="hotness",
        db=db,
    )


@router.get("/{product_id}", response_model=HotProductOut)
def product_detail(product_id: UUID, db: Session = Depends(get_db)):
    from app.services.scorer import calc_hotness, calc_days_ago

    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    item = {c.name: getattr(product, c.name) for c in product.__table__.columns}
    days_ago = calc_days_ago(product.publish_time)
    hotness = calc_hotness(product.want_count, product.publish_time)

    item.update({
        "score": round(hotness, 2),
        "want_velocity": 0,
        "price_advantage": 0,
        "engagement_rate": 0,
        "days_ago": days_ago,
        "hotness": round(hotness, 2),
    })

    return HotProductOut(**item)
