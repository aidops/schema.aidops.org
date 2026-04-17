"""Validates AidOps YAML source files.

Checks:
1. YAML files conform to JSON Schema format specs (AidOps files only)
2. Referential integrity (property refs, vocabulary refs, concept refs)
   - Resolves across both AidOps schema and vendored PublicSchema
3. Multilingual completeness (all configured languages present)
4. No orphaned properties (defined but unused by any concept in AidOps)
5. Supertype/subtype symmetry (skipped when supertype is vendored)
"""

import json
import sys
from pathlib import Path

import jsonschema

from build.loader import (
    load_all_yaml,
    load_merged_schema,
    load_vocabularies_with_paths,
    load_yaml,
)
from build.utils import collect_inherited_ids

SCHEMAS_DIR = Path(__file__).parent / "schemas"


class ValidationError:
    """A single validation issue with context."""

    def __init__(self, file: str, message: str, severity: str = "error"):
        self.file = file
        self.message = message
        self.severity = severity

    def __str__(self):
        return f"{self.file}: {self.message}"

    def __repr__(self):
        return f"ValidationError({self.file!r}, {self.message!r}, severity={self.severity!r})"


def _load_json_schema(name: str) -> dict:
    path = SCHEMAS_DIR / name
    return json.loads(path.read_text())


def _validate_against_schema(
    data: dict, schema: dict, filename: str
) -> list[ValidationError]:
    """Validate a data dict against a JSON Schema."""
    errors = []
    validator = jsonschema.Draft202012Validator(schema)
    for error in validator.iter_errors(data):
        path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else ""
        location = f" at {path}" if path else ""
        errors.append(ValidationError(filename, f"{error.message}{location}"))
    return errors


def _check_multilingual(
    data: dict,
    languages: list[str],
    filename: str,
    field_path: str,
    maturity: str = "normative",
) -> list[ValidationError]:
    """Check that a multilingual dict has all required languages.

    At draft maturity, only English is required; missing translations for
    other languages produce warnings. At candidate or normative maturity,
    all configured languages are required (errors).
    """
    issues = []
    if not isinstance(data, dict):
        return issues
    for lang in languages:
        if lang not in data:
            if maturity == "draft" and lang != "en":
                issues.append(ValidationError(
                    filename,
                    f"Missing '{lang}' translation in {field_path}",
                    severity="warning",
                ))
            else:
                issues.append(ValidationError(
                    filename,
                    f"Missing '{lang}' translation in {field_path}",
                ))
    return issues


