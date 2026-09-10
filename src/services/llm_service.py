"""
Penta Document Intelligence — LLM Orkestrasyonu Modülü

Azure OpenAI (GPT-4o/GPT-4o-mini) ile zero-shot fatura/irsaliye
veri ayıklama işlemini yönetir. Deterministik system prompt ile
hallucination önlenir.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from openai import AzureOpenAI

from src.config import Settings
from src.schemas.extraction import FaturaVerisi

logger = logging.getLogger(__name__)

# ─── System Prompt ────────────────────────────────────────────
# Katı kurallarla hallucination önlemi ve deterministik çıktı
SYSTEM_PROMPT = """Sen Türk fatura, irsaliye ve mali dokümanlardan veri ayıklayan deterministik bir veri çıkarma motorusun.

## KESİN KURALLAR:
1. ASLA varsayımda bulunma. Dokümanda olmayan bilgiyi UYDURMA.
2. Bir alanı bulamıyorsan değerini null olarak döndür.
3. Sayısal değerleri (fiyat, tutar, adet) her zaman sayı olarak döndür, string olarak DEĞİL.
4. Tarihleri YYYY-MM-DD formatında döndür (ör: 2024-01-15).
5. KDV oranını yüzde olarak döndür (ör: 20, %20 değil).
6. Para birimi belirtilmemişse TRY varsay.
7. VKN/TCKN'yi string olarak döndür (başındaki sıfırlar korunmalı).

## ÇIKTI FORMATI:
Yanıtını SADECE aşağıdaki JSON şemasına uygun olarak döndür. Açıklama, yorum veya ek metin EKLEME.

{
  "dokuman_tipi": "string veya null (e-Fatura, İrsaliye, Makbuz, vb.)",
  "fatura_no": "string veya null",
  "tarih": "YYYY-MM-DD veya null",
  "vade_tarihi": "YYYY-MM-DD veya null",
  "tedarikci_unvan": "string veya null",
  "tedarikci_vkn": "string veya null",
  "tedarikci_adres": "string veya null",
  "alici_unvan": "string veya null",
  "alici_vkn": "string veya null",
  "alici_adres": "string veya null",
  "kalemler": [
    {
      "urun_adi": "string",
      "adet": number,
      "birim": "string veya null (Adet, Kg, Lt, m² vb.)",
      "birim_fiyat": number,
      "kdv_orani": number,
      "toplam_tutar": number
    }
  ],
  "ara_toplam": number veya null,
  "kdv_toplam": number veya null,
  "genel_toplam": number veya null,
  "para_birimi": "TRY/USD/EUR vb.",
  "notlar": "string veya null"
}"""

USER_PROMPT_TEMPLATE = """Aşağıdaki dokümanın içeriğini analiz et ve tüm fatura/irsaliye verilerini ayıkla.

## DOKÜMAN İÇERİĞİ:
{document_content}

## TALİMAT:
Yukarıdaki dokümandan tüm verileri ayıklayıp JSON formatında döndür. Bulamadığın alanları null bırak."""


@dataclass
class LLMResult:
    """LLM çıktı sonucu."""

    extracted_data: FaturaVerisi
    """Doğrulanmış fatura verisi."""

    raw_response: str
    """LLM'den dönen ham JSON string."""

    model: str
    """Kullanılan model adı."""

    token_usage: dict[str, int]
    """Token kullanım bilgileri."""


class LLMService:
    """
    Azure OpenAI orkestrasyonu.

    Zero-shot extraction: Önceden eğitim gerektirmeden,
    system prompt ile fatura verilerini ayıklar.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self._deployment = settings.azure_openai_deployment_name
        logger.info(
            "LLM Service başlatıldı — Model: %s, Endpoint: %s",
            self._deployment,
            settings.azure_openai_endpoint,
        )

    async def extract_invoice_data(
        self,
        document_content: str,
    ) -> LLMResult:
        """
        Doküman metninden fatura/irsaliye verilerini ayıklar.

        İşlem adımları:
        1. User prompt'a doküman içeriğini yerleştirir
        2. Azure OpenAI'ye JSON mode ile istek atar
        3. Dönen JSON'ı Pydantic modeliyle doğrular

        Args:
            document_content: OCR'dan gelen Markdown metin

        Returns:
            LLMResult: Doğrulanmış veri, ham yanıt ve token kullanımı

        Raises:
            LLMExtractionError: LLM çağrısı veya doğrulama başarısız olursa
        """
        user_prompt = USER_PROMPT_TEMPLATE.format(
            document_content=document_content
        )

        logger.info(
            "LLM extraction başlatılıyor — Doküman: %d karakter",
            len(document_content),
        )

        try:
            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,  # Deterministic çıktı
                max_tokens=4096,
                top_p=1.0,
            )
        except Exception as e:
            logger.error("LLM API çağrısı başarısız: %s", str(e))
            raise LLMExtractionError(
                code="LLM_API_ERROR",
                message=f"Azure OpenAI API çağrısı başarısız oldu: {str(e)}",
            ) from e

        # Token kullanımı
        token_usage: dict[str, int] = {}
        if response.usage:
            token_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        raw_content = response.choices[0].message.content or "{}"

        logger.info(
            "LLM yanıtı alındı — Tokens: %s",
            token_usage,
        )

        # JSON parse ve Pydantic doğrulama
        extracted_data = self._parse_and_validate(raw_content)

        return LLMResult(
            extracted_data=extracted_data,
            raw_response=raw_content,
            model=self._deployment,
            token_usage=token_usage,
        )

    def _parse_and_validate(self, raw_json: str) -> FaturaVerisi:
        """
        LLM JSON çıktısını parse eder ve Pydantic ile doğrular.

        JSON parse hatası veya doğrulama hatası durumunda
        detaylı hata bilgisi ile exception fırlatır.
        """
        # ── JSON Parse ────────────────────────────────────────
        try:
            data: dict[str, Any] = json.loads(raw_json)
        except json.JSONDecodeError as e:
            logger.error("LLM çıktısı geçerli JSON değil: %s", str(e))
            raise LLMExtractionError(
                code="INVALID_LLM_JSON",
                message="LLM yanıtı geçerli JSON formatında değil.",
                detail=f"JSON parse hatası: {str(e)}",
            ) from e

        # ── Pydantic Doğrulama ────────────────────────────────
        try:
            validated = FaturaVerisi.model_validate(data)
        except Exception as e:
            logger.error("Pydantic doğrulama hatası: %s", str(e))
            raise LLMExtractionError(
                code="VALIDATION_ERROR",
                message="LLM çıktısı veri şemasına uymuyor.",
                detail=f"Doğrulama hatası: {str(e)}",
            ) from e

        logger.info(
            "Veri doğrulandı — Fatura No: %s, %d kalem",
            validated.fatura_no,
            len(validated.kalemler),
        )

        return validated

    def close(self) -> None:
        """İstemci bağlantısını kapatır."""
        self._client.close()
        logger.info("LLM Service kapatıldı.")


class LLMExtractionError(Exception):
    """LLM veri ayıklama hatası."""

    def __init__(
        self,
        code: str,
        message: str,
        detail: str | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)
