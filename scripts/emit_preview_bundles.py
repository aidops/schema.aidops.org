#!/usr/bin/env python3
"""Emit per-locale hover-card preview bundles from dist/vocabulary.json.

The site's hover-card script (site/src/scripts/hover-card.ts) fetches
`/preview/{locale}.json` lazily and reads a flat map keyed by:
- AidOps items:       local path (e.g. "/AnthropometricProfile")
- PublicSchema items: canonical URI (e.g. "https://publicschema.org/Person")

publicschema-build emits per-item preview files under `dist/preview/<section>/`,
which the script here collapses into the flat per-locale bundles the client
expects. This is a thin compatibility shim; the source of truth is still the
publicschema-build output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LOCALES = ("en", "fr", "es")
DEFAULT_LOCALE = "en"

# Per-locale character budget for the truncated definition preview.
# French and Spanish prose runs ~15-20% longer for the same information
# density, so their limits are higher to keep roughly equivalent content
# in the card.
LOCALE_EXCERPT_LIMIT: dict[str, int] = {"en": 220, "fr": 260, "es": 260}


def truncate_excerpt(text: str, limit: int) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_space = cut.rfind(" ")
    if last_space <= 0:
        return cut.rstrip() + "…"
    return cut[:last_space].rstrip() + "…"


def pick_locale(field: dict[str, str] | None, locale: str) -> tuple[str, str]:
    """Return (value, locale_used). Falls back to en, then any non-empty entry."""
    if not field:
        return "", locale
    val = field.get(locale)
    if val:
        return val, locale
    val = field.get(DEFAULT_LOCALE)
    if val:
        return val, DEFAULT_LOCALE
    for loc, v in field.items():
        if v:
            return v, loc
    return "", locale


def entry_key(item: dict[str, Any]) -> str | None:
    """Routable key for the hover lookup. None if the item is a stub
    without a path or URI (sister-project placeholders in vocabulary.json)."""
    if item.get("source") == "aidops":
        return item.get("path") or None
    return item.get("uri") or None


def build_entry(
    item: dict[str, Any],
    kind: str,
    locale: str,
) -> dict[str, Any]:
    label, _ = pick_locale(item.get("label"), locale)
    definition, locale_used = pick_locale(item.get("definition"), locale)
    limit = LOCALE_EXCERPT_LIMIT.get(locale, 220)
    entry: dict[str, Any] = {
        "label": label or item.get("id", ""),
        "kind": kind,
        "source": item.get("source") or "aidops",
        "maturity": item.get("maturity", "draft"),
        "href": entry_key(item) or "",
        "definition_excerpt": truncate_excerpt(definition, limit),
        "locale_used": locale_used,
    }
    if kind == "property":
        entry["type"] = item.get("type") or ""
        entry["vocabulary"] = item.get("vocabulary")
    return entry


def build_bundle(vocab: dict[str, Any], locale: str) -> dict[str, dict[str, Any]]:
    bundle: dict[str, dict[str, Any]] = {}
    sections: list[tuple[str, str]] = [
        ("concepts", "concept"),
        ("properties", "property"),
        ("vocabularies", "vocabulary"),
    ]
    for section, kind in sections:
        for item in vocab.get(section, {}).values():
            key = entry_key(item)
            if not key:
                continue
            bundle[key] = build_entry(item, kind, locale)
    return bundle


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"),
                        help="Path to dist directory (default: dist)")
    args = parser.parse_args(argv)

    vocab_path = args.dist / "vocabulary.json"
    if not vocab_path.exists():
        print(f"error: {vocab_path} not found; run `publicschema build` first",
              file=sys.stderr)
        return 1

    with vocab_path.open() as f:
        vocab = json.load(f)

    preview_dir = args.dist / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)

    for locale in LOCALES:
        bundle = build_bundle(vocab, locale)
        out_path = preview_dir / f"{locale}.json"
        out_path.write_text(json.dumps(bundle, ensure_ascii=False, sort_keys=True))
        print(f"wrote {out_path} ({len(bundle)} entries)")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
