"""
Penta Document Intelligence — Ana Uygulama

FastAPI tabanlı REST API. Doküman yükleme, OCR, LLM extraction
ve doğrulanmış JSON çıktı pipeline'ını yönetir.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.schemas.extraction import FaturaVerisi
from src.schemas.response import (
    APIResponse,
    ErrorDetail,
    ErrorResponse,
    ExtractionMetadata,
    HealthResponse,
)
from src.services.llm_service import LLMExtractionError, LLMService
from src.services.ocr_service import OCRService
from src.services.router_service import RouterService
from src.utils.validators import FileValidationError, validate_file

# ─── Logging Konfigürasyonu ───────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Servis Instance'ları (Lifespan ile yönetilir) ────────────
_ocr_service: OCRService | None = None
_llm_service: LLMService | None = None
_router_service: RouterService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Uygulama yaşam döngüsü yöneticisi.

    Başlangıçta Azure client'larını oluşturur,
    kapanışta temiz bir şekilde kapatır.
    """
    global _ocr_service, _llm_service, _router_service

    settings = get_settings()

    logger.info("═" * 60)
    logger.info("Penta Document Intelligence başlatılıyor...")
    logger.info("═" * 60)

    # Servisleri başlat (kimlik bilgileri eksikse graceful fallback)
    try:
        _ocr_service = OCRService(settings)
    except Exception as e:
        logger.warning(
            "OCR Service başlatılamadı (Azure kimlik bilgileri yapılandırılmamış olabilir): %s",
            e,
        )
        _ocr_service = None

    try:
        _llm_service = LLMService(settings)
    except Exception as e:
        logger.warning(
            "LLM Service başlatılamadı "
            "(Azure OpenAI kimlik bilgileri yapılandırılmamış olabilir): %s",
            e,
        )
        _llm_service = None

    _router_service = RouterService()

    if _ocr_service and _llm_service:
        logger.info("Tüm servisler hazır.")
    else:
        logger.warning(
            "Uygulama eksik Azure konfigürasyonu ile başlatıldı (degraded mod)."
        )

    yield  # Uygulama çalışıyor

    # Temiz kapanış
    logger.info("Servisler kapatılıyor...")
    if _ocr_service:
        _ocr_service.close()
    if _llm_service:
        _llm_service.close()
    logger.info("Uygulama kapatıldı.")


