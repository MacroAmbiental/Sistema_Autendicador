"""Gera um PDF valido, com QR visivel e rodape reservado em todas as paginas."""
from __future__ import annotations

from io import BytesIO

from app.services.hash_service import calculate_sha256
from app.services.qrcode_service import generate_qr_code_image


def authenticate_pdf(pdf_bytes: bytes, verification_url: str) -> bytes:
    if not pdf_bytes or not pdf_bytes.lstrip().startswith(b"%PDF-"):
        raise ValueError("Envie um arquivo PDF valido.")

    import fitz

    try:
        source = fitz.open(stream=pdf_bytes, filetype="pdf")
        if source.is_encrypted or source.page_count == 0:
            raise ValueError("PDF criptografado ou vazio nao e aceito.")
        output = fitz.open()
        qr = generate_qr_code_image(verification_url)
        png = BytesIO()
        qr.save(png, format="PNG")
        qr_bytes = png.getvalue()
        try:
            for index, source_page in enumerate(source):
                bounds = source_page.rect
                if bounds.width < 160 or bounds.height < 180:
                    raise ValueError("Pagina PDF muito pequena para o selo de verificacao.")
                page = output.new_page(width=bounds.width, height=bounds.height)
                # Deixar margem inferior livre evita encobrir campos e assinaturas.
                qr_side = min(65, bounds.width * 0.20)
                footer_height = qr_side + 13
                target = fitz.Rect(4, 4, bounds.width - 4, bounds.height - footer_height)
                page.show_pdf_page(target, source, index, keep_proportion=True)
                qr_rect = fitz.Rect(8, bounds.height - qr_side - 6, 8 + qr_side, bounds.height - 6)
                page.insert_image(qr_rect, stream=qr_bytes)
                page.insert_text((qr_side + 15, bounds.height - 38), "AUTENTICADOR MACROAMBIENTAL", fontsize=8)
                page.insert_text((qr_side + 15, bounds.height - 25), "Aponte a camera para validar esta versao", fontsize=7)
                page.insert_text((qr_side + 15, bounds.height - 13), "Confira o arquivo oficial no portal de verificacao", fontsize=6.5)
            return output.tobytes(garbage=4, deflate=True, no_new_id=True)
        finally:
            output.close()
            source.close()
    except (RuntimeError, ValueError) as exc:
        raise ValueError("PDF invalido ou impossivel de processar: " + str(exc)) from exc


def verify_pdf_against_hash(pdf_bytes: bytes, expected_hash: str) -> bool:
    # Um upload para verificacao nao deve receber um segundo QR / ser reserializado.
    return calculate_sha256(pdf_bytes) == expected_hash
