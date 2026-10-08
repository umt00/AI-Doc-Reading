"""
Penta Document Intelligence — Konfigürasyon Modülü

pydantic-settings ile ortam değişkenlerini tip-güvenli yükler.
.env dosyasından otomatik okuma yapar.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Uygulama konfigürasyonu — .env dosyasından otomatik yüklenir."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Azure Document Intelligence ──────────────────────────
    azure_document_intelligence_endpoint: str = Field(
        default="",
        description="Azure Document Intelligence servis endpoint URL'i",
    )
    azure_document_intelligence_key: str = Field(
        default="",
        description="Azure Document Intelligence API anahtarı",
    )

    # ─── Azure OpenAI ─────────────────────────────────────────
    azure_openai_endpoint: str = Field(
        default="",
        description="Azure OpenAI servis endpoint URL'i",
    )
    azure_openai_api_key: str = Field(
        default="",
        description="Azure OpenAI API anahtarı",
    )
    azure_openai_deployment_name: str = Field(
        default="gpt-4o",
        description="Azure OpenAI deployment adı (model)",
    )
    azure_openai_api_version: str = Field(
        default="2024-08-01-preview",
        description="Azure OpenAI API versiyonu",
    )

    # ─── Uygulama Ayarları ────────────────────────────────────
    max_file_size_mb: int = Field(
        default=50,
        description="Maksimum dosya boyutu (MB)",
    )
    log_level: str = Field(
        default="INFO",
        description="Loglama seviyesi",
    )
    allowed_origins: str = Field(
        default="*",
        description="CORS izinli origin'ler (virgülle ayrılmış)",
    )
    uvicorn_host: str = Field(
        default="0.0.0.0",
        description="Uvicorn bind adresi",
    )
    uvicorn_port: int = Field(
        default=8000,
        description="Uvicorn port numarası",
    )

    @property
    def max_file_size_bytes(self) -> int:
        """Maksimum dosya boyutunu byte cinsinden döndürür."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        """CORS origin listesini döndürür."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Singleton Settings örneğini döndürür (uygulama genelinde tek instance)."""
    return Settings()
