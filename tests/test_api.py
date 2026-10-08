"""Integration tests for FastAPI application endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import src.main as main_module
from src.main import app
from src.schemas.extraction import FaturaVerisi
from src.services.llm_service import LLMResult
from src.services.ocr_service import OCRResult
from src.services.router_service import RouterService


def test_health_check_endpoint_degraded_when_unconfigured():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["ocr_service"] == "not_configured"


def test_health_check_endpoint_healthy_when_configured():
    with TestClient(app) as client:
        main_module._ocr_service = MagicMock()
        main_module._llm_service = MagicMock()
        main_module._router_service = RouterService()

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["ocr_service"] == "ready"
        assert data["services"]["llm_service"] == "ready"


def test_extract_endpoint_503_when_services_not_ready():
    with TestClient(app) as client:
        main_module._ocr_service = None
        main_module._llm_service = None

        response = client.post(
            "/api/v1/extract",
            files={"file": ("test.pdf", b"%PDF-1.4 %%EOF", "application/pdf")},
        )
        assert response.status_code == 503


def test_extract_endpoint_empty_file():
    with TestClient(app) as client:
        main_module._ocr_service = MagicMock()
        main_module._llm_service = MagicMock()
        main_module._router_service = RouterService()

        response = client.post(
            "/api/v1/extract",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "EMPTY_FILE"


def test_extract_endpoint_invalid_file_format():
    with TestClient(app) as client:
        main_module._ocr_service = MagicMock()
        main_module._llm_service = MagicMock()
        main_module._router_service = RouterService()

        response = client.post(
            "/api/v1/extract",
            files={"file": ("test.txt", b"Invalid content", "text/plain")},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_FILE_FORMAT"


@pytest.mark.asyncio
async def test_extract_endpoint_success_flow():
    mock_ocr = MagicMock()
    mock_ocr.analyze = AsyncMock(
        return_value=OCRResult(
            content="# Fatura\nFatura No: FT-123\nToplam: 500 TL",
            page_count=1,
            model_id="prebuilt-layout",
            tables_detected=1,
        )
    )

    mock_llm = MagicMock()
    mock_llm.extract_invoice_data = AsyncMock(
        return_value=LLMResult(
            extracted_data=FaturaVerisi(
                fatura_no="FT-123",
                tedarikci_unvan="Test Ltd.",
            ),
            raw_response='{"fatura_no": "FT-123"}',
            model="gpt-4o",
            token_usage={"total_tokens": 150},
        )
    )

    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    with TestClient(app) as client:
        main_module._ocr_service = mock_ocr
        main_module._llm_service = mock_llm
        main_module._router_service = RouterService()

        response = client.post(
            "/api/v1/extract",
            files={"file": ("fatura.pdf", valid_pdf_content, "application/pdf")},
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert json_resp["success"] is True
        assert json_resp["data"]["fatura_no"] == "FT-123"
        assert json_resp["metadata"]["kullanilan_model"] == "prebuilt-layout"
        assert json_resp["metadata"]["llm_model"] == "gpt-4o"

