"""Shared YAML loading helpers for the AidOps build pipeline.

Extends the base loader pattern with load_merged_schema(), which loads
both the AidOps-owned schema/ and the vendored PublicSchema schema/,
tagging every item with its source so downstream code can filter on it.
"""

from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    """Load a single YAML file, returning an empty dict for empty/missing content."""
    return yaml.safe_load(path.read_text()) or {}


def load_all_yaml(directory: Path) -> dict[str, dict]:
    """Load all YAML files from a directory, keyed by relative path from directory.

    Using the relative path (e.g. 'sp/status.yaml') instead of just the
    filename avoids silent overwrites when two files share the same name
    in different subdirectories.
    """
    result = {}
    if not directory.exists():
        return result
    for p in sorted(directory.rglob("*.yaml")):
        result[str(p.relative_to(directory))] = load_yaml(p)
    return result


def load_vocabularies_with_paths(directory: Path) -> list[tuple[Path, dict]]:
    """Load vocabulary YAMLs with their relative paths for domain validation."""
    result = []
    if not directory.exists():
        return result
    for p in sorted(directory.rglob("*.yaml")):
        rel = p.relative_to(directory)
        result.append((rel, load_yaml(p)))
    return result


def load_merged_schema(
    aidops_schema_dir: Path,
    vendor_schema_dir: Path,
) -> dict:
    """Load and merge AidOps and PublicSchema YAML into a single data structure.

    Every concept, property, vocabulary, and bibliography entry is tagged
    with source="aidops" (owned) or source="publicschema" (vendored).
    The merged structure separates the two sources so callers can process
    the full type graph while filtering output to AidOps-owned items only.

    Returns a dict with keys:
        aidops_schema_dir:    the AidOps schema directory Path
        vendor_schema_dir:    the PS vendor schema directory Path
        concepts:             dict[id, {data, source}]
        properties:           dict[id, {data, source}]
        vocabularies:         dict[key, {data, source}]  (key is canonical ref)
        bibliography:         dict[id, {data, source}]
        aidops_meta:          _meta.yaml from schema/
        ps_meta:              _meta.yaml from vendor/publicschema/schema/
    """
    aidops_meta = load_yaml(aidops_schema_dir / "_meta.yaml")
    ps_meta = {}
    if vendor_schema_dir.exists():
        ps_meta_path = vendor_schema_dir / "_meta.yaml"
        if ps_meta_path.exists():
            ps_meta = load_yaml(ps_meta_path)

    concepts: dict[str, dict] = {}
    properties: dict[str, dict] = {}
    vocabularies: dict[str, dict] = {}
    bibliography: dict[str, dict] = {}

    def _load_by_id(directory: Path, source: str, target: dict) -> None:
        """Load YAML files keyed by their 'id' field, tagging each with source."""
        if not directory.exists():
            return
        for p in sorted(directory.rglob("*.yaml")):
            data = load_yaml(p)
            item_id = data.get("id")
            if not item_id:
                continue
            if item_id in target:
                # AidOps wins if already loaded; PS should not overwrite AidOps items
                existing_source = target[item_id]["source"]
                if existing_source == "aidops":
                    continue
            target[item_id] = {"data": data, "source": source}

    def _load_vocabularies_by_key(directory: Path, source: str) -> None:
        """Load vocabulary YAMLs keyed by canonical form, tagging each with source."""
        if not directory.exists():
            return
        for p in sorted(directory.rglob("*.yaml")):
            data = load_yaml(p)
            if "id" not in data:
                continue
            domain = data.get("domain")
            vocab_id = data["id"]
            key = f"{domain}/{vocab_id}" if domain else vocab_id
            if key in vocabularies:
                existing_source = vocabularies[key]["source"]
                if existing_source == "aidops":
                    continue
            vocabularies[key] = {"data": data, "source": source}

    # Load AidOps items first (they take precedence)
    _load_by_id(aidops_schema_dir / "concepts", "aidops", concepts)
    _load_by_id(aidops_schema_dir / "properties", "aidops", properties)
    _load_vocabularies_by_key(aidops_schema_dir / "vocabularies", "aidops")
    _load_by_id(aidops_schema_dir / "bibliography", "aidops", bibliography)

    # Load vendored PS items (filled in for type-graph resolution)
    _load_by_id(vendor_schema_dir / "concepts", "publicschema", concepts)
    _load_by_id(vendor_schema_dir / "properties", "publicschema", properties)
    _load_vocabularies_by_key(vendor_schema_dir / "vocabularies", "publicschema")
    _load_by_id(vendor_schema_dir / "bibliography", "publicschema", bibliography)

    return {
        "aidops_schema_dir": aidops_schema_dir,
        "vendor_schema_dir": vendor_schema_dir,
        "aidops_meta": aidops_meta,
        "ps_meta": ps_meta,
        "concepts": concepts,
        "properties": properties,
        "vocabularies": vocabularies,
        "bibliography": bibliography,
    }
