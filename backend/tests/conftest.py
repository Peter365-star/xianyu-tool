import pytest
from app.config import settings


@pytest.fixture(autouse=True)
def reset_scorer_weights():
    """Ensure scorer weights are at defaults for each test."""
    settings.weight_want_velocity = 0.4
    settings.weight_price_advantage = 0.25
    settings.weight_engagement_rate = 0.2
    settings.weight_freshness = 0.15
