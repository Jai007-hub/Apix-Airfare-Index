import re

_AMOUNT_RE = re.compile(r"[\d,]+(?:\.\d+)?")


def parse_amount(text: str | None) -> float | None:
    """Extracts a numeric amount from strings like 'Rs. 8,428' or 'INR 1,382.50'.
    Returns None if no number is found."""
    if not text:
        return None
    match = _AMOUNT_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None
