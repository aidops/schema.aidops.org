"""Tests for the AidOps build pipeline.

Covers: output structure, AidOps-only filtering, URI generation,
JSON Schema with inherited properties, JSON-LD context.
"""

import json

import jsonschema

from build.build import build_vocabulary
from tests.conftest import make_concept, make_property, make_vocabulary


# ---------------------------------------------------------------------------
# Round-trip: YAML in -> JSON out -> assert structure
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_vocabulary_json_structure(
        self, tmp_aidops, write_concept, write_property, write_vocabulary
    ):
        write_vocabulary("severity.yaml", make_vocabulary(id="severity"))
        write_property("sev.yaml", make_property(id="sev", vocabulary="severity"))
        write_concept("test.yaml", make_concept(
            id="Test", properties=["sev"],
        ))

        result = build_vocabulary(tmp_aidops)

        assert "meta" in result
        assert "concepts" in result
        assert "properties" in result
        assert "vocabularies" in result

        assert "Test" in result["concepts"]
        assert "sev" in result["properties"]
        assert "severity" in result["vocabularies"]

    def test_ps_concepts_present_with_source_tag(
        self, tmp_aidops, write_concept, write_property
    ):
        """Vendored PS concepts (Profile) appear in output tagged source=publicschema."""
        write_property("score.yaml", make_property(id="score", type="decimal"))
        write_concept("assess.yaml", make_concept(
            id="Assess", supertypes=["Profile"], properties=["score"],
        ))

        result = build_vocabulary(tmp_aidops)
        assert result["concepts"]["Assess"]["source"] == "aidops"
        assert "Profile" in result["concepts"]
        assert result["concepts"]["Profile"]["source"] == "publicschema"

    def test_ps_properties_present_with_source_tag(
        self, tmp_aidops, write_concept, write_property
    ):
        """Vendored PS properties (subject, observation_date) appear in output
        with source=publicschema so the site can render inherited rows with
        real type/vocabulary/definition instead of 'unknown'."""
        write_property("score.yaml", make_property(id="score", type="decimal"))
        write_concept("assess.yaml", make_concept(
            id="Assess", supertypes=["Profile"], properties=["score"],
        ))

        result = build_vocabulary(tmp_aidops)
        assert result["properties"]["score"]["source"] == "aidops"
        assert "subject" in result["properties"]
        assert result["properties"]["subject"]["source"] == "publicschema"
        assert result["properties"]["subject"]["type"] is not None
        assert result["properties"]["subject"]["type"] != ""

    def test_ps_items_use_publicschema_uri(
        self, tmp_aidops, write_concept, write_property
    ):
        """PS entries carry canonical publicschema.org URIs so site links route
        externally, not to a nonexistent AidOps path."""
        write_concept("assess.yaml", make_concept(id="Assess", supertypes=["Profile"]))
        result = build_vocabulary(tmp_aidops)
        profile = result["concepts"]["Profile"]
        assert profile["uri"].startswith("https://publicschema.org/")
        subject = result["properties"]["subject"]
        assert subject["uri"].startswith("https://publicschema.org/")


# ---------------------------------------------------------------------------
# URI generation
# ---------------------------------------------------------------------------

class TestURIGeneration:
    def test_concept_uses_aidops_uri(self, tmp_aidops, write_concept):
        write_concept("test.yaml", make_concept(id="Test"))
        result = build_vocabulary(tmp_aidops)
        assert result["concepts"]["Test"]["uri"] == "https://schema.aidops.org/Test"

    def test_property_uses_aidops_uri(
        self, tmp_aidops, write_concept, write_property
    ):
        write_property("score.yaml", make_property(id="score"))
        write_concept("test.yaml", make_concept(id="Test", properties=["score"]))
        result = build_vocabulary(tmp_aidops)
        assert result["properties"]["score"]["uri"] == "https://schema.aidops.org/score"

    def test_vocabulary_uses_aidops_uri(
        self, tmp_aidops, write_vocabulary
    ):
        write_vocabulary("severity.yaml", make_vocabulary(id="severity"))
        result = build_vocabulary(tmp_aidops)
        assert result["vocabularies"]["severity"]["uri"] == "https://schema.aidops.org/vocab/severity"


# ---------------------------------------------------------------------------
# JSON Schema with inherited properties
# ---------------------------------------------------------------------------

class TestJsonSchemaInheritance:
    def test_json_schema_includes_inherited_properties(
        self, tmp_aidops, write_concept, write_property
    ):
        """JSON Schema for an AidOps concept includes inherited PS properties."""
        write_property("score.yaml", make_property(id="score", type="decimal"))
        write_concept("assess.yaml", make_concept(
            id="Assess", supertypes=["Profile"], properties=["score"],
        ))

        result = build_vocabulary(tmp_aidops)
        schema = result["concept_schemas"]["Assess"]

        # Valid JSON Schema
        jsonschema.Draft202012Validator.check_schema(schema)

        # Includes own property
        assert "score" in schema["properties"]

        # Includes inherited PS properties
        assert "subject" in schema["properties"]
        assert "observation_date" in schema["properties"]


# ---------------------------------------------------------------------------
# JSON-LD context
# ---------------------------------------------------------------------------

class TestJsonLdContext:
    def test_context_uses_aidops_vocab(
        self, tmp_aidops, write_concept
    ):
        write_concept("test.yaml", make_concept(id="Test"))
        result = build_vocabulary(tmp_aidops)
        ctx = result["context"]["@context"]
        assert ctx["@vocab"] == "https://schema.aidops.org/"

    def test_context_has_ps_meta_prefix(
        self, tmp_aidops, write_concept
    ):
        """Context includes the ps: meta-namespace prefix."""
        write_concept("test.yaml", make_concept(id="Test"))
        result = build_vocabulary(tmp_aidops)
        ctx = result["context"]["@context"]
        assert ctx["ps"] == "https://publicschema.org/meta/"

    def test_context_concept_has_aidops_uri(
        self, tmp_aidops, write_concept
    ):
        write_concept("test.yaml", make_concept(id="Test"))
        result = build_vocabulary(tmp_aidops)
        ctx = result["context"]["@context"]
        assert ctx["Test"] == "https://schema.aidops.org/Test"
