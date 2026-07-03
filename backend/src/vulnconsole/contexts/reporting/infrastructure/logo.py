"""Company logo handling: inline a logo file as a data URI, or fall back to a
generated monogram so a report always looks intentional and branded."""

import base64
from pathlib import Path

_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}


def logo_data_uri(logo_path: str) -> str | None:
    if not logo_path:
        return None
    path = Path(logo_path)
    if not path.is_file():
        return None
    mime = _MIME_BY_SUFFIX.get(path.suffix.lower())
    if mime is None:
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def monogram(company_name: str) -> str:
    """Up to two initials from the company name, for the fallback logo mark."""
    words = [w for w in company_name.split() if w]
    if not words:
        return "VC"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()
