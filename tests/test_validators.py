"""Unit tests for file validators."""

import io

import pytest
from fastapi import UploadFile

from src.utils.validators import (
    FileValidationError,
    detect_mime_type,
    validate_file,
)


def create_upload_file(
    filename: str,
    content: bytes,
    content_type: str = "application/pdf",
) -> UploadFile:
    file_obj = io.BytesIO(content)
    upload = UploadFile(
        file=file_obj,
        filename=filename,
        headers={"content-type": content_type},
    )
    return upload


@pytest.mark.asyncio
async def test_validate_file_empty_filename():
    file = create_upload_file(filename="", content=b"%PDF-1.4 test %%EOF")
    with pytest.raises(FileValidationError) as exc:
        await validate_file(file, max_size_bytes=1024 * 1024)
    assert exc.value.code == "EMPTY_FILENAME"


@pytest.mark.asyncio
async def test_validate_file_empty_content():
    file = create_upload_file(filename="test.pdf", content=b"")
    with pytest.raises(FileValidationError) as exc:
        await validate_file(file, max_size_bytes=1024 * 1024)
    assert exc.value.code == "EMPTY_FILE"


@pytest.mark.asyncio
async def test_validate_file_too_large():
    file = create_upload_file(filename="test.pdf", content=b"A" * 200)
    with pytest.raises(FileValidationError) as exc:
        await validate_file(file, max_size_bytes=100)
    assert exc.value.code == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_validate_file_unsupported_format():
    file = create_upload_file(
        filename="test.txt",
        content=b"Hello world text file",
        content_type="text/plain",
    )
    with pytest.raises(FileValidationError) as exc:
        await validate_file(file, max_size_bytes=1024 * 1024)
    assert exc.value.code == "INVALID_FILE_FORMAT"


@pytest.mark.asyncio
async def test_validate_file_corrupted_pdf():
    file = create_upload_file(
        filename="test.pdf",
        content=b"NOT_A_PDF_FILE",
        content_type="application/pdf",
    )
    with pytest.raises(FileValidationError) as exc:
        await validate_file(file, max_size_bytes=1024 * 1024)
    assert exc.value.code == "CORRUPTED_FILE"


@pytest.mark.asyncio
async def test_validate_file_encrypted_pdf_marker():
    # Mock PDF with /Encrypt marker
    content = b"%PDF-1.4 /Encrypt 12 0 R %%EOF"
    file = create_upload_file(filename="test.pdf", content=content, content_type="application/pdf")
    with pytest.raises(FileValidationError) as exc:
        await validate_file(file, max_size_bytes=1024 * 1024)
    assert exc.value.code == "ENCRYPTED_PDF"


@pytest.mark.asyncio
async def test_validate_file_valid_pdf():
    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    file = create_upload_file(filename="invoice.pdf", content=valid_pdf_content)
    content, mime = await validate_file(file, max_size_bytes=1024 * 1024)
    assert content == valid_pdf_content
    assert mime == "application/pdf"


@pytest.mark.asyncio
async def test_validate_file_valid_png():
    # PNG signature: \x89PNG\r\n\x1a\n
    png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    file = create_upload_file(filename="receipt.png", content=png_content, content_type="image/png")
    content, mime = await validate_file(file, max_size_bytes=1024 * 1024)
    assert content == png_content
    assert mime == "image/png"


def test_detect_mime_type():
    assert detect_mime_type(b"%PDF-1.7") == "application/pdf"
    assert detect_mime_type(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert detect_mime_type(b"\x89PNG\r\n") == "image/png"
    assert detect_mime_type(b"UNKNOWN") is None
