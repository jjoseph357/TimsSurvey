import pytest

from sites import detect_site


@pytest.mark.parametrize("raw, site, code", [
    ("1234-5678-9012-3456-78901", "tims", "123456789012345678901"),
    ("123456789012345678901", "tims", "123456789012345678901"),
    ("3BNM6JL4021TG12", "dq", "3BNM6JL4021TG12"),
    (" 3bnm-6jl4-021tg12 ", "dq", "3BNM6JL4021TG12"),
    ("3BNM6JL4O21TG12", "dq", "3BNM6JL4021TG12"),  # DQ codes never contain the letter O
])
def test_detects_site_and_normalizes_code(raw, site, code):
    assert detect_site(raw) == (site, code)


@pytest.mark.parametrize("raw", ["", "12345", "1234567890123456789012", "3BNM6JL4021TG1!"])
def test_rejects_unrecognized_codes(raw):
    assert detect_site(raw) is None
