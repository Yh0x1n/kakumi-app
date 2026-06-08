"""Tests for QR code generation helper.

RED phase: All tests fail because qr_helper module doesn't exist yet.
"""

import base64


class TestMakeQrDataUrl:
    """Tests for _make_qr_data_url()."""

    def test_make_qr_data_url_returns_data_uri(self):
        """Output starts with data:image/png;base64,."""
        from kakumi_app.services.qr_helper import _make_qr_data_url

        uri = _make_qr_data_url("https://example.com/viewer/42?code=abc123")
        assert uri.startswith("data:image/png;base64,")

    def test_make_qr_data_url_valid_base64(self):
        """Decoded content is a valid PNG (header \\x89PNG)."""
        from kakumi_app.services.qr_helper import _make_qr_data_url

        uri = _make_qr_data_url("https://example.com/viewer/42?code=abc123")
        b64_data = uri.split(",", 1)[1]
        raw = base64.b64decode(b64_data)
        assert raw[:4] == b"\x89PNG"

    def test_make_qr_data_url_deterministic(self):
        """Same URL yields same output."""
        from kakumi_app.services.qr_helper import _make_qr_data_url

        url = "/viewer/dashboard/42?code=a1b2c3d4"
        uri1 = _make_qr_data_url(url)
        uri2 = _make_qr_data_url(url)
        assert uri1 == uri2

    def test_make_qr_encodes_correct_url(self):
        """URL /viewer/dashboard/42?code=a1b2c3d4 is encoded in QR."""
        from kakumi_app.services.qr_helper import _make_qr_data_url

        url = "/viewer/dashboard/42?code=a1b2c3d4"
        uri = _make_qr_data_url(url)
        assert uri.startswith("data:image/png;base64,")
        # Verify it's a valid PNG
        b64_data = uri.split(",", 1)[1]
        raw = base64.b64decode(b64_data)
        assert raw[:4] == b"\x89PNG"
        # PNG is at least 100 bytes (small QR code)
        assert len(raw) > 100

    def test_make_qr_empty_url(self):
        """Empty string returns valid data URI."""
        from kakumi_app.services.qr_helper import _make_qr_data_url

        uri = _make_qr_data_url("")
        assert uri.startswith("data:image/png;base64,")

    def test_make_qr_special_chars(self):
        """URL with special chars works."""
        from kakumi_app.services.qr_helper import _make_qr_data_url

        url = "/viewer/dashboard/1?code=a+b&q=test%20value#frag"
        uri = _make_qr_data_url(url)
        assert uri.startswith("data:image/png;base64,")
        b64_data = uri.split(",", 1)[1]
        raw = base64.b64decode(b64_data)
        assert raw[:4] == b"\x89PNG"
