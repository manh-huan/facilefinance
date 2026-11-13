"""Matching keys for names read from user files."""

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def name_key(name: str) -> str:
    """NFC-normalized, trimmed, whitespace-collapsed, casefolded name.

    Diacritics are never stripped: "Hà Nội" and "Ha Noi" are different keys. Used for
    ``counterparties.name_key`` so the same counterparty is not duplicated by stray
    spaces, case or Unicode composition differences. When an import maps two different
    raw spellings to one key, the importer adds a warning to ``import_report`` listing
    both spellings, so a wrong merge is visible.
    """
    text = unicodedata.normalize("NFC", name)
    text = _WHITESPACE.sub(" ", text).strip()
    return unicodedata.normalize("NFC", text.casefold())
