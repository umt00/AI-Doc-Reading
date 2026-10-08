"""Unit tests for Pydantic extraction and response schemas."""

from datetime import date
from decimal import Decimal

from src.schemas.extraction import FaturaKalemi, FaturaVerisi
from src.schemas.response import APIResponse, ExtractionMetadata


def test_fatura_kalemi_decimal_coercion():
    kalem = FaturaKalemi(
        urun_adi="Klavye",
        adet="5",
        birim="Adet",
        birim_fiyat=120.50,
        kdv_orani=20,
        toplam_tutar="723.00",
    )
    assert kalem.adet == Decimal("5")
    assert isinstance(kalem.birim_fiyat, Decimal)
    assert kalem.kdv_orani == Decimal("20")
    assert kalem.toplam_tutar == Decimal("723.00")


def test_fatura_verisi_date_parsing_iso():
    data = FaturaVerisi(
        tarih="2024-05-18",
        vade_tarihi="2024-06-18",
    )
    assert data.tarih == date(2024, 5, 18)
    assert data.vade_tarihi == date(2024, 6, 18)


def test_fatura_verisi_date_parsing_turkish_dot():
    data = FaturaVerisi(
        tarih="18.05.2024",
    )
    assert data.tarih == date(2024, 5, 18)


def test_fatura_verisi_date_parsing_slash():
    data = FaturaVerisi(
        tarih="18/05/2024",
    )
    assert data.tarih == date(2024, 5, 18)


def test_fatura_verisi_totals_coercion():
    data = FaturaVerisi(
        ara_toplam="1000.50",
        kdv_toplam=200.10,
        genel_toplam="1200.60",
    )
    assert data.ara_toplam == Decimal("1000.50")
    assert data.genel_toplam == Decimal("1200.60")


def test_api_response_wrapper():
    fatura = FaturaVerisi(fatura_no="TEST-001")
    metadata = ExtractionMetadata(
        dosya_adi="test.pdf",
        dosya_boyutu_kb=120.4,
        sayfa_sayisi=1,
        kullanilan_model="prebuilt-layout",
        llm_model="gpt-4o",
        islem_suresi_sn=1.25,
    )
    res = APIResponse[FaturaVerisi](
        success=True,
        data=fatura,
        metadata=metadata,
    )
    dumped = res.model_dump()
    assert dumped["success"] is True
    assert dumped["data"]["fatura_no"] == "TEST-001"
    assert dumped["metadata"]["islem_suresi_sn"] == 1.25
