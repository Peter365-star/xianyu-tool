import logging
from datetime import datetime, timedelta
from typing import List, Tuple

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select, delete

from app.database import SessionLocal
from app.models.product import Product
from app.models.hot_score import HotScore
from app.services.crawler import CrawlerService
from app.services.scorer import calculate_hot_score

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS: List[Tuple[str, str]] = [
    ("iPhone", "digital"),
    ("机械键盘", "digital"),
    ("相机", "digital"),
    ("潮鞋", "clothing"),
    ("盲盒", "toys"),
    ("包包", "luxury"),
    ("护肤品", "beauty"),
]

scheduler = BackgroundScheduler()
crawler_service = CrawlerService()


def scheduled_crawl():
    import asyncio
    logger.info("Starting scheduled crawl...")
    for keyword, category in DEFAULT_KEYWORDS:
        try:
            products = asyncio.run(crawler_service.crawl(keyword, category))
            if products:
                db = SessionLocal()
                try:
                    for cp in products:
                        existing = (
                            db.execute(
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
                    db.commit()
                finally:
                    db.close()
        except Exception as e:
            logger.error(f"Scheduled crawl error for '{keyword}': {e}")


def recalculate_scores():
    logger.info("Recalculating hot scores...")
    db = SessionLocal()
    try:
        products = db.execute(select(Product)).scalars().all()

        for cat in set(p.category for p in products if p.category):
            cat_products = [p for p in products if p.category == cat]
            prices = [p.price for p in cat_products if p.price > 0]
            cat_avg = sum(prices) / len(prices) if prices else 0

            for product in cat_products:
                previous_score = (
                    db.execute(
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
                    want_velocity=float(product.want_count),
                    price_advantage=cat_avg / product.price if product.price > 0 and cat_avg > 0 else 0,
                    engagement_rate=product.want_count / product.view_count if product.view_count > 0 else 0,
                    freshness=float(score),
                ))

        db.commit()
    finally:
        db.close()
    logger.info(f"Score recalculation done")


def cleanup_old_data():
    logger.info("Cleaning up old data...")
    cutoff = datetime.utcnow() - timedelta(days=30)
    db = SessionLocal()
    try:
        db.execute(delete(HotScore).where(HotScore.calculated_at < cutoff))
        db.commit()
    finally:
        db.close()
    logger.info("Cleanup done")


def start_scheduler():
    scheduler.add_job(scheduled_crawl, "cron", hour="8,14,20", id="scheduled_crawl")
    scheduler.add_job(recalculate_scores, "cron", hour="9,15,21", id="recalculate_scores")
    scheduler.add_job(cleanup_old_data, "cron", hour="3", id="cleanup")
    scheduler.start()
    logger.info("Scheduler started")


def shutdown_scheduler():
    scheduler.shutdown()
