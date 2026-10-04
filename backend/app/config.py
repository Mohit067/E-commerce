from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Nova Commerce API"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "dev-secret-change-in-production-please-override"
    refresh_secret_key: str = "dev-refresh-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    database_url: str = "sqlite:///./ecommerce.db"
    cors_origins: str = "http://localhost:3000"
    google_api_key: str = ""
    google_genai_model: str = "gemini-2.0-flash"
    seed_count_products: int = 1200
    demo_customer_email: str = "customer@example.com"
    demo_admin_email: str = "admin@example.com"
    demo_password: str = "password123"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
