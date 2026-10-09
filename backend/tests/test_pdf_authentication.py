"""Testes atuais de integridade: PDF de verdade e bytes imutaveis."""
import hashlib
from io import BytesIO
from reportlab.pdfgen import canvas
import fitz
import pytest

from app.services.hash_service import calculate_sha256
from app.services.pdf_service import authenticate_pdf, verify_pdf_against_hash


def _pdf():
    out = BytesIO()
    builder = canvas.Canvas(out, invariant=1)
    builder.drawString(40, 750, "CHECKLIST")
    builder.save()
    return out.getvalue()


def test_hash_service_calculates_sha256_for_bytes():
    payload = b"documento autentico"
    assert calculate_sha256(payload) == hashlib.sha256(payload).hexdigest()


def test_authenticate_pdf_with_visible_bottom_left_qrcode():
    url = "https://exemplo.com/verificar/TESTE/V1"
    result = authenticate_pdf(_pdf(), url)
    assert result.startswith(b"%PDF-")
    document = fitz.open(stream=result, filetype="pdf")
    assert len(document[0].get_images()) >= 1
    assert "AUTENTICADOR" in document[0].get_text()
    document.close()
    assert verify_pdf_against_hash(result, calculate_sha256(result))
    tampered = result[:-1] + bytes([result[-1] ^ 1])
    assert not verify_pdf_against_hash(tampered, calculate_sha256(result))


def test_invalid_or_incomplete_pdf_is_rejected():
    with pytest.raises(ValueError):
        authenticate_pdf(b"%PDF-1.4\n%%EOF", "https://exemplo.com/verificar/TESTE/V1")


def test_equal_source_produces_identical_document_for_retries():
    url = "https://exemplo.com/verificar/TESTE/V1"
    assert authenticate_pdf(_pdf(), url) == authenticate_pdf(_pdf(), url)
