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
