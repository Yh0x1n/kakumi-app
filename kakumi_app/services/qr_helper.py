"""
QR Code generation helper.
Produces SSR-safe data URIs with no file I/O.
"""

from io import BytesIO
import base64

import qrcode


def _make_qr_data_url(url: str) -> str:
    """Generate a QR code image and return as base64 data URI.

    Args:
        url: URL string to encode in QR.

    Returns:
        Data URI string: data:image/png;base64,<encoded>
    """
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"
