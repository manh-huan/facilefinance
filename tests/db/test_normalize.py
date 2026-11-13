import unicodedata

from facilefinance.db.normalize import name_key


def test_trims_collapses_whitespace_and_casefolds() -> None:
    assert name_key("  Công   ty\tTNHH  Mẫu 01 ") == "công ty tnhh mẫu 01"


def test_unicode_composition_does_not_matter() -> None:
    composed = unicodedata.normalize("NFC", "Công ty Mẫu")
    decomposed = unicodedata.normalize("NFD", "Công ty Mẫu")
    assert composed != decomposed
    assert name_key(composed) == name_key(decomposed)


def test_diacritics_are_kept() -> None:
    assert name_key("Cong ty") != name_key("Công ty")
