"""Generate preview.json — the data source for the site's hover cards.

One JSON file keyed by:
- AidOps items:  local path (e.g. "/AnthropometricProfile")
- PublicSchema items: canonical URI (e.g. "https://publicschema.org/Person")

Each entry carries per-locale metadata the hover card needs to render
without round-tripping to the full vocabulary.json.
"""

from typing import Any

DEFAULT_LOCALES = ("en", "fr", "es")
DEFAULT_LOCALE = "en"

# Per-locale character budget for the truncated definition preview.
# French and Spanish prose averages ~15-20% longer than English for the
# same information density, so their limits are higher to keep roughly
# equivalent information in the card.
LOCALE_EXCERPT_LIMIT: dict[str, int] = {
    "en": 220,
    "fr": 260,
    "es": 260,
}


def truncate_excerpt(text: str, limit: int) -> str:
    """Word-boundary-safe truncation with trailing ellipsis.

    If `text` is within `limit`, returns it unchanged. Otherwise cuts at the
    last word boundary at or before `limit` and appends "…". Never produces a
    result that splits a word.
    """
    if not text:
        return ""
    if len(text) <= limit:
        return text
    # Cut at the last whitespace within the budget
    cut = text[:limit]
    last_space = cut.rfind(" ")
    if last_space <= 0:
        # No space found in budget (single extremely long word) — hard cut.
        return cut.rstrip() + "…"
    return cut[:last_space].rstrip() + "…"


def _pick_locale(
    field: dict[str, str] | None, locale: str, fallback: str = DEFAULT_LOCALE
) -> tuple[str, str]:
    """Return (value, locale_used). Falls back to `fallback` when missing."""
    if not field:
        return "", locale
    if locale in field and field[locale]:
        return field[locale], locale
    if fallback in field and field[fallback]:
        return field[fallback], fallback
    # Last resort: any populated locale, in a stable order.
    for candidate in DEFAULT_LOCALES:
        if candidate in field and field[candidate]:
            return field[candidate], candidate
    return "", locale


def _entry_key(item: dict[str, Any]) -> str:
    """Preview key: local path for AidOps items, canonical URI for PS items."""
    if item.get("source") == "aidops":
        return item["path"]
    return item["uri"]


def _build_locale_entry(
    item: dict[str, Any],
    kind: str,
    locale: str,
) -> dict[str, Any]:
    label, _ = _pick_locale(item.get("label"), locale)
    definition, locale_used = _pick_locale(item.get("definition"), locale)
    limit = LOCALE_EXCERPT_LIMIT.get(locale, 220)
    entry: dict[str, Any] = {
        "label": label or item["id"],
        "kind": kind,
        "source": item.get("source", "aidops"),
        "maturity": item.get("maturity", "draft"),
        "href": _entry_key(item),
        "definition_excerpt": truncate_excerpt(definition, limit),
        "locale_used": locale_used,
    }
    if kind == "property":
        entry["type"] = item.get("type", "")
        entry["vocabulary"] = item.get("vocabulary")
    return entry


def build_preview(
    result: dict[str, Any],
    locales: tuple[str, ...] = DEFAULT_LOCALES,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Produce the preview lookup table.

    Returns a dict keyed by preview-key (path or URI). Each value is a
    per-locale dict whose entries carry label, definition excerpt, kind,
    source, maturity, href, and — for properties — type and vocabulary.
    """
    preview: dict[str, dict[str, dict[str, Any]]] = {}

    for concept in result.get("concepts", {}).values():
        key = _entry_key(concept)
        preview[key] = {
            locale: _build_locale_entry(concept, "concept", locale)
            for locale in locales
        }

    for prop in result.get("properties", {}).values():
        key = _entry_key(prop)
        preview[key] = {
            locale: _build_locale_entry(prop, "property", locale)
            for locale in locales
        }

    for vocab in result.get("vocabularies", {}).values():
        key = _entry_key(vocab)
        preview[key] = {
            locale: _build_locale_entry(vocab, "vocabulary", locale)
            for locale in locales
        }

    return preview
