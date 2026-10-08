"""Unit tests for the RouterService."""

from src.services.router_service import RouterService


def test_router_mime_and_size_images():
    router = RouterService()
    decision = router.decide_from_mime_and_size("image/png", 50_000)
    assert decision.model == "prebuilt-layout"
    assert "Görsel dosya" in decision.reason


def test_router_mime_and_size_large_file():
    router = RouterService()
    decision = router.decide_from_mime_and_size("application/pdf", 6 * 1024 * 1024)
    assert decision.model == "prebuilt-layout"
    assert "Büyük dosya" in decision.reason


def test_router_content_analysis_invoice_keywords():
    router = RouterService()
    sample_text = (
        "Fatura No: GIB20240001\n"
        "Birim Fiyat: 150.00 TL\n"
        "KDV: 30.00 TL\n"
        "Genel Toplam: 180.00 TL\n"
    )
    decision = router.analyze_content_for_routing(sample_text)
    assert decision.model == "prebuilt-layout"
    assert len(decision.keyword_hits) >= 3


def test_router_content_analysis_plain_text():
    router = RouterService()
    sample_text = "Bu sadece bir duyuru metnidir. Şirket genel kurul toplantısı yapılacaktır."
    decision = router.analyze_content_for_routing(sample_text)
    assert decision.model == "prebuilt-read"
    assert "Basit metin" in decision.reason
