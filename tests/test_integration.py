"""Integration tests that validate and build the real AidOps schema.

These tests catch issues in the actual YAML content files that unit tests
with synthetic data would miss. They require vendored PublicSchema:
run `just fetch-publicschema` before running tests.
"""

import json
from pathlib import Path

import jsonschema
import pytest

from build.build import build_vocabulary
from build.validate import validate_schema_dir
from tests.conftest import SCHEMA_DIR, VENDOR_DIR


@pytest.fixture(autouse=True)
def _require_vendor():
    """Skip integration tests if vendored PS is not present."""
    if not VENDOR_DIR.exists():
        pytest.skip("Vendored PublicSchema not found; run `just fetch-publicschema`")


class TestRealSchema:
    def test_real_schema_validates(self):
        """The real AidOps schema passes validation with zero errors."""
        issues = validate_schema_dir(SCHEMA_DIR)
        errors = [e for e in issues if e.severity == "error"]
        assert errors == [], (
            f"Validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    def test_real_schema_builds(self):
        """The real AidOps schema builds successfully."""
        result = build_vocabulary(SCHEMA_DIR)

        assert "meta" in result
        assert "concepts" in result
        assert "properties" in result
        assert "vocabularies" in result
        assert "context" in result
        assert "concept_schemas" in result

        # AidOps has exactly 4 concepts
        assert len(result["concepts"]) == 4, (
            f"Expected 4 concepts, got {len(result['concepts'])}: "
            f"{sorted(result['concepts'].keys())}"
        )
        assert set(result["concepts"].keys()) == {
            "FoodSecurityProfile",
            "AnthropometricProfile",
            "DwellingDamageProfile",
            "HazardEvent",
        }

        # 104 exclusive properties
        assert len(result["properties"]) == 104, (
            f"Expected 104 properties, got {len(result['properties'])}"
        )

        # 25 exclusive vocabularies
        assert len(result["vocabularies"]) == 25, (
            f"Expected 25 vocabularies, got {len(result['vocabularies'])}"
        )

        # Every concept has a JSON Schema
        for concept_id in result["concepts"]:
            assert concept_id in result["concept_schemas"], (
                f"Missing JSON Schema for concept {concept_id}"
            )

        # JSON-LD context has entries for all AidOps concepts and properties
        ctx = result["context"]["@context"]
        for concept_id in result["concepts"]:
            assert concept_id in ctx, f"Missing context entry for concept {concept_id}"
        for prop_id in result["properties"]:
            assert prop_id in ctx, f"Missing context entry for property {prop_id}"

    def test_no_ps_concepts_in_output(self):
        """Vendored PS concepts must not appear in AidOps build output."""
        result = build_vocabulary(SCHEMA_DIR)
        ps_concepts = {"Profile", "Event", "Person", "Household", "Group",
                        "Organization", "Location", "Instrument"}
        leaked = ps_concepts & set(result["concepts"].keys())
        assert not leaked, f"PS concepts leaked into output: {leaked}"

    def test_aidops_uris(self):
        """All AidOps concepts use schema.aidops.org URIs."""
        result = build_vocabulary(SCHEMA_DIR)
        for cid, concept in result["concepts"].items():
            assert concept["uri"].startswith("https://schema.aidops.org/"), (
                f"{cid} has wrong URI: {concept['uri']}"
            )

    def test_supertype_links_to_publicschema(self):
        """Profile subtypes link to publicschema.org for their supertype."""
        result = build_vocabulary(SCHEMA_DIR)
        for cid in ["FoodSecurityProfile", "AnthropometricProfile", "DwellingDamageProfile"]:
            concept = result["concepts"][cid]
            supertypes = concept.get("supertypes", [])
            assert "Profile" in supertypes, f"{cid} missing Profile supertype"


class TestCrossReferences:
    """Verify inherited properties and cross-schema resolution."""

    def test_food_security_inherited_properties(self):
        """FoodSecurityProfile's property_groups include inherited Profile properties."""
        result = build_vocabulary(SCHEMA_DIR)
        fsp = result["concepts"]["FoodSecurityProfile"]
        groups = fsp.get("property_groups", [])
        admin_group = next((g for g in groups if g["category"] == "administrative"), None)
        assert admin_group is not None, "Missing 'administrative' property group"
        assert "subject" in admin_group["properties"]
        assert "observation_date" in admin_group["properties"]

    def test_food_security_json_schema_has_inherited_props(self):
        """FoodSecurityProfile JSON Schema includes subject, observation_date."""
        result = build_vocabulary(SCHEMA_DIR)
        schema = result["concept_schemas"]["FoodSecurityProfile"]
        assert "subject" in schema["properties"]
        assert "observation_date" in schema["properties"]
        # Also has own properties
        assert "fcs_staples_days" in schema["properties"]
        assert "fcs_score" in schema["properties"]

    def test_anthropometric_json_schema_has_inherited_props(self):
        """AnthropometricProfile JSON Schema includes subject, observation_date."""
        result = build_vocabulary(SCHEMA_DIR)
        schema = result["concept_schemas"]["AnthropometricProfile"]
        assert "subject" in schema["properties"]
        assert "body_weight" in schema["properties"]

    def test_dwelling_damage_json_schema_has_all_props(self):
        """DwellingDamageProfile JSON Schema includes both own and inherited props."""
        result = build_vocabulary(SCHEMA_DIR)
        schema = result["concept_schemas"]["DwellingDamageProfile"]
        # Inherited from Profile
        assert "subject" in schema["properties"]
        # Own properties
        assert "damage_level" in schema["properties"]
        assert "habitability_status" in schema["properties"]

    def test_hazard_event_json_schema(self):
        """HazardEvent JSON Schema has its own properties."""
        result = build_vocabulary(SCHEMA_DIR)
        schema = result["concept_schemas"]["HazardEvent"]
        assert "hazard_type" in schema["properties"]
        assert "severity" in schema["properties"]


class TestDistOutputs:
    """Verify that dist/ outputs are generated correctly."""

    def test_dist_files_exist(self):
        """The build produces all expected dist/ files."""
        result = build_vocabulary(SCHEMA_DIR)

        # Check key output sections
        assert result.get("context") is not None
        assert result.get("concept_schemas") is not None
        assert result.get("jsonld_docs") is not None

        # JSON-LD docs for all 4 concepts
        for cid in ["FoodSecurityProfile", "AnthropometricProfile",
                     "DwellingDamageProfile", "HazardEvent"]:
            key = f"concepts/{cid}.jsonld"
            assert key in result["jsonld_docs"], f"Missing JSON-LD doc: {key}"
