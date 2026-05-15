import logging
import time
from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.crawl_task import CrawlTask
from app.models.product import Product
from app.schemas.crawl import CrawlTriggerRequest, CrawlTaskOut
from app.services.crawler import CrawlerService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/crawl", tags=["crawl"])
crawler_service = CrawlerService()


@router.post("/trigger", response_model=CrawlTaskOut)
def trigger_crawl(
    body: CrawlTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = CrawlTask(
        keyword=body.keyword,
        category=body.category,
        duration_minutes=body.duration_minutes,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(
        _run_crawl_task,
        task.id, body.keyword, body.category,
        body.duration_minutes, body.source,
    )
    return CrawlTaskOut.model_validate(task)


@router.get("/status", response_model=List[CrawlTaskOut])
def crawl_status(db: Session = Depends(get_db)):
    result = db.execute(
        select(CrawlTask).order_by(desc(CrawlTask.created_at)).limit(50)
    )
    tasks = result.scalars().all()
    return [CrawlTaskOut.model_validate(t) for t in tasks]


def _run_crawl_task(
    task_id: UUID,
    keyword: str,
    category: Optional[str],
    duration_minutes: Optional[int],
    source: str,
):
    db = SessionLocal()
    all_crawled: list[dict] = []
    try:
        task = db.get(CrawlTask, task_id)
        if not task:
            return

        task.status = "running"
        task.started_at = datetime.utcnow()
        db.commit()

        end_time = datetime.utcnow() + timedelta(minutes=duration_minutes) if duration_minutes else None
        round_num = 0

        try:
            import asyncio

            while True:
                round_num += 1
                products = asyncio.run(crawler_service.crawl(keyword, category))

                if products:
                    seen_ids = set()
                    for cp in products:
                        if cp.xianyu_id in seen_ids:
                            continue
                        seen_ids.add(cp.xianyu_id)

                        existing = (
                            db.execute(select(Product).where(Product.xianyu_id == cp.xianyu_id))
                        ).scalar_one_or_none()
                        if existing:
                            existing.want_count = max(existing.want_count or 0, cp.want_count or 0)
                            existing.view_count = max(existing.view_count or 0, cp.view_count or 0)
                            existing.price = cp.price if cp.price > 0 else existing.price
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
                                want_count=cp.want_count or 0,
                                view_count=cp.view_count or 0,
                                category=cp.category or category,
                                source=source,
                                link=cp.link or f"https://www.goofish.com/item?id={cp.xianyu_id}",
                                publish_time=cp.publish_time or datetime.utcnow(),
                                fetched_at=datetime.utcnow(),
                            ))

                    db.commit()
                    logger.info(f"Round {round_num}: {len(products)} products for '{keyword}'")

                    for cp in products:
                        link = cp.link
                        if not link and cp.xianyu_id.startswith("xy_"):
                            # Real item from search: use the numeric ID
                            real_id = cp.xianyu_id.replace("xy_", "")
                            if real_id.isdigit():
                                link = f"https://www.goofish.com/item?id={real_id}"
                        all_crawled.append({
                            "title": cp.title,
                            "price": cp.price,
                            "seller_name": cp.seller_name or "",
                            "link": link or "",
                        })

                # Check if we should continue
                if not end_time or datetime.utcnow() >= end_time:
                    break
                time.sleep(30)

            task.items_found = len(all_crawled)
            task.level = "L2"
            task.status = "done"
            # Store deduplicated snapshot
            seen_titles = set()
            unique_snapshot = []
            for item in all_crawled:
                if item["title"] not in seen_titles:
                    seen_titles.add(item["title"])
                    unique_snapshot.append(item)
            task.products_data = unique_snapshot[:200]

        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            task.status = "failed"
            task.error = str(e)[:500]
            logger.error(f"Crawl task {task_id} failed: {e}")

        task.ended_at = datetime.utcnow()
        db.commit()
        logger.info(f"Crawl task {task_id} done: {len(all_crawled)} items in {round_num} rounds")
    finally:
        db.close()
