# SPDX-License-Identifier: Apache-2.0
"""End-to-end smoke test: publicschema-build can compile AidOps.

Validates phase-5 of the SchemaProject refactor: AidOps's schema/project.yaml
is loadable by publicschema-build's compiler with the vendored PublicSchema
dep resolved via the local-path mechanism.
"""

import subprocess
import sys
from pathlib import Path

import pytest  # noqa: I001
from build.schema_project import load_schema_project

AIDOPS_ROOT = Path(__file__).parent.parent

_VENDOR_PROJECT_YAML = AIDOPS_ROOT / "vendor" / "publicschema" / "schema" / "project.yaml"
_VENDOR_EXISTS = _VENDOR_PROJECT_YAML.exists()


@pytest.mark.skipif(
    not _VENDOR_EXISTS,
    reason="vendor not fetched; run `just fetch-publicschema` first",
)
def test_aidops_project_yaml_loads():
    graph = load_schema_project(AIDOPS_ROOT)
    assert graph.manifest.id == "aidops"
    assert graph.manifest.kind == "extension"
    assert "publicschema" in graph.resolved_dependencies
    ps = graph.resolved_dependencies["publicschema"]
    assert ps.manifest.id == "publicschema"
    assert ps.manifest.kind == "core"
    # Sanity check: vocabulary directory exists and has at least one entry.
    assert len(graph.vocabularies) > 0


@pytest.mark.skipif(
    not _VENDOR_EXISTS,
    reason="vendor not fetched; run `just fetch-publicschema` first",
)
def test_aidops_build_produces_vocabulary_json(tmp_path):
    """Run `publicschema build` as a subprocess and assert dist/vocabulary.json is created."""
    out_dir = tmp_path / "dist"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build.cli",
            "build",
            "--profile-dir",
            str(AIDOPS_ROOT),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"publicschema build failed (exit {result.returncode}):\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert (out_dir / "vocabulary.json").exists(), (
        f"vocabulary.json not produced in {out_dir}; "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
