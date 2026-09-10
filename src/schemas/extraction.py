"""
Penta Document Intelligence — Fatura & İrsaliye Veri Şemaları

LLM'den dönen JSON verisini doğrulayan Pydantic v2 modelleri.
Sayısal alanlar Decimal, tarihler YYYY-MM-DD formatında zorunludur.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class FaturaKalemi(BaseModel):
    """Fatura/irsaliye satır kalemi."""

    urun_adi: str = Field(
        ...,
        description="Ürün veya hizmet adı",
        examples=["A4 Kağıt 500'lü Paket"],
    )
    adet: Decimal = Field(
        ...,
        description="Ürün adedi / miktarı",
        examples=[10],
    )
    birim: Optional[str] = Field(
        default=None,
        description="Ölçü birimi (adet, kg, lt, m² vb.)",
        examples=["Adet", "Kg"],
    )
    birim_fiyat: Decimal = Field(
        ...,
        description="Birim fiyat (KDV hariç)",
        examples=[45.50],
    )
    kdv_orani: Decimal = Field(
        ...,
        description="KDV oranı (yüzde olarak, ör: 20 = %20)",
        examples=[20],
    )
    toplam_tutar: Decimal = Field(
        ...,
        description="Satır toplam tutarı (KDV dahil)",
        examples=[546.00],
    )

    @field_validator("adet", "birim_fiyat", "kdv_orani", "toplam_tutar", mode="before")
    @classmethod
    def coerce_to_decimal(cls, v: object) -> Decimal:
        """Gelen değeri Decimal'e çevirir; string, int ve float kabul eder."""
        if v is None:
            return Decimal("0")
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except Exception:
            return Decimal("0")


class FaturaVerisi(BaseModel):
    """Fatura / irsaliye dokümanından ayıklanan tüm veriler."""

    # ─── Doküman Tipi ─────────────────────────────────────────
    dokuman_tipi: Optional[str] = Field(
        default=None,
        description="Doküman türü (fatura, irsaliye, makbuz vb.)",
        examples=["e-Fatura", "İrsaliye"],
    )

    # ─── Temel Bilgiler ───────────────────────────────────────
    fatura_no: Optional[str] = Field(
        default=None,
        description="Fatura veya irsaliye numarası",
        examples=["FT2024000123"],
    )
    tarih: Optional[date] = Field(
        default=None,
        description="Düzenleme tarihi (YYYY-MM-DD)",
        examples=["2024-01-15"],
    )
    vade_tarihi: Optional[date] = Field(
        default=None,
        description="Vade tarihi (YYYY-MM-DD)",
        examples=["2024-02-15"],
    )

    # ─── Taraf Bilgileri ──────────────────────────────────────
    tedarikci_unvan: Optional[str] = Field(
        default=None,
        description="Tedarikçi / satıcı firma ünvanı",
    )
    tedarikci_vkn: Optional[str] = Field(
        default=None,
        description="Tedarikçi vergi kimlik numarası (VKN/TCKN)",
        examples=["1234567890"],
    )
    tedarikci_adres: Optional[str] = Field(
        default=None,
        description="Tedarikçi adresi",
    )

    alici_unvan: Optional[str] = Field(
        default=None,
        description="Alıcı firma ünvanı",
    )
    alici_vkn: Optional[str] = Field(
        default=None,
        description="Alıcı vergi kimlik numarası (VKN/TCKN)",
        examples=["0987654321"],
    )
    alici_adres: Optional[str] = Field(
        default=None,
        description="Alıcı adresi",
    )

    # ─── Kalemler ─────────────────────────────────────────────
    kalemler: list[FaturaKalemi] = Field(
        default_factory=list,
        description="Fatura satır kalemleri listesi",
    )

    # ─── Toplamlar ────────────────────────────────────────────
    ara_toplam: Optional[Decimal] = Field(
        default=None,
        description="KDV hariç ara toplam",
    )
    kdv_toplam: Optional[Decimal] = Field(
        default=None,
        description="Toplam KDV tutarı",
    )
    genel_toplam: Optional[Decimal] = Field(
        default=None,
        description="Genel toplam (KDV dahil)",
    )

    # ─── Ek Bilgiler ─────────────────────────────────────────
    para_birimi: Optional[str] = Field(
        default="TRY",
        description="Para birimi (ISO 4217)",
        examples=["TRY", "USD", "EUR"],
    )
    notlar: Optional[str] = Field(
        default=None,
        description="Fatura üzerindeki ek notlar veya açıklamalar",
    )

    @field_validator("tarih", "vade_tarihi", mode="before")
    @classmethod
    def parse_date_string(cls, v: object) -> date | None:
        """String formatındaki tarihleri date nesnesine çevirir."""
        if v is None or v == "":
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            # YYYY-MM-DD formatını dene
            try:
                return date.fromisoformat(v)
            except ValueError:
                pass
            # DD.MM.YYYY formatını dene (Türk formatı)
            try:
                parts = v.split(".")
                if len(parts) == 3:
                    return date(int(parts[2]), int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                pass
            # DD/MM/YYYY formatını dene
            try:
                parts = v.split("/")
                if len(parts) == 3:
                    return date(int(parts[2]), int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                pass
        return None

    @field_validator("ara_toplam", "kdv_toplam", "genel_toplam", mode="before")
    @classmethod
    def coerce_totals(cls, v: object) -> Decimal | None:
        """Toplam alanlarını Decimal'e çevirir."""
        if v is None or v == "":
            return None
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except Exception:
            return None
