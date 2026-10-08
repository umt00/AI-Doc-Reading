"""
Penta Document Intelligence — API Yanıt Şemaları

Tüm endpoint'ler için standart yanıt formatları.
Generic APIResponse ile tip güvenli wrapper sağlar.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ExtractionMetadata(BaseModel):
    """Doküman işleme sürecine ait metadata."""

    dosya_adi: str = Field(
        ...,
        description="Yüklenen dosyanın adı",
    )
    dosya_boyutu_kb: float = Field(
        ...,
        description="Dosya boyutu (KB)",
    )
    sayfa_sayisi: int | None = Field(
        default=None,
        description="Doküman sayfa sayısı",
    )
    kullanilan_model: str = Field(
        ...,
        description="Kullanılan OCR modeli (prebuilt-layout veya prebuilt-read)",
    )
    llm_model: str = Field(
        ...,
        description="Kullanılan LLM modeli (ör: gpt-4o)",
    )
    islem_suresi_sn: float = Field(
        ...,
        description="Toplam işlem süresi (saniye)",
    )
    llm_token_kullanimi: dict[str, int] | None = Field(
        default=None,
        description="LLM token kullanım detayları (prompt, completion, total)",
    )
    islem_zamani: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="İşlem zaman damgası (UTC)",
    )


class APIResponse(BaseModel, Generic[T]):
    """Başarılı API yanıtı için generic wrapper."""

    success: bool = Field(
        default=True,
        description="İşlem başarı durumu",
    )
    data: T = Field(
        ...,
        description="Ayıklanan veri",
    )
    metadata: ExtractionMetadata = Field(
        ...,
        description="İşlem metadata bilgileri",
    )


class ErrorDetail(BaseModel):
    """Hata detay bilgisi."""

    code: str = Field(
        ...,
        description="Hata kodu",
        examples=["INVALID_FILE_FORMAT"],
    )
    message: str = Field(
        ...,
        description="Kullanıcıya yönelik hata mesajı",
    )
    detail: str | None = Field(
        default=None,
        description="Teknik hata detayı (debug için)",
    )


class ErrorResponse(BaseModel):
    """Hata yanıt modeli."""

    success: bool = Field(
        default=False,
        description="İşlem başarı durumu (her zaman false)",
    )
    error: ErrorDetail = Field(
        ...,
        description="Hata detayları",
    )


class HealthResponse(BaseModel):
    """Health check endpoint yanıtı."""

    status: str = Field(
        default="healthy",
        description="Servis durumu",
    )
    version: str = Field(
        default="0.1.0",
        description="API versiyonu",
    )
    services: dict[str, Any] = Field(
        default_factory=dict,
        description="Bağlı servislerin durumu",
    )
