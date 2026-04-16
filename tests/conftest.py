"""Shared test fixtures for AidOps build pipeline tests."""

from pathlib import Path

import pytest
import yaml

AIDOPS_ROOT = Path(__file__).parent.parent
SCHEMA_DIR = AIDOPS_ROOT / "schema"
VENDOR_DIR = AIDOPS_ROOT / "vendor" / "publicschema" / "schema"
BUILD_SCHEMAS_DIR = AIDOPS_ROOT / "build" / "schemas"


@pytest.fixture
def tmp_aidops(tmp_path):
    """Create a minimal AidOps schema layout with a mock vendored PS."""
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    (schema_dir / "concepts").mkdir()
    (schema_dir / "properties").mkdir()
    (schema_dir / "vocabularies").mkdir()
    (schema_dir / "bibliography").mkdir()

    meta = {
        "name": "AidOps",
        "base_uri": "https://schema.aidops.org/",
        "version": "0.1.0",
        "maturity": "draft",
        "languages": ["en", "fr", "es"],
        "license": "Apache-2.0",
        "dependencies": {
            "publicschema": {
                "base_uri": "https://publicschema.org/",
                "version": "0.2.0",
            }
        },
    }
    (schema_dir / "_meta.yaml").write_text(yaml.dump(meta, allow_unicode=True))

    # Create a minimal vendored PS with Profile supertype
    vendor_dir = tmp_path / "vendor" / "publicschema" / "schema"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "concepts").mkdir()
    (vendor_dir / "properties").mkdir()
    (vendor_dir / "vocabularies").mkdir()

    ps_meta = {
        "name": "PublicSchema",
        "base_uri": "https://publicschema.org/",
        "version": "0.2.0",
        "maturity": "draft",
        "languages": ["en", "fr", "es"],
        "license": "CC-BY-4.0",
    }
    (vendor_dir / "_meta.yaml").write_text(yaml.dump(ps_meta, allow_unicode=True))

    # Write a Profile concept into vendored PS
    profile_data = {
        "id": "Profile",
        "maturity": "draft",
        "abstract": True,
        "definition": {
            "en": "A point-in-time record.",
            "fr": "Un enregistrement ponctuel.",
            "es": "Un registro puntual.",
        },
        "properties": ["subject", "observation_date"],
        "subtypes": [],
    }
    (vendor_dir / "concepts" / "profile.yaml").write_text(
        yaml.dump(profile_data, allow_unicode=True)
    )

    # Write PS properties: subject, observation_date
    for prop_id, ptype in [("subject", "string"), ("observation_date", "date")]:
        prop_data = {
            "id": prop_id,
            "maturity": "draft",
            "label": {"en": prop_id.replace("_", " ").capitalize(),
                       "fr": f"Libellé {prop_id}", "es": f"Etiqueta {prop_id}"},
            "definition": {"en": f"A test property {prop_id}.",
                            "fr": f"Un test {prop_id}.", "es": f"Un test {prop_id}."},
            "type": ptype,
            "cardinality": "single",
        }
        (vendor_dir / "properties" / f"{prop_id}.yaml").write_text(
            yaml.dump(prop_data, allow_unicode=True)
        )

    return schema_dir


@pytest.fixture
def write_concept(tmp_aidops):
    """Write a concept YAML file into the AidOps schema."""
    def _write(filename, data):
        path = tmp_aidops / "concepts" / filename
        path.write_text(yaml.dump(data, allow_unicode=True))
        return path
    return _write


@pytest.fixture
def write_property(tmp_aidops):
    """Write a property YAML file into the AidOps schema."""
    def _write(filename, data):
        path = tmp_aidops / "properties" / filename
        path.write_text(yaml.dump(data, allow_unicode=True))
        return path
    return _write


@pytest.fixture
def write_vocabulary(tmp_aidops):
    """Write a vocabulary YAML file into the AidOps schema."""
    def _write(filename, data):
        path = tmp_aidops / "vocabularies" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(data, allow_unicode=True))
        return path
    return _write


@pytest.fixture
def write_ps_concept(tmp_aidops):
    """Write a concept YAML into the vendored PublicSchema."""
    vendor_dir = tmp_aidops.parent / "vendor" / "publicschema" / "schema"
    def _write(filename, data):
        path = vendor_dir / "concepts" / filename
        path.write_text(yaml.dump(data, allow_unicode=True))
        return path
    return _write


@pytest.fixture
def write_ps_property(tmp_aidops):
    """Write a property YAML into the vendored PublicSchema."""
    vendor_dir = tmp_aidops.parent / "vendor" / "publicschema" / "schema"
    def _write(filename, data):
        path = vendor_dir / "properties" / filename
        path.write_text(yaml.dump(data, allow_unicode=True))
        return path
    return _write


@pytest.fixture
def write_ps_vocabulary(tmp_aidops):
    """Write a vocabulary YAML into the vendored PublicSchema."""
    vendor_dir = tmp_aidops.parent / "vendor" / "publicschema" / "schema"
    def _write(filename, data):
        path = vendor_dir / "vocabularies" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(data, allow_unicode=True))
        return path
    return _write


def make_concept(id="TestProfile", **overrides):
    """Create a minimal valid concept dict."""
    data = {
        "id": id,
        "maturity": "draft",
        "definition": {
            "en": f"A test {id}.",
            "fr": f"Un test {id}.",
            "es": f"Un test {id}.",
        },
        "properties": [],
    }
    data.update(overrides)
    return data


def make_property(id="test_field", type="string", **overrides):
    """Create a minimal valid property dict."""
    data = {
        "id": id,
        "maturity": "draft",
        "label": {
            "en": id.replace("_", " ").capitalize(),
            "fr": f"Libellé {id}",
            "es": f"Etiqueta {id}",
        },
        "definition": {
            "en": f"A test property {id}.",
            "fr": f"Un test {id}.",
            "es": f"Un test {id}.",
        },
        "type": type,
        "cardinality": "single",
    }
    data.update(overrides)
    return data


def make_vocabulary(id="test-vocab", **overrides):
    """Create a minimal valid vocabulary dict."""
    data = {
        "id": id,
        "maturity": "draft",
        "definition": {
            "en": "A test vocabulary.",
            "fr": "Un vocabulaire test.",
            "es": "Un vocabulario test.",
        },
        "values": [
            {
                "code": "value_a",
                "label": {"en": "Value A", "fr": "Valeur A", "es": "Valor A"},
                "definition": {"en": "First value.", "fr": "Premiere valeur.", "es": "Primer valor."},
            }
        ],
    }
    data.update(overrides)
    return data