# ─── FastAPI Uygulaması ───────────────────────────────────────
app = FastAPI(
    title="AI Document Reading API",
    description=(
        "Azure AI Document Intelligence ve Azure OpenAI (GPT-4o) ile "
        "fatura ve irsaliye dokümanlarından train-free / zero-shot "
        "akıllı veri çıkarma REST API prototipi."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS Middleware ──────────────────────────────────────────
# Not: CORS ayarları uygulama başlangıcında yapılandırılır.
# .env yüklenmeden önce default değerler kullanılır.
try:
    _cors_settings = get_settings()
    _cors_origins = _cors_settings.cors_origins
except Exception:
    _cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global Exception Handler ────────────────────────────────
@app.exception_handler(FileValidationError)
async def file_validation_handler(
    request: object,
    exc: FileValidationError,
) -> JSONResponse:
    """Dosya doğrulama hatalarını 400 Bad Request olarak döndürür."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
            )
        ).model_dump(),
    )


@app.exception_handler(LLMExtractionError)
async def llm_extraction_handler(
    request: object,
    exc: LLMExtractionError,
) -> JSONResponse:
    """LLM extraction hatalarını 422 olarak döndürür."""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                detail=exc.detail,
            )
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: object,
    exc: Exception,
) -> JSONResponse:
    """Beklenmeyen hataları 500 Internal Server Error olarak döndürür."""
    logger.exception("Beklenmeyen hata: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="Sunucu hatası oluştu. Lütfen tekrar deneyin.",
                detail=str(exc),
            )
        ).model_dump(),
    )


# ─── Health Check ─────────────────────────────────────────────
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Sistem"],
    summary="Sağlık kontrolü",
    description="API ve bağlı servislerin durumunu kontrol eder.",
)
async def health_check() -> HealthResponse:
    """Servis sağlık durumunu döndürür."""
    is_ready = bool(_ocr_service and _llm_service and _router_service)
    return HealthResponse(
        status="healthy" if is_ready else "degraded",
        version="0.1.0",
        services={
            "ocr_service": "ready" if _ocr_service else "not_configured",
            "llm_service": "ready" if _llm_service else "not_configured",
            "router_service": "ready" if _router_service else "not_initialized",
        },
    )


# ─── Ana Extraction Endpoint ─────────────────────────────────
@app.post(
    "/api/v1/extract",
    response_model=APIResponse[FaturaVerisi],
    tags=["Doküman İşleme"],
    summary="Doküman veri ayıklama",
    description=(
        "Fatura veya irsaliye dokümanını yükleyerek otomatik veri ayıklama yapar. "
        "PDF, JPEG ve PNG formatlarını destekler. Maksimum dosya boyutu: 50 MB."
    ),
    responses={
        200: {"description": "Başarılı — Ayıklanan veri döndürüldü"},
        400: {"description": "Geçersiz dosya — Format, boyut veya şifre hatası"},
        422: {"description": "Veri ayıklama hatası — LLM veya doğrulama başarısız"},
        500: {"description": "Sunucu hatası"},
    },
)
async def extract_document(
    file: UploadFile = File(
        ...,
        description="İşlenecek doküman dosyası (PDF, JPEG, PNG)",
    ),
) -> APIResponse[FaturaVerisi]:
    """
    Doküman işleme pipeline'ı:

    1. **Dosya Doğrulama**: Format, boyut ve bütünlük kontrolü
    2. **Akıllı Yönlendirme**: Heuristic analiz ile Read/Layout seçimi
    3. **OCR Analizi**: Azure Document Intelligence ile Markdown çıktı
    4. **LLM Extraction**: GPT-4o ile zero-shot veri ayıklama
    5. **Pydantic Doğrulama**: Tip güvenli veri validasyonu
    """
    start_time = time.time()
    current_settings = get_settings()

    # Servis kontrolü
    if not _ocr_service or not _llm_service or not _router_service:
        raise HTTPException(
            status_code=503,
            detail="Servisler henüz başlatılmadı.",
        )

    # ── Faz 1: Dosya Doğrulama ────────────────────────────────
    logger.info("═" * 50)
    logger.info("Yeni istek: %s", file.filename)
    logger.info("═" * 50)

    file_content, mime_type = await validate_file(
        file=file,
        max_size_bytes=current_settings.max_file_size_bytes,
    )

    file_size_kb = len(file_content) / 1024

    # ── Faz 2: Akıllı Yönlendirme ────────────────────────────
    routing_decision = _router_service.decide_from_mime_and_size(
        mime_type=mime_type,
        file_size_bytes=len(file_content),
    )

    logger.info(
        "Yönlendirme: %s (güvenirlik: %.2f)",
        routing_decision.model,
        routing_decision.confidence,
    )

    # ── Faz 3: OCR Analizi ────────────────────────────────────
    ocr_result = await _ocr_service.analyze(
        file_content=file_content,
        model_id=routing_decision.model,
    )

    # Eğer Read ile başladıysak ve tablo tespit edildiyse,
    # Layout ile tekrar analiz et
    if routing_decision.model == "prebuilt-read" and ocr_result.content:
        content_routing = _router_service.analyze_content_for_routing(
            ocr_result.content
        )
        if content_routing.model == "prebuilt-layout":
            logger.info(
                "İçerik analizi sonrası Layout'a yönlendiriliyor: %s",
                content_routing.reason,
            )
            ocr_result = await _ocr_service.analyze(
                file_content=file_content,
                model_id="prebuilt-layout",
            )

    if not ocr_result.content or len(ocr_result.content.strip()) == 0:
        raise HTTPException(
            status_code=422,
            detail="Doküman içeriği okunamadı. Dosyanın metin içerdiğinden emin olun.",
        )

    # ── Faz 4: LLM Extraction ────────────────────────────────
    llm_result = await _llm_service.extract_invoice_data(
        document_content=ocr_result.content,
    )

    # ── Faz 5: Yanıt Oluşturma ───────────────────────────────
    elapsed = time.time() - start_time

    metadata = ExtractionMetadata(
        dosya_adi=file.filename or "unknown",
        dosya_boyutu_kb=round(file_size_kb, 2),
        sayfa_sayisi=ocr_result.page_count,
        kullanilan_model=ocr_result.model_id,
        llm_model=llm_result.model,
        islem_suresi_sn=round(elapsed, 2),
        llm_token_kullanimi=llm_result.token_usage,
    )

    logger.info(
        "İşlem tamamlandı — Süre: %.2f sn, Model: %s, Fatura No: %s",
        elapsed,
        ocr_result.model_id,
        llm_result.extracted_data.fatura_no,
    )

    return APIResponse[FaturaVerisi](
        success=True,
        data=llm_result.extracted_data,
        metadata=metadata,
    )


# ─── Doğrudan Çalıştırma ─────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    run_settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=run_settings.uvicorn_host,
        port=run_settings.uvicorn_port,
        reload=True,
    )
