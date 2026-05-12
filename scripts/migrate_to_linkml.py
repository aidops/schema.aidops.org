#!/usr/bin/env python3
"""Migrate AidOps bespoke YAML to a LinkML composite.

One-shot script. Run before the cutover; preserved afterwards purely as
documentation of how the cutover was performed.

Reads ``schema/`` (concepts/, properties/, vocabularies/, bibliography/,
categories.yaml, project.yaml) and writes a LinkML composite under
``dist/linkml/`` (gitignored).

Strategy: each bespoke entity becomes a LinkML class/slot/enum carrying
the full original document inside a ``publicschema_logical_document``
annotation, so ``publicschema-build``'s reader projects it back
verbatim. The native LinkML attributes (title, description, is_a, slots,
range, multivalued, permissible_values) are populated alongside so
``linkml-lint`` and the LinkML generators (gen-owl, gen-shacl,
gen-jsonld-context, gen-json-schema) succeed on the composite.

Cross-schema references (supertypes from PublicSchema, vocabulary
references to PS enums) ride as CURIEs (``publicschema:Group``) and are
resolved through a LinkML ``imports:`` of the vendored PS composite.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "schema"
PROJECT_FILE = SOURCE_DIR / "project.yaml"
CONCEPTS_DIR = SOURCE_DIR / "concepts"
PROPERTIES_DIR = SOURCE_DIR / "properties"
VOCABULARIES_DIR = SOURCE_DIR / "vocabularies"
BIBLIOGRAPHY_DIR = SOURCE_DIR / "bibliography"
CATEGORIES_FILE = SOURCE_DIR / "categories.yaml"
DEFAULT_OUTPUT_DIR = ROOT / "dist" / "linkml"
VENDOR_PS_LINKML = ROOT / "vendor" / "publicschema" / "schema" / "publicschema.yaml"

# LinkML primitives this migration may encounter on bespoke `type:`.
PRIMITIVE_TYPE_MAP = {
    "string": "string",
    "text": "string",
    "integer": "integer",
    "int": "integer",
    "number": "float",
    "float": "float",
    "boolean": "boolean",
    "bool": "boolean",
    "date": "date",
    "datetime": "datetime",
    "uri": "uri",
    "url": "uri",
    "geojson_geometry": "string",  # LinkML has no native geo type
}

# PublicSchema types AidOps refers to by bare name. The migrator rewrites
# these to publicschema: CURIEs so the LinkML imports: chain resolves them.
PS_TYPES: set[str] = set()


@dataclass
class Context:
    project: dict[str, Any] = field(default_factory=dict)
    concepts: dict[str, dict] = field(default_factory=dict)  # id -> bespoke
    properties: dict[str, dict] = field(default_factory=dict)
    vocabularies: dict[str, dict] = field(default_factory=dict)
    bibliography: dict[str, dict] = field(default_factory=dict)
    categories: dict[str, dict] = field(default_factory=dict)
    # Reverse projection of `informs:` from bibliography entries.
    biblio_refs: dict[str, list[str]] = field(default_factory=dict)  # target_key -> [biblio_id]
    unmapped: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> Any:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def dump_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.safe_dump(
            data,
            f,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=10_000,
        )


def _normalize_refs(doc: dict) -> dict:
    """Coerce ``references`` to a list. Two AidOps property files use a
    bare scalar; the canonical shape is a list (matches PS)."""
    refs = doc.get("references")
    if isinstance(refs, str) and refs:
        doc["references"] = [refs]
    return doc


def load_inventory(ctx: Context) -> None:
    ctx.project = load_yaml(PROJECT_FILE).get("schema_project", {})
    for path in sorted(CONCEPTS_DIR.glob("*.yaml")):
        doc = load_yaml(path)
        ctx.concepts[doc["id"]] = doc
    for path in sorted(PROPERTIES_DIR.glob("*.yaml")):
        doc = _normalize_refs(load_yaml(path))
        ctx.properties[doc["id"]] = doc
    for path in sorted(VOCABULARIES_DIR.glob("*.yaml")):
        doc = load_yaml(path)
        ctx.vocabularies[doc["id"]] = doc
    for path in sorted(BIBLIOGRAPHY_DIR.glob("*.yaml")):
        doc = load_yaml(path)
        ctx.bibliography[doc["id"]] = doc
    if CATEGORIES_FILE.exists():
        ctx.categories = load_yaml(CATEGORIES_FILE)


# ---------------------------------------------------------------------------
# Reverse-projection helpers
# ---------------------------------------------------------------------------

INFORMS_KIND_TO_REGISTRY = {
    "concepts": "concept",
    "properties": "property",
    "vocabularies": "vocabulary",
}


def build_biblio_refs(ctx: Context) -> None:
    """Reverse `informs:` into per-target lists keyed by '<kind>:<id>'."""
    for bib_id, bib in ctx.bibliography.items():
        informs = bib.get("informs") or {}
        if not isinstance(informs, dict):
            continue
        for kind, ids in informs.items():
            registry = INFORMS_KIND_TO_REGISTRY.get(kind)
            if not registry or not isinstance(ids, list):
                continue
            for target in ids:
                key = f"{registry}:{target}"
                ctx.biblio_refs.setdefault(key, []).append(bib_id)


def biblio_refs_for(kind: str, name: str, ctx: Context) -> list[str]:
    return ctx.biblio_refs.get(f"{kind}:{name}", [])


# ---------------------------------------------------------------------------
# Annotation helpers
# ---------------------------------------------------------------------------

def localized(value: Any) -> dict[str, str] | None:
    """Normalize an i18n value to {lang: text} or None."""
    if value is None:
        return None
    if isinstance(value, str):
        return {"en": value.strip()} if value.strip() else None
    if isinstance(value, dict):
        out = {str(k): str(v).strip() for k, v in value.items() if isinstance(v, str) and v.strip()}
        return out or None
    return None


def annotations_for(doc: dict[str, Any], *, kind: str, name: str, ctx: Context) -> dict[str, Any]:
    """Build the LinkML annotations payload.

    LinkML's Annotation type only admits scalar values, so the bespoke
    document is JSON-stringified into ``publicschema_logical_document_json``.
    ``publicschema-build``'s reader recognises the ``_json`` suffix and
    parses the value back to a dict.
    """
    logical = dict(doc)
    refs = biblio_refs_for(kind, name, ctx)
    if refs:
        logical["bibliography_refs"] = list(refs)
    annotations: dict[str, Any] = {
        "publicschema_logical_document_json": json.dumps(logical, sort_keys=True),
    }
    if refs:
        # Also surface as a simple comma-separated string for tools that
        # don't decode the logical document.
        annotations["bibliography_refs"] = ",".join(refs)
    return annotations


# ---------------------------------------------------------------------------
# CURIE rewriting for cross-schema references
# ---------------------------------------------------------------------------

def to_ps_curie(name: str) -> str:
    """Return the name unchanged. LinkML resolves cross-schema references
    by bare name through the imports closure; CURIE-prefixing here breaks
    that resolution (LinkML treats ``publicschema:Profile`` as a literal
    class name and fails to find it)."""
    return name


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------

def slug_to_pascal(slug: str) -> str:
    return "".join(p.capitalize() for p in re.split(r"[-_]+", slug) if p)


def convert_concept(name: str, doc: dict, ctx: Context) -> dict:
    cls: dict[str, Any] = {}
    if title := localized(doc.get("label")):
        cls["title"] = title["en"] if set(title) == {"en"} else title
    if description := localized(doc.get("definition")):
        cls["description"] = description["en"] if set(description) == {"en"} else description
    supers = [s for s in (doc.get("supertypes") or []) if s]
    if supers:
        cls["is_a"] = to_ps_curie(supers[0])
        if len(supers) > 1:
            cls["mixins"] = [to_ps_curie(s) for s in supers[1:]]
    cls["class_uri"] = f"aidops:{name}"
    slots = [s for s in (doc.get("properties") or []) if s]
    if slots:
        cls["slots"] = list(slots)
    cls["annotations"] = annotations_for(doc, kind="concept", name=name, ctx=ctx)
    return cls


def convert_property(name: str, doc: dict, ctx: Context) -> dict:
    slot: dict[str, Any] = {}
    if title := localized(doc.get("label")):
        slot["title"] = title["en"] if set(title) == {"en"} else title
    if description := localized(doc.get("definition")):
        slot["description"] = description["en"] if set(description) == {"en"} else description
    slot["slot_uri"] = f"aidops:{name}"
    # Range: vocab > references[0] > primitive type.
    vocab_id = doc.get("vocabulary")
    refs = doc.get("references") or []
    raw_type = doc.get("type")
    if vocab_id:
        vocab_pascal = slug_to_pascal(vocab_id)
        if vocab_pascal in ctx.vocabularies or vocab_id in ctx.vocabularies:
            slot["range"] = vocab_pascal
        else:
            slot["range"] = to_ps_curie(vocab_pascal)
    elif isinstance(refs, list) and refs:
        slot["range"] = to_ps_curie(refs[0])
    elif raw_type:
        slot["range"] = PRIMITIVE_TYPE_MAP.get(raw_type, "string")
    else:
        slot["range"] = "string"
    cardinality = doc.get("cardinality")
    if cardinality == "multiple":
        slot["multivalued"] = True
    slot["annotations"] = annotations_for(doc, kind="property", name=name, ctx=ctx)
    return slot


def convert_vocabulary(name: str, doc: dict, ctx: Context) -> tuple[str, dict]:
    """Return (pascal-case enum id, enum definition)."""
    enum_id = slug_to_pascal(name)
    enum: dict[str, Any] = {}
    if title := localized(doc.get("label")):
        enum["title"] = title["en"] if set(title) == {"en"} else title
    if description := localized(doc.get("definition")):
        enum["description"] = description["en"] if set(description) == {"en"} else description
    enum["enum_uri"] = f"aidops:{enum_id}"
    pvs: dict[str, dict] = {}
    for value in doc.get("values") or []:
        if not isinstance(value, dict):
            continue
        code = str(value.get("code") or "").strip()
        if not code:
            continue
        pv: dict[str, Any] = {}
        if title := localized(value.get("label")):
            pv["title"] = title["en"] if set(title) == {"en"} else title
        if description := localized(value.get("definition")):
            pv["description"] = description["en"] if set(description) == {"en"} else description
        per_value_extras: dict[str, Any] = {}
        for k, v in value.items():
            if k in {"code", "label", "definition"}:
                continue
            if v is None:
                continue
            per_value_extras[k] = v
        if per_value_extras:
            pv["annotations"] = {
                "publicschema_pv_extras_json": json.dumps(per_value_extras, sort_keys=True),
            }
        pvs[code] = pv
    if pvs:
        enum["permissible_values"] = pvs
    enum["annotations"] = annotations_for(doc, kind="vocabulary", name=name, ctx=ctx)
    return enum_id, enum


def convert_bibliography(name: str, doc: dict, ctx: Context) -> dict:
    """Each bibliography entry becomes a class is_a Citation."""
    cls: dict[str, Any] = {"is_a": "Citation"}
    if doc.get("title"):
        cls["title"] = str(doc["title"])
    if doc.get("short_title"):
        cls["description"] = str(doc["short_title"])
    cls["class_uri"] = f"aidops:bibliography/{name}"
    cls["annotations"] = {
        "publicschema_logical_document_json": json.dumps(doc, sort_keys=True),
    }
    return cls


def convert_categories(ctx: Context) -> dict:
    """Categories become a single PropertyCategory enum."""
    if not ctx.categories:
        return {}
    pvs: dict[str, dict] = {}
    for cat_id, cat in ctx.categories.items():
        pv: dict[str, Any] = {}
        if isinstance(cat, dict):
            if title := localized(cat.get("label")):
                pv["title"] = title["en"] if set(title) == {"en"} else title
            if description := localized(cat.get("definition") or cat.get("description")):
                pv["description"] = description["en"] if set(description) == {"en"} else description
        pvs[cat_id] = pv
    return {
        "title": "Property Category",
        "description": "UI taxonomy for property_groups[].category in AidOps profiles.",
        "enum_uri": "aidops:PropertyCategory",
        "permissible_values": pvs,
        "annotations": {
            "publicschema_logical_document_json": json.dumps(ctx.categories, sort_keys=True),
        },
    }


# ---------------------------------------------------------------------------
# Cross-schema reference discovery
# ---------------------------------------------------------------------------

def discover_ps_types(ctx: Context) -> None:
    """Identify supertype refs and vocab/concept refs that resolve to PS, not AidOps."""
    aidops_concepts = set(ctx.concepts)
    aidops_vocab_pascals = {slug_to_pascal(v) for v in ctx.vocabularies}
    aidops_properties = set(ctx.properties)
    referenced: set[str] = set()
    for doc in ctx.concepts.values():
        for s in (doc.get("supertypes") or []):
            referenced.add(s)
        for s in (doc.get("subtypes") or []):
            referenced.add(s)
        for p in (doc.get("properties") or []):
            referenced.add(p)
    for doc in ctx.properties.values():
        if v := doc.get("vocabulary"):
            referenced.add(slug_to_pascal(v))
        for r in (doc.get("references") or []):
            referenced.add(r)
    # Anything referenced but not owned by AidOps must come from PublicSchema.
    for ref in referenced:
        if ref in aidops_concepts:
            continue
        if ref in aidops_vocab_pascals:
            continue
        if ref in aidops_properties:
            continue
        if ref in PRIMITIVE_TYPE_MAP:
            continue
        PS_TYPES.add(ref)


# ---------------------------------------------------------------------------
# Composite emission
# ---------------------------------------------------------------------------

def prefixes(ctx: Context) -> dict[str, str]:
    base = ctx.project.get("base_uri", "https://schema.aidops.org/").rstrip("/") + "/"
    ps_dep = next(
        (d for d in (ctx.project.get("dependencies") or []) if d.get("id") == "publicschema"),
        {},
    )
    ps_base = (ps_dep.get("base_uri") or "https://publicschema.org/").rstrip("/") + "/"
    return {
        "aidops": base,
        "publicschema": ps_base,
        "linkml": "https://w3id.org/linkml/",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "schema": "http://schema.org/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    }


PS_IMPORT_PATH = "../../vendor/publicschema/schema/publicschema"


def schema_header(name: str, ctx: Context, *, imports: list[str]) -> dict[str, Any]:
    base = ctx.project.get("base_uri", "https://schema.aidops.org/").rstrip("/") + "/"
    # Replace the symbolic ``publicschema`` placeholder with the relative
    # path to the vendored PS LinkML composite. Path is relative to this
    # schema's location (``schema/linkml/`` post-cutover, ``dist/linkml/``
    # before).
    resolved_imports = [PS_IMPORT_PATH if imp == "publicschema" else imp for imp in imports]
    return {
        "id": f"{base}linkml/{name}",
        "name": name,
        "title": f"AidOps · {name}",
        "description": (
            "Generated by scripts/migrate_to_linkml.py. Source of truth post-cutover."
        ),
        "license": ctx.project.get("license", "Apache-2.0"),
        "version": ctx.project.get("version", "0.1.0"),
        "prefixes": prefixes(ctx),
        "default_prefix": "aidops",
        "default_range": "string",
        "imports": resolved_imports,
    }


def emit_concepts(ctx: Context, out_dir: Path) -> None:
    classes: dict[str, dict] = {}
    for name, doc in ctx.concepts.items():
        classes[name] = convert_concept(name, doc, ctx)
    body = schema_header("concepts", ctx, imports=["linkml:types", "publicschema"])
    body["classes"] = classes
    dump_yaml(out_dir / "concepts.yaml", body)


def emit_properties(ctx: Context, out_dir: Path) -> None:
    slots: dict[str, dict] = {}
    for name, doc in ctx.properties.items():
        slots[name] = convert_property(name, doc, ctx)
    body = schema_header("properties", ctx, imports=["linkml:types", "publicschema"])
    body["slots"] = slots
    dump_yaml(out_dir / "properties.yaml", body)


def emit_vocabularies(ctx: Context, out_dir: Path) -> None:
    enums: dict[str, dict] = {}
    for name, doc in ctx.vocabularies.items():
        enum_id, enum = convert_vocabulary(name, doc, ctx)
        enums[enum_id] = enum
    body = schema_header("vocabularies", ctx, imports=["linkml:types"])
    body["enums"] = enums
    dump_yaml(out_dir / "vocabularies.yaml", body)


def emit_bibliography(ctx: Context, out_dir: Path) -> None:
    classes: dict[str, dict] = {
        "Citation": {
            "abstract": True,
            "description": "Bibliographic record carried as a class is_a Citation.",
            "class_uri": "aidops:Citation",
        }
    }
    for name, doc in ctx.bibliography.items():
        classes[name] = convert_bibliography(name, doc, ctx)
    body = schema_header("bibliography", ctx, imports=["linkml:types"])
    body["classes"] = classes
    dump_yaml(out_dir / "bibliography.yaml", body)


def emit_categories(ctx: Context, out_dir: Path) -> None:
    enum = convert_categories(ctx)
    if not enum:
        return
    body = schema_header("categories", ctx, imports=["linkml:types"])
    body["enums"] = {"PropertyCategory": enum}
    dump_yaml(out_dir / "categories.yaml", body)


def emit_composite(ctx: Context, out_dir: Path) -> None:
    body = schema_header(
        "aidops",
        ctx,
        imports=[
            "linkml:types",
            "publicschema",
            "concepts",
            "properties",
            "vocabularies",
            "bibliography",
            "categories",
        ],
    )
    body["description"] = (
        "AidOps schema composite. Imports PublicSchema (vendored) and the "
        "per-kind AidOps LinkML modules emitted from the bespoke source by "
        "scripts/migrate_to_linkml.py."
    )
    dump_yaml(out_dir / "aidops.yaml", body)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(ctx: Context, out_dir: Path) -> None:
    lines: list[str] = [
        "# AidOps LinkML migration report",
        "",
        f"- concepts: {len(ctx.concepts)}",
        f"- properties: {len(ctx.properties)}",
        f"- vocabularies: {len(ctx.vocabularies)}",
        f"- bibliography: {len(ctx.bibliography)}",
        f"- categories: {len(ctx.categories)}",
        f"- cross-schema (PS) refs: {len(PS_TYPES)} -> {sorted(PS_TYPES)}",
        "",
    ]
    if ctx.unmapped:
        lines.append("## Unmapped fields")
        lines.extend(f"- {item}" for item in ctx.unmapped)
    (out_dir / "_migration_report.md").write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args(argv)
    out_dir: Path = args.out

    ctx = Context()
    load_inventory(ctx)
    build_biblio_refs(ctx)
    discover_ps_types(ctx)

    if out_dir.exists():
        for child in out_dir.iterdir():
            if child.is_file():
                child.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    emit_concepts(ctx, out_dir)
    emit_properties(ctx, out_dir)
    emit_vocabularies(ctx, out_dir)
    emit_bibliography(ctx, out_dir)
    emit_categories(ctx, out_dir)
    emit_composite(ctx, out_dir)
    write_report(ctx, out_dir)

    print(
        f"Migrated {len(ctx.concepts)} concepts, {len(ctx.properties)} properties, "
        f"{len(ctx.vocabularies)} vocabularies, {len(ctx.bibliography)} bibliography, "
        f"{len(ctx.categories)} categories -> {out_dir}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
