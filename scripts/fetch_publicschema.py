# SPDX-License-Identifier: Apache-2.0
"""Fetch and vendor the PublicSchema schema directory.

Copies the local PublicSchema schema into vendor/publicschema/schema/.
If upstream ships schema/project.yaml, that manifest is used as-is.
Older PS releases that only ship _meta.yaml fall through to a synth
shim that converts _meta.yaml into the SchemaProject manifest shape.

Usage:
    uv run python scripts/fetch_publicschema.py [--local-path PATH]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

# Repo root is one directory above this script.
REPO_ROOT = Path(__file__).parent.parent.resolve()
VENDOR_DEST = REPO_ROOT / "vendor" / "publicschema" / "schema"

# Default local source: ../v2/schema (sibling to the AidOps repo).
DEFAULT_LOCAL_PATH = REPO_ROOT / ".." / "v2" / "schema"


def _load_project_yaml() -> dict:
    """Read schema/project.yaml to discover the publicschema dependency entry."""
    project_yaml = REPO_ROOT / "schema" / "project.yaml"
    data = yaml.safe_load(project_yaml.read_text(encoding="utf-8")) or {}
    return data


def _find_publicschema_dep(project: dict) -> dict:
    """Return the publicschema dependency entry from schema/project.yaml."""
    deps = project.get("schema_project", {}).get("dependencies") or []
    for dep in deps:
        if dep.get("id") == "publicschema":
            return dep
    raise ValueError("No publicschema dependency found in schema/project.yaml")


def _synthesize_project_yaml_from_linkml(composite: dict, dest: Path) -> None:
    """Write a project.yaml synthesized from a LinkML composite header.

    Post-LinkML-cutover PS no longer ships a bespoke ``_meta.yaml`` or
    ``project.yaml``; the composite ``publicschema.yaml`` is the only
    metadata-bearing file. Read its top-level fields and reverse them
    into the SchemaProject manifest shape ``publicschema-build`` expects.
    """
    name = str(composite.get("name") or "publicschema")
    title = str(composite.get("title") or name)
    version = str(composite.get("version") or "")
    license_ = str(composite.get("license") or "")
    default_prefix = str(composite.get("default_prefix") or name)
    prefixes = composite.get("prefixes") or {}
    base_uri = str(prefixes.get(default_prefix) or "")
    project_doc = {
        "schema_project": {
            "id": name,
            "kind": "core",
            "name": title,
            "namespace": default_prefix,
            "base_uri": base_uri,
            "version": version,
            "status": "release",
            "languages": {"primary": "en", "additional": ["fr", "es"]},
            "license": license_,
        }
    }
    dest.write_text(yaml.dump(project_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"  Synthesized project.yaml at {dest} (from LinkML composite)")


def _synthesize_project_yaml(meta: dict, dest: Path) -> None:
    """Write a project.yaml synthesized from a legacy _meta.yaml.

    _meta.yaml uses:
        name, base_uri, version, maturity, languages (list), license
    project.yaml expects:
        schema_project.{id, kind, name, namespace, base_uri, version, status,
                         languages.{primary, additional}, license}
    """
    # languages: _meta.yaml has a flat list; project.yaml uses {primary, additional}.
    raw_langs = meta.get("languages", [])
    if isinstance(raw_langs, list) and raw_langs:
        primary_lang = raw_langs[0]
        additional_langs = raw_langs[1:]
    else:
        primary_lang = str(raw_langs) if raw_langs else "en"
        additional_langs = []

    project_doc = {
        "schema_project": {
            "id": "publicschema",
            "kind": "core",
            "name": str(meta.get("name", "PublicSchema")),
            "namespace": "publicschema",
            "base_uri": str(meta.get("base_uri", "")),
            "version": str(meta.get("version", "")),
            "status": str(meta.get("maturity", "draft")),
            "languages": {
                "primary": primary_lang,
                "additional": additional_langs,
            },
            "license": str(meta.get("license", "")),
        }
    }

    dest.write_text(yaml.dump(project_doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"  Synthesized project.yaml at {dest}")


def _validate_via_load_schema_project(vendor_root: Path) -> None:
    """Call publicschema-build's load_schema_project to validate the synthesis."""
    from build.schema_project import load_schema_project

    graph = load_schema_project(vendor_root)
    print(
        f"  load_schema_project OK: id={graph.manifest.id!r}, "
        f"version={graph.manifest.version!r}, kind={graph.manifest.kind!r}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--local-path",
        default=str(DEFAULT_LOCAL_PATH),
        metavar="PATH",
        help=(
            "Path to PublicSchema schema/ directory "
            f"(default: {DEFAULT_LOCAL_PATH})"
        ),
    )
    args = parser.parse_args(argv)

    local_path = Path(args.local_path).resolve()
    if not local_path.exists():
        print(f"error: local_path does not exist: {local_path}", file=sys.stderr)
        return 1
    has_upstream_project_yaml = (local_path / "project.yaml").exists()
    has_meta_yaml = (local_path / "_meta.yaml").exists()
    has_linkml_composite = (local_path / "publicschema.yaml").exists()
    if not (has_upstream_project_yaml or has_meta_yaml or has_linkml_composite):
        print(
            f"error: none of project.yaml, _meta.yaml, or publicschema.yaml found at {local_path}; "
            "is this a PublicSchema schema/ directory?",
            file=sys.stderr,
        )
        return 1

    # Discover the expected version from schema/project.yaml.
    project = _load_project_yaml()
    dep = _find_publicschema_dep(project)
    expected_version = dep.get("version", "")

    # Wipe and re-copy.
    vendor_schema_parent = VENDOR_DEST.parent
    if vendor_schema_parent.exists():
        shutil.rmtree(vendor_schema_parent)
        print(f"Removed existing {vendor_schema_parent}")

    shutil.copytree(local_path, VENDOR_DEST)
    print(f"Copied {local_path} -> {VENDOR_DEST}")

    # Determine the actual version, preferring upstream project.yaml.
    vendored_project_yaml = VENDOR_DEST / "project.yaml"
    vendored_meta_yaml = VENDOR_DEST / "_meta.yaml"
    vendored_linkml_composite = VENDOR_DEST / "publicschema.yaml"
    if vendored_project_yaml.exists():
        vendored_project = (
            yaml.safe_load(vendored_project_yaml.read_text(encoding="utf-8")) or {}
        )
        actual_version = str(
            vendored_project.get("schema_project", {}).get("version", "")
        )
        print(f"  Using upstream project.yaml at {vendored_project_yaml}")
    elif vendored_meta_yaml.exists():
        # Synth fallback for legacy PS releases that only ship _meta.yaml.
        meta = yaml.safe_load(vendored_meta_yaml.read_text(encoding="utf-8")) or {}
        actual_version = str(meta.get("version", ""))
        _synthesize_project_yaml(meta, vendored_project_yaml)
    elif vendored_linkml_composite.exists():
        # Post-LinkML-cutover PS: synth from the composite header.
        composite = yaml.safe_load(vendored_linkml_composite.read_text(encoding="utf-8")) or {}
        actual_version = str(composite.get("version", ""))
        _synthesize_project_yaml_from_linkml(composite, vendored_project_yaml)
    else:
        raise SystemExit(
            f"vendored PS at {VENDOR_DEST} has no project.yaml, _meta.yaml, "
            "or publicschema.yaml composite — cannot synthesize manifest."
        )

    # Version check.
    if actual_version != expected_version:
        print(
            f"warning: vendor version {actual_version!r} does not match "
            f"pinned version {expected_version!r} in schema/project.yaml",
            file=sys.stderr,
        )

    # Validate via publicschema-build.
    # vendor/publicschema/schema/project.yaml → dep repo root = vendor/publicschema/
    vendor_root = VENDOR_DEST.parent
    _validate_via_load_schema_project(vendor_root)

    print("fetch-publicschema complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
