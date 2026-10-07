from __future__ import annotations

from urllib.parse import quote

try:
    import qrcode
except ImportError:  # pragma: no cover
    qrcode = None


def build_verification_url(public_id: str, base_url: str = "https://autenticador.macroambiental.com.br") -> str:
    normalized_base = base_url.rstrip("/")
    encoded_public_id = quote(str(public_id), safe="")
    return f"{normalized_base}/verificar/{encoded_public_id}"


def generate_qr_code_image(url: str, *, size: int = 8, border: int = 2):
    if qrcode is None:
        raise RuntimeError("A biblioteca 'qrcode' não está instalada.")
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")