def validate_schema_dir(schema_dir: Path) -> list[ValidationError]:
    """Validate AidOps YAML source files against the full merged type graph.

    Loads both AidOps schema/ and vendored PublicSchema schema/ for
    cross-schema reference resolution, but only validates AidOps-owned
    files (source="aidops").

    Returns a list of ValidationError objects. Empty list means valid.
    """
    errors = []

    # Load meta
    meta_path = schema_dir / "_meta.yaml"
    if not meta_path.exists():
        errors.append(ValidationError("_meta.yaml", "Missing _meta.yaml"))
        return errors

    meta = load_yaml(meta_path)
    meta_schema = _load_json_schema("meta.schema.json")

    # The AidOps _meta.yaml has an extra 'dependencies' block not in the base
    # PS meta schema. We validate against a relaxed copy that allows it.
    relaxed_meta_schema = json.loads(json.dumps(meta_schema))
    relaxed_meta_schema.pop("additionalProperties", None)
    errors.extend(_validate_against_schema(meta, relaxed_meta_schema, "_meta.yaml"))
    if errors:
        return errors

    languages = meta.get("languages", ["en"])

    vendor_schema_dir = schema_dir.parent / "vendor" / "publicschema" / "schema"

    # Load merged schema for cross-schema resolution
    merged = load_merged_schema(schema_dir, vendor_schema_dir)

    # Build full lookup indexes (both AidOps and PS)
    all_concept_ids: set[str] = set(merged["concepts"].keys())
    all_property_ids: set[str] = set(merged["properties"].keys())

    # Vocabulary IDs from the merged schema
    all_vocabulary_ids: set[str] = set(merged["vocabularies"].keys())

    # AidOps-only indexes for orphan / structural checks
    aidops_concept_ids: set[str] = {
        cid for cid, tagged in merged["concepts"].items()
        if tagged["source"] == "aidops"
    }
    aidops_property_ids: set[str] = {
        pid for pid, tagged in merged["properties"].items()
        if tagged["source"] == "aidops"
    }

    # Load AidOps YAML files directly for JSON Schema validation
    # (we need the raw files keyed by filename, not by id)
    concepts_raw = load_all_yaml(schema_dir / "concepts")
    properties_raw = load_all_yaml(schema_dir / "properties")
    vocabularies_raw = load_all_yaml(schema_dir / "vocabularies")
    vocabularies_with_paths = load_vocabularies_with_paths(schema_dir / "vocabularies")
    bibliography_raw = load_all_yaml(schema_dir / "bibliography")

    # Load categories (optional)
    categories_path = schema_dir / "categories.yaml"
    categories = load_yaml(categories_path) if categories_path.exists() else {}
    if categories:
        categories_schema = _load_json_schema("categories.schema.json")
        errors.extend(_validate_against_schema(
            categories, categories_schema, "categories.yaml",
        ))
    category_ids = set(categories.keys())

    # Build AidOps vocabulary canonical ID set with domain-path validation
    aidops_vocabulary_ids: set[str] = set()
    for rel_path, data in vocabularies_with_paths:
        if "id" not in data:
            continue
        filename = rel_path.name
        vocab_id = data["id"]
        yaml_domain = data.get("domain")
        parts = rel_path.parts
        if len(parts) == 1:
            if yaml_domain:
                errors.append(ValidationError(
                    filename,
                    f"Root-level vocabulary has 'domain: {yaml_domain}' but lives at vocabularies/ root; "
                    f"move the file to vocabularies/{yaml_domain}/ or remove the domain field",
                ))
                continue
            aidops_vocabulary_ids.add(vocab_id)
        else:
            subdir = parts[0]
            if len(parts) > 2:
                errors.append(ValidationError(
                    filename,
                    f"Vocabulary nested more than one level deep ({rel_path}); use vocabularies/<domain>/<id>.yaml",
                ))
                continue
            if yaml_domain != subdir:
                errors.append(ValidationError(
                    filename,
                    f"Vocabulary in 'vocabularies/{subdir}/' must declare 'domain: {subdir}' "
                    f"(found {yaml_domain!r})",
                ))
                continue
            if "/" in vocab_id:
                errors.append(ValidationError(
                    filename,
                    f"Vocabulary 'id' must be bare (no slash); got '{vocab_id}'. "
                    f"The domain segment is derived from the 'domain' field.",
                ))
                continue
            aidops_vocabulary_ids.add(f"{subdir}/{vocab_id}")

    # Load JSON Schemas for structural validation
    concept_schema = _load_json_schema("concept.schema.json")
    property_schema = _load_json_schema("property.schema.json")
    vocabulary_schema = _load_json_schema("vocabulary.schema.json")
    bibliography_schema = _load_json_schema("bibliography.schema.json")

    # Validate AidOps concepts
    for filename, data in concepts_raw.items():
        errors.extend(_validate_against_schema(data, concept_schema, filename))
        if "definition" in data:
            errors.extend(_check_multilingual(
                data["definition"], languages, filename, "definition",
                maturity=data.get("maturity", "draft"),
            ))

    # Validate AidOps properties
    for filename, data in properties_raw.items():
        errors.extend(_validate_against_schema(data, property_schema, filename))
        if "definition" in data:
            errors.extend(_check_multilingual(
                data["definition"], languages, filename, "definition",
                maturity=data.get("maturity", "draft"),
            ))
        if "label" in data:
            errors.extend(_check_multilingual(
                data["label"], languages, filename, "label",
                maturity=data.get("maturity", "draft"),
            ))

    # Validate AidOps vocabularies
    for filename, data in vocabularies_raw.items():
        errors.extend(_validate_against_schema(data, vocabulary_schema, filename))
        if "definition" in data:
            errors.extend(_check_multilingual(
                data["definition"], languages, filename, "definition",
                maturity=data.get("maturity", "draft"),
            ))
        for i, value in enumerate(data.get("values", [])):
            if "label" in value:
                errors.extend(_check_multilingual(
                    value["label"], ["en"], filename,
                    f"values[{i}].label",
                ))
            if "definition" in value:
                errors.extend(_check_multilingual(
                    value["definition"], ["en"], filename,
                    f"values[{i}].definition",
                ))

    # Referential integrity: concept -> property references.
    # Properties may live in AidOps or PS; both are valid.
    used_property_ids: set[str] = set()
    for filename, data in concepts_raw.items():
        for prop_entry in data.get("properties", []):
            prop_id = prop_entry["id"] if isinstance(prop_entry, dict) else prop_entry
            used_property_ids.add(prop_id)
            if prop_id not in all_property_ids:
                errors.append(ValidationError(
                    filename,
                    f"Property '{prop_id}' referenced but not defined in properties/ "
                    f"(checked AidOps and vendored PublicSchema)",
                ))

    # Referential integrity: property -> vocabulary references.
    # Vocabularies may be AidOps-owned or vendored PS.
    for filename, data in properties_raw.items():
        vocab_ref = data.get("vocabulary")
        if vocab_ref and vocab_ref not in all_vocabulary_ids:
            errors.append(ValidationError(
                filename,
                f"Vocabulary '{vocab_ref}' referenced but not defined "
                f"(checked AidOps and vendored PublicSchema vocabularies/)",
            ))

    # Referential integrity: property -> concept references
    for filename, data in properties_raw.items():
        concept_ref = data.get("references")
        if concept_ref and concept_ref not in all_concept_ids:
            errors.append(ValidationError(
                filename,
                f"Concept '{concept_ref}' referenced but not defined "
                f"(checked AidOps and vendored PublicSchema concepts/)",
            ))

    # Orphaned properties: AidOps properties not used by any AidOps concept.
    # We check against ALL concept usage (including inherited from PS supertypes)
    # to avoid false positives from inherited properties.
    aidops_used: set[str] = set()
    for cid, tagged in merged["concepts"].items():
        for prop_entry in tagged["data"].get("properties", []):
            pid = prop_entry["id"] if isinstance(prop_entry, dict) else prop_entry
            aidops_used.add(pid)

    for filename, data in properties_raw.items():
        prop_id = data.get("id")
        if prop_id and prop_id not in aidops_used:
            errors.append(ValidationError(
                filename,
                f"Property '{prop_id}' is defined but not used by any concept (orphaned)",
            ))

    # Referential integrity: concept -> supertype/subtype references.
    # Supertypes may be vendored PS concepts.
    for filename, data in concepts_raw.items():
        for supertype in data.get("supertypes", []):
            if supertype not in all_concept_ids:
                errors.append(ValidationError(
                    filename,
                    f"Supertype '{supertype}' referenced but not defined "
                    f"(checked AidOps and vendored PublicSchema concepts/)",
                ))
        for subtype in data.get("subtypes", []):
            if subtype not in all_concept_ids:
                errors.append(ValidationError(
                    filename,
                    f"Subtype '{subtype}' referenced but not defined "
                    f"(checked AidOps and vendored PublicSchema concepts/)",
                ))

    # Supertype/subtype symmetry check.
    # Only enforce symmetry when BOTH sides are AidOps-owned.
    # Vendored PS supertypes won't list AidOps subtypes; that's expected.
    aidops_concept_by_id: dict[str, tuple[str, dict]] = {}
    for filename, data in concepts_raw.items():
        cid = data.get("id")
        if cid:
            aidops_concept_by_id[cid] = (filename, data)

    for cid, (filename, data) in aidops_concept_by_id.items():
        for supertype in data.get("supertypes", []):
            # Skip symmetry check when supertype is vendored
            if supertype not in aidops_concept_ids:
                continue
            if supertype in aidops_concept_by_id:
                parent_data = aidops_concept_by_id[supertype][1]
                if cid not in parent_data.get("subtypes", []):
                    errors.append(ValidationError(
                        filename,
                        f"'{cid}' lists '{supertype}' as supertype, but '{supertype}' does not list '{cid}' as subtype",
                    ))
        for subtype in data.get("subtypes", []):
            # Skip symmetry check when subtype is vendored
            if subtype not in aidops_concept_ids:
                continue
            if subtype in aidops_concept_by_id:
                child_data = aidops_concept_by_id[subtype][1]
                if cid not in child_data.get("supertypes", []):
                    errors.append(ValidationError(
                        filename,
                        f"'{cid}' lists '{subtype}' as subtype, but '{subtype}' does not list '{cid}' as supertype",
                    ))

    # Validate bibliography entries
    for filename, data in bibliography_raw.items():
        errors.extend(_validate_against_schema(data, bibliography_schema, filename))

    # Bibliography cross-reference integrity
    for filename, data in bibliography_raw.items():
        informs = data.get("informs") or {}
        for cid in informs.get("concepts", []):
            if cid not in all_concept_ids:
                errors.append(ValidationError(
                    filename,
                    f"Bibliography 'informs.concepts' references concept '{cid}' which is not defined",
                ))
        for vid in informs.get("vocabularies", []):
            if vid not in all_vocabulary_ids:
                errors.append(ValidationError(
                    filename,
                    f"Bibliography 'informs.vocabularies' references vocabulary '{vid}' which is not defined",
                ))
        for pid in informs.get("properties", []):
            if pid not in all_property_ids:
                errors.append(ValidationError(
                    filename,
                    f"Bibliography 'informs.properties' references property '{pid}' which is not defined",
                ))

    # Reverse bibliography coverage: warn for any AidOps property that no
    # bibliography entry cites via informs.properties. Properties in the
    # allowlist below are cross-cutting administrative fields with no single
    # canonical source; they are exempt from this check. The check is skipped
    # entirely when the schema has no bibliography entries (e.g. test fixtures).
    BIBLIOGRAPHY_EXEMPT_PROPERTIES: set[str] = {
        "linked_child_person_id",   # internal linkage field, no canonical instrument
        "location_of_assessment",   # GPS/admin field common to all post-shock instruments
        "recall_period_days",       # context field shared across FIES, LCS, HDDS, MDD-W
    }
    if bibliography_raw:
        cited_property_ids: set[str] = set()
        for _bib_fn, bib_data in bibliography_raw.items():
            for pid in (bib_data.get("informs") or {}).get("properties") or []:
                cited_property_ids.add(pid)
        for filename, data in properties_raw.items():
            pid = data.get("id")
            if pid and pid not in cited_property_ids and pid not in BIBLIOGRAPHY_EXEMPT_PROPERTIES:
                errors.append(ValidationError(
                    filename,
                    f"Property '{pid}' is not cited by any bibliography entry "
                    f"(add it to an informs.properties list, or to BIBLIOGRAPHY_EXEMPT_PROPERTIES)",
                    severity="warning",
                ))

    # age_applicability cross-check against WG/CFM bibliography citations
    WG_BAND_IMPLICATIONS = {
        "washington-group-ss": {"adult"},
        "washington-group-es": {"adult"},
    }
    CFM_CHILD_BANDS = {"child_2_4", "child_5_17"}
    property_bib_ids: dict[str, set[str]] = {pid: set() for pid in aidops_property_ids}
    for _bib_filename, bib_data in bibliography_raw.items():
        bib_id = bib_data.get("id")
        if not bib_id:
            continue
        for pid in (bib_data.get("informs") or {}).get("properties", []) or []:
            if pid in property_bib_ids:
                property_bib_ids[pid].add(bib_id)
    for filename, data in properties_raw.items():
        pid = data.get("id")
        if not pid:
            continue
        declared = set(data.get("age_applicability") or [])
        cites = property_bib_ids.get(pid, set())
        for bib_id, required in WG_BAND_IMPLICATIONS.items():
            if bib_id in cites and not required.issubset(declared):
                missing = sorted(required - declared)
                errors.append(ValidationError(
                    filename,
                    f"Property '{pid}' is cited in bibliography '{bib_id}' "
                    f"but age_applicability is missing required band(s): "
                    f"{', '.join(missing)}",
                ))
        if "washington-group-cfm" in cites and not (declared & CFM_CHILD_BANDS):
            errors.append(ValidationError(
                filename,
                f"Property '{pid}' is cited in bibliography "
                f"'washington-group-cfm' but age_applicability is missing "
                f"at least one child band (expected one of: child_2_4, child_5_17)",
            ))

    # Vocabulary value code uniqueness
    for filename, data in vocabularies_raw.items():
        codes = [v["code"] for v in data.get("values", []) if "code" in v]
        seen: set[str] = set()
        for code in codes:
            if code in seen:
                errors.append(ValidationError(
                    filename,
                    f"Duplicate value code '{code}' in vocabulary",
                ))
            seen.add(code)

    # property_groups validation: category references and completeness
    for filename, data in concepts_raw.items():
        groups = data.get("property_groups")
        if not groups:
            continue
        concept_id = data.get("id", filename)

        for group in groups:
            cat = group.get("category", "")
            if cat and category_ids and cat not in category_ids:
                errors.append(ValidationError(
                    filename,
                    f"property_groups references category '{cat}' "
                    f"which is not defined in categories.yaml",
                ))

        # Completeness: every own + inherited property must appear in groups.
        all_expected: set[str] = set()
        for prop_entry in data.get("properties", []):
            pid = prop_entry["id"] if isinstance(prop_entry, dict) else prop_entry
            all_expected.add(pid)
        # Walk supertype chain using the merged concept index
        visited_supers: set[str] = set()
        collect_inherited_ids(
            data, merged["concepts"], all_expected, visited_supers,
        )
        grouped_ids: set[str] = set()
        for group in groups:
            for pid in group.get("properties", []):
                grouped_ids.add(pid)

        missing = all_expected - grouped_ids
        if missing:
            missing_sorted = ", ".join(sorted(missing))
            errors.append(ValidationError(
                filename,
                f"property_groups on '{concept_id}' is missing properties: "
                f"{missing_sorted}. These would silently vanish from the "
                f"concept page.",
            ))

        for group in groups:
            for pid in group.get("properties", []):
                if pid not in all_property_ids:
                    errors.append(ValidationError(
                        filename,
                        f"property_groups references property '{pid}' "
                        f"which is not defined in properties/",
                    ))

    return errors


def main():
    """CLI entry point for validation."""
    schema_dir = Path("schema")
    if len(sys.argv) > 1:
        schema_dir = Path(sys.argv[1])

    issues = validate_schema_dir(schema_dir)
    warnings = [i for i in issues if i.severity == "warning"]
    errors = [i for i in issues if i.severity == "error"]

    if warnings:
        print(f"{len(warnings)} warning(s):", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)

    if errors:
        print(f"Validation failed with {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Validation passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
