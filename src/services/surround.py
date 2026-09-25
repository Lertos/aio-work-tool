"""Wrap every line of a block of text in a prefix and suffix (Surround tab)."""
from __future__ import annotations

from ..model.items import SurroundItem

SEPARATORS = ",;"


def final_suffix(suffix: str) -> str:
    """The suffix minus one trailing separator (and trailing spaces): ``"', "`` -> ``"'"``."""
    trimmed = suffix.rstrip()
    if trimmed and trimmed[-1] in SEPARATORS:
        return trimmed[:-1]
    return suffix


def surround(text: str, item: SurroundItem) -> str:
    """Trim each line and wrap it as ``prefix + line + suffix``; blank lines are dropped.

    With ``remove_final_suffix`` the last line loses the trailing separator in the
    suffix, so ``'a',`` ``'b',`` ends in ``'c'`` rather than ``'c',``.
    """
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    out = [f"{item.prefix}{line}{item.suffix}" for line in lines]
    if out and item.remove_final_suffix:
        out[-1] = f"{item.prefix}{lines[-1]}{final_suffix(item.suffix)}"
    return "\n".join(out)
