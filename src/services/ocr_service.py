"""
Penta Document Intelligence — OCR Servis Modülü

Azure Document Intelligence Layout ve Read API çağrılarını yönetir.
Dokümanları Markdown formatında metin çıktısına çevirir.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeResult,
    DocumentContentFormat,
)
from azure.core.credentials import AzureKeyCredential

from src.config import Settings

logger = logging.getLogger(__name__)

# Desteklenen OCR modelleri
OCRModel = Literal["prebuilt-layout", "prebuilt-read"]


@dataclass
class OCRResult:
    """OCR analiz sonucu."""

    content: str
    """Markdown veya düz metin olarak doküman içeriği."""

    page_count: int
    """Doküman sayfa sayısı."""

    model_id: str
    """Kullanılan OCR model kimliği."""

    tables_detected: int = 0
    """Tespit edilen tablo sayısı."""

    raw_result: AnalyzeResult | None = field(default=None, repr=False)
    """Ham Azure API sonucu (debug/advanced kullanım için)."""


class OCRService:
    """
    Azure Document Intelligence istemci wrapper'ı.

    Layout ve Read modellerini destekler; Markdown çıktı formatı ile
    LLM'e beslenmeye hazır metin üretir.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = DocumentIntelligenceClient(
            endpoint=settings.azure_document_intelligence_endpoint,
            credential=AzureKeyCredential(settings.azure_document_intelligence_key),
        )
        logger.info(
            "OCR Service başlatıldı — Endpoint: %s",
            settings.azure_document_intelligence_endpoint,
        )

    async def analyze(
        self,
        file_content: bytes,
        model_id: OCRModel = "prebuilt-layout",
    ) -> OCRResult:
        """
        Dokümanı Azure Document Intelligence ile analiz eder.

        Args:
            file_content: Dosya binary içeriği
            model_id: Kullanılacak model ('prebuilt-layout' veya 'prebuilt-read')

        Returns:
            OCRResult: Analiz sonucu (Markdown metin, sayfa sayısı, tablo bilgisi)
        """
        logger.info("OCR analizi başlatılıyor — Model: %s", model_id)

        if model_id == "prebuilt-layout":
            return await self._analyze_layout(file_content)
        else:
            return await self._analyze_read(file_content)

    async def _analyze_layout(self, file_content: bytes) -> OCRResult:
        """
        Layout modeli ile detaylı analiz.

        Tablo, başlık, paragraf hiyerarşisini koruyarak
        Markdown formatında çıktı üretir.
        """
        poller = self._client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=file_content,
            content_type="application/octet-stream",
            output_content_format=DocumentContentFormat.MARKDOWN,
        )
        result: AnalyzeResult = poller.result()

        # Sayfa ve tablo sayısını çıkar
        page_count = len(result.pages) if result.pages else 0
        tables_detected = len(result.tables) if result.tables else 0

        content = result.content or ""

        logger.info(
            "Layout analizi tamamlandı — %d sayfa, %d tablo, %d karakter",
            page_count,
            tables_detected,
            len(content),
        )

        return OCRResult(
            content=content,
            page_count=page_count,
            model_id="prebuilt-layout",
            tables_detected=tables_detected,
            raw_result=result,
        )

    async def _analyze_read(self, file_content: bytes) -> OCRResult:
        """
        Read modeli ile basit metin çıkarma.

        Tablo yapısını korumaz; düz metin olarak çıktı üretir.
        Maliyet avantajı: Layout'un 1/10'u.
        """
        poller = self._client.begin_analyze_document(
            model_id="prebuilt-read",
            body=file_content,
            content_type="application/octet-stream",
        )
        result: AnalyzeResult = poller.result()

        page_count = len(result.pages) if result.pages else 0
        content = result.content or ""

        logger.info(
            "Read analizi tamamlandı — %d sayfa, %d karakter",
            page_count,
            len(content),
        )

        return OCRResult(
            content=content,
            page_count=page_count,
            model_id="prebuilt-read",
            tables_detected=0,
            raw_result=result,
        )

    def close(self) -> None:
        """İstemci bağlantısını kapatır."""
        self._client.close()
        logger.info("OCR Service kapatıldı.")
