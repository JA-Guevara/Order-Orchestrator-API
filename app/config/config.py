"""Configuración central de la API.

REGLA DEL PROYECTO: toda variable es OBLIGATORIA y vive en el .env.
No hay defaults en código. El .env es el inventario único y completo
de la configuración activa. Si falta una variable, la API no arranca
y Pydantic indica exactamente cuál.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== App =====
    app_name: str
    app_env: Literal["development", "staging", "production"]
    debug: bool
    api_prefix: str

    # ===== Database =====
    database_url: str
    db_echo: bool
    db_pool_size: int = Field(ge=1, le=50)
    db_max_overflow: int = Field(ge=0, le=100)

    # ===== Redis =====
    redis_url: str

    # ===== Reservas =====
    reserva_lease_seconds: int = Field(ge=60, le=7200)
    reserva_key_prefix: str
    reserva_max_candidatos: int = Field(ge=1, le=500)

    # ===== JWT =====
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256"]
    jwt_expire_minutes: int = Field(ge=5, le=1440)
    jwt_issuer: str

    # ===== API Clients =====
    api_clients_file: str

    # ===== CORS =====
    cors_origins: str
    
    # ===== Rate Limiting =====
    rate_limit_enabled: bool
    rate_limit_auth: str
    rate_limit_reservar: str
    rate_limit_resultado: str


    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()