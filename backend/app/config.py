from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./xianyu.db"
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
