from __future__ import annotations

from io import BytesIO
from urllib.parse import quote

from app.services.hash_service import calculate_sha256
from app.services.qrcode_service import build_verification_url, generate_qr_code_image


def authenticate_pdf(pdf_bytes: bytes, verification_url: str) -> bytes:
    if not pdf_bytes:
        raise ValueError("O conteúdo do PDF não pode estar vazio.")

    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:  # pragma: no cover
        marker = (
            b"% AUTENTICADOR MACROAMBIENTAL\n"
            + quote(verification_url, safe="").encode("utf-8")
            + b"\n"
        )
        if b"%%EOF" in pdf_bytes:
            return pdf_bytes.replace(b"%%EOF", marker + b"%%EOF", 1)
        return pdf_bytes + marker

    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    qr_image = generate_qr_code_image(verification_url)
    png_buffer = BytesIO()
    qr_image.save(png_buffer, format="PNG")
    qr_png = png_buffer.getvalue()

    page = writer.pages[0]
    page.merge_page(page)
    return b"".join([pdf_bytes[:10], b"% QR CODE AUTENTICADO ", qr_png, b"% END QR CODE ", pdf_bytes[10:]])


def verify_pdf_against_hash(pdf_bytes: bytes, expected_hash: str) -> bool:
    return calculate_sha256(pdf_bytes) == expected_hash
