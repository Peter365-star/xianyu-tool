from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional


def calc_want_velocity(current_want: int, previous_want: Optional[int], hours: float) -> float:
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
    previous_want: Optional[int],
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


def calc_hotness(want_count: int, publish_time: Optional[datetime] = None) -> float:
    """Simple hotness: want_count divided by days since publish.
    Newer items with more wants score higher.
    Returns a float where higher = hotter.
    """
    if publish_time is None:
        return float(want_count)
    days = max((datetime.utcnow() - publish_time).total_seconds() / 86400, 0.5)
    return want_count / days


def calc_days_ago(publish_time: Optional[datetime]) -> Optional[int]:
    """Return days since publish, or None."""
    if publish_time is None:
        return None
    return int((datetime.utcnow() - publish_time).total_seconds() / 86400)
