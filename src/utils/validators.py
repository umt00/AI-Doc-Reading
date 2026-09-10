"""
Penta Document Intelligence — Dosya Doğrulama Modülü

Yüklenen dosyaların format, boyut ve bütünlük kontrollerini yapar.
Geçersiz dosyalar Azure API'lerine gönderilmeden reddedilir.
"""

from __future__ import annotations

import io
import logging
from typing import NamedTuple

from fastapi import UploadFile

logger = logging.getLogger(__name__)

# ─── Desteklenen MIME türleri ve magic byte imzaları ──────────
ALLOWED_MIME_TYPES: dict[str, str] = {
    "application/pdf": "PDF",
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/tiff": "TIFF",
    "image/bmp": "BMP",
}

# Magic bytes ile dosya formatı tespiti (ilk N byte)
MAGIC_BYTES: dict[bytes, str] = {
    b"%PDF": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"II\x2a\x00": "image/tiff",  # Little-endian TIFF
    b"MM\x00\x2a": "image/tiff",  # Big-endian TIFF
    b"BM": "image/bmp",
}

# Şifreli PDF göstergeleri
PDF_ENCRYPT_MARKERS = [b"/Encrypt", b"/Standard"]


class ValidationResult(NamedTuple):
    """Doğrulama sonucu."""

    is_valid: bool
    error_code: str | None = None
    error_message: str | None = None


class FileValidationError(Exception):
    """Dosya doğrulama hatası."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def detect_mime_type(file_header: bytes) -> str | None:
    """
    Dosyanın ilk byte'larından MIME türünü tespit eder.

    Magic byte kontrolü ile Content-Type header'ına güvenmek yerine
    gerçek dosya formatını belirler.
    """
    for magic, mime_type in MAGIC_BYTES.items():
        if file_header[: len(magic)] == magic:
            return mime_type
    return None


async def validate_file(
    file: UploadFile,
    max_size_bytes: int,
) -> tuple[bytes, str]:
    """
    Yüklenen dosyayı kapsamlı şekilde doğrular.

    Kontroller:
    1. Dosya boş mu?
    2. Dosya formatı destekleniyor mu? (magic bytes)
    3. Dosya boyutu limitin altında mı?
    4. PDF ise şifreli mi?
    5. Dosya bütünlüğü sağlam mı?

    Returns:
        tuple[bytes, str]: (dosya içeriği, tespit edilen MIME türü)

    Raises:
        FileValidationError: Doğrulama başarısız olursa
    """
    # ── 1. Dosya var mı? ──────────────────────────────────────
    if file.filename is None or file.filename.strip() == "":
        raise FileValidationError(
            code="EMPTY_FILENAME",
            message="Dosya adı boş olamaz.",
        )

    # Dosya içeriğini oku
    content = await file.read()

    if len(content) == 0:
        raise FileValidationError(
            code="EMPTY_FILE",
            message="Yüklenen dosya boş.",
        )

    # ── 2. Dosya boyutu kontrolü ──────────────────────────────
    if len(content) > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        file_mb = len(content) / (1024 * 1024)
        raise FileValidationError(
            code="FILE_TOO_LARGE",
            message=(
                f"Dosya boyutu ({file_mb:.1f} MB) maksimum limiti ({max_mb:.0f} MB) aşıyor."
            ),
        )

    # ── 3. Format kontrolü (magic bytes) ──────────────────────
    detected_mime = detect_mime_type(content[:16])

    if detected_mime is None:
        # Fallback: Content-Type header'ına bak
        if file.content_type in ALLOWED_MIME_TYPES:
            detected_mime = file.content_type
        else:
            raise FileValidationError(
                code="INVALID_FILE_FORMAT",
                message=(
                    f"Desteklenmeyen dosya formatı. "
                    f"Kabul edilen formatlar: {', '.join(ALLOWED_MIME_TYPES.values())}"
                ),
            )

    if detected_mime not in ALLOWED_MIME_TYPES:
        raise FileValidationError(
            code="INVALID_FILE_FORMAT",
            message=(
                f"Desteklenmeyen dosya formatı: {detected_mime}. "
                f"Kabul edilen formatlar: {', '.join(ALLOWED_MIME_TYPES.values())}"
            ),
        )

    # ── 4. PDF şifre kontrolü ─────────────────────────────────
    if detected_mime == "application/pdf":
        _check_pdf_encrypted(content)
        _check_pdf_integrity(content)

    logger.info(
        "Dosya doğrulandı: %s (%.1f KB, %s)",
        file.filename,
        len(content) / 1024,
        ALLOWED_MIME_TYPES[detected_mime],
    )

    return content, detected_mime


def _check_pdf_encrypted(content: bytes) -> None:
    """
    PDF dosyasının şifreli olup olmadığını kontrol eder.

    PyPDF ile detaylı kontrol yapar; başarısız olursa
    raw byte taramasına düşer.
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise FileValidationError(
                code="ENCRYPTED_PDF",
                message="Şifreli PDF dosyaları işlenemiyor. Lütfen şifresiz bir dosya yükleyin.",
            )
    except FileValidationError:
        raise
    except Exception:
        # PyPDF ile okunamıyorsa raw byte kontrolü yap
        for marker in PDF_ENCRYPT_MARKERS:
            # İlk 4KB'da /Encrypt var mı kontrol et
            if marker in content[:4096]:
                raise FileValidationError(
                    code="ENCRYPTED_PDF",
                    message="Şifreli PDF dosyaları işlenemiyor. Lütfen şifresiz bir dosya yükleyin.",
                )


def _check_pdf_integrity(content: bytes) -> None:
    """
    PDF dosyasının temel bütünlük kontrolünü yapar.

    PDF header ve trailer varlığını doğrular.
    """
    # PDF header kontrolü
    if not content[:5].startswith(b"%PDF-"):
        raise FileValidationError(
            code="CORRUPTED_FILE",
            message="Bozuk PDF dosyası: Geçerli PDF başlığı bulunamadı.",
        )

    # PDF trailer kontrolü (son 1KB'da %%EOF olmalı)
    tail = content[-1024:]
    if b"%%EOF" not in tail:
        logger.warning(
            "PDF dosyasında %%EOF bulunamadı — dosya eksik/bozuk olabilir."
        )
