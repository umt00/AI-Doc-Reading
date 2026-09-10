"""
Penta Document Intelligence — Akıllı Yönlendirici Modülü

Heuristic analiz ile dokümanı uygun OCR modeline sevk eder.
Basit dokümanlar → Read API ($1/1K), tablolu dokümanlar → Layout API ($10/1K).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

# Karar tipi
ModelDecision = Literal["prebuilt-layout", "prebuilt-read"]

# ─── Tablo / Fatura Göstergeleri ──────────────────────────────

# Türkçe ve İngilizce fatura/irsaliye anahtar kelimeleri
TABLE_INDICATOR_KEYWORDS: list[str] = [
    # Türkçe fatura alanları
    "fatura no",
    "fatura numarası",
    "irsaliye no",
    "irsaliye numarası",
    "birim fiyat",
    "birim fiyatı",
    "kdv",
    "kdv oranı",
    "kdv tutarı",
    "toplam tutar",
    "genel toplam",
    "ara toplam",
    "mal hizmet",
    "miktar",
    "adet",
    "vergi dairesi",
    "vkn",
    "tckn",
    "vergi kimlik",
    # İngilizce karşılıklar
    "invoice no",
    "invoice number",
    "unit price",
    "total amount",
    "subtotal",
    "grand total",
    "quantity",
    "tax rate",
    "vat",
    "line item",
]

# Tablo yapısı göstergeleri (satır/sütun düzeni)
TABLE_STRUCTURE_PATTERNS: list[str] = [
    r"\|.*\|.*\|",       # Markdown tablo satırı (| col1 | col2 |)
    r"\d+[.,]\d{2}\s",   # Ondalık sayılar (fiyat formatı: 1.234,56)
    r"\%\s*\d+",         # Yüzde gösterimi
    r"\d+\s*x\s*\d+",   # Çarpım ifadesi (adet x fiyat)
]

# Minimum eşik değerleri
MIN_KEYWORD_HITS = 3       # Bu kadar anahtar kelime bulunursa Layout kullan
MIN_PATTERN_HITS = 2       # Bu kadar yapısal desen bulunursa Layout kullan


@dataclass
class RoutingDecision:
    """Yönlendirme kararı ve gerekçesi."""

    model: ModelDecision
    """Seçilen OCR modeli."""

    confidence: float
    """Karar güvenirlik skoru (0.0 - 1.0)."""

    reason: str
    """Kararın gerekçesi."""

    keyword_hits: list[str]
    """Tespit edilen anahtar kelimeler."""

    pattern_hits: int
    """Tespit edilen yapısal desen sayısı."""


class RouterService:
    """
    Maliyet-bilinçli akıllı yönlendirici.

    İlk geçiş olarak Read API ile düşük maliyetli metin çıkarır,
    ardından heuristic analiz ile Layout gerekli mi belirler.
    """

    def analyze_content_for_routing(self, text: str) -> RoutingDecision:
        """
        Metin içeriğini analiz ederek uygun OCR modelini belirler.

        Heuristic kurallar:
        1. Fatura/irsaliye anahtar kelimeleri taranır
        2. Tablo yapısı desenleri kontrol edilir
        3. Eşik değerlerine göre karar verilir

        Args:
            text: OCR veya raw metin içeriği

        Returns:
            RoutingDecision: Model seçimi, güvenirlik ve gerekçe
        """
        text_lower = text.lower()

        # ── Anahtar kelime taraması ───────────────────────────
        keyword_hits: list[str] = []
        for keyword in TABLE_INDICATOR_KEYWORDS:
            if keyword in text_lower:
                keyword_hits.append(keyword)

        # ── Yapısal desen taraması ────────────────────────────
        pattern_hits = 0
        for pattern in TABLE_STRUCTURE_PATTERNS:
            matches = re.findall(pattern, text, re.MULTILINE)
            pattern_hits += len(matches)

        # ── Karar mantığı ────────────────────────────────────
        keyword_score = len(keyword_hits) / MIN_KEYWORD_HITS
        pattern_score = pattern_hits / max(MIN_PATTERN_HITS, 1)

        # Birleşik skor: anahtar kelime ağırlığı %60, desen ağırlığı %40
        combined_score = (keyword_score * 0.6) + (pattern_score * 0.4)
        confidence = min(combined_score, 1.0)

        if len(keyword_hits) >= MIN_KEYWORD_HITS or pattern_hits >= MIN_PATTERN_HITS:
            model: ModelDecision = "prebuilt-layout"
            reason = (
                f"Tablolu doküman tespit edildi — "
                f"{len(keyword_hits)} anahtar kelime ({', '.join(keyword_hits[:5])}), "
                f"{pattern_hits} yapısal desen bulundu."
            )
        else:
            model = "prebuilt-read"
            confidence = max(1.0 - confidence, 0.3)
            reason = (
                f"Basit metin dokümanı — "
                f"Yalnızca {len(keyword_hits)} anahtar kelime, "
                f"{pattern_hits} yapısal desen bulundu. "
                f"Read API maliyet avantajı ile yeterli."
            )

        decision = RoutingDecision(
            model=model,
            confidence=confidence,
            reason=reason,
            keyword_hits=keyword_hits,
            pattern_hits=pattern_hits,
        )

        logger.info(
            "Yönlendirme kararı: %s (güvenirlik: %.2f) — %s",
            model,
            confidence,
            reason,
        )

        return decision

    def decide_from_mime_and_size(
        self,
        mime_type: str,
        file_size_bytes: int,
    ) -> RoutingDecision:
        """
        Dosya türü ve boyutuna göre ön yönlendirme.

        Görsel dosyalar her zaman Layout'a gider (tablo yapısı korunmalı).
        Küçük PDF'ler (<100KB) Read ile başlar.

        Args:
            mime_type: Dosya MIME türü
            file_size_bytes: Dosya boyutu (byte)

        Returns:
            RoutingDecision: Ön yönlendirme kararı
        """
        # Görsel dosyalar → her zaman Layout
        if mime_type.startswith("image/"):
            return RoutingDecision(
                model="prebuilt-layout",
                confidence=0.8,
                reason="Görsel dosya — Layout modeli ile tablo yapısı korunur.",
                keyword_hits=[],
                pattern_hits=0,
            )

        # Büyük PDF'ler → direkt Layout (muhtemelen tablolu)
        if file_size_bytes > 5 * 1024 * 1024:  # > 5MB
            return RoutingDecision(
                model="prebuilt-layout",
                confidence=0.7,
                reason="Büyük dosya (>5MB) — muhtemelen tablolu, Layout tercih edildi.",
                keyword_hits=[],
                pattern_hits=0,
            )

        # Diğerleri → iki aşamalı analiz gerekli
        return RoutingDecision(
            model="prebuilt-layout",
            confidence=0.5,
            reason="Varsayılan Layout — fatura/irsaliye dokümanları için önerilen model.",
            keyword_hits=[],
            pattern_hits=0,
        )
