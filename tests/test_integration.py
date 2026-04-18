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

        aidops_concepts = {
            cid: c for cid, c in result["concepts"].items()
            if c.get("source") == "aidops"
        }
        aidops_properties = {
            pid: p for pid, p in result["properties"].items()
            if p.get("source") == "aidops"
        }
        aidops_vocabularies = {
            vid: v for vid, v in result["vocabularies"].items()
            if v.get("source") == "aidops"
        }

        # AidOps has exactly 30 concepts; update this count when adding/removing AidOps concepts
        # Batch 2 adds: HealthAccessProfile
        # Batch 3 adds: MentalHealthProfile
        # Batch 3 adds: ChildProtectionProfile
        # Phase 6 adds: GBVRiskProfile
        # Phase 6 Batch 2 adds: Community + LivelihoodProfile, AgricultureProfile,
        #   WarningResponseProfile, AccountabilityToAffectedPopulationsProfile,
        #   HealthFacilityProfile, CommunityNeedsProfile
        # Phase 7 adds: ProtectionProfile, MarketProfile,
        #   PastoralFoodSecurityProfile, ClimateAdaptationProfile
        # Phase 8 adds: IndividualGBVExperienceProfile
        assert len(aidops_concepts) == 30, (
            f"Expected 30 AidOps concepts, got {len(aidops_concepts)}: "
            f"{sorted(aidops_concepts.keys())}"
        )
        assert set(aidops_concepts.keys()) == {
            "AccountabilityToAffectedPopulationsProfile",
            "AgricultureProfile",
            "AnthropometricProfile",
            "ChildHealthProfile",
            "ChildProtectionProfile",
            "ClimateAdaptationProfile",
            "Community",
            "CommunityNeedsProfile",
            "DisplacementProfile",
            "DwellingDamageProfile",
            "EducationProfile",
            "EnergyAccessProfile",
            "FoodSecurityProfile",
            "GBVRiskProfile",
            "GenderEmpowermentProfile",
            "HealthAccessProfile",
            "HealthFacilityProfile",
            "IndividualGBVExperienceProfile",
            "LivelihoodProfile",
            "MarketProfile",
            "MaternalNewbornHealthProfile",
            "MentalHealthProfile",
            "NFIProfile",
            "NutritionPracticesProfile",
            "PastoralFoodSecurityProfile",
            "ProtectionProfile",
            "ReproductiveHealthProfile",
            "ShelterAdequacyProfile",
            "WASHAssessmentProfile",
            "WarningResponseProfile",
        }

        # Update this count when adding/removing AidOps-owned properties.
        # Batch 2 delta (Batch 1 baseline was 443):
        #   HealthAccessProfile: +30 properties
        #   NFIProfile:          +32 properties (managed by NFI author)
        # Batch 3 delta (Batch 2 baseline was 505):
        #   MentalHealthProfile:   +27 properties (21 items + 6 derived scores)
        #   ChildProtectionProfile:+44 properties (41 items + 3 derived scores)
        #   CP Batch +41 props, +6 vocabs (plus 1 extra vocab for fgm-continuation-belief → +7 in build count)
        # Phase 6 delta (Batch 3 baseline was 576):
        #   GBVRiskProfile: +15 properties (14 net-new + 1 new specific_need_adolescent_girl_at_risk)
        # Phase 6 Batch 2 delta (Phase 6 Batch 1 baseline was 591):
        #   Community: +1 property (community_type)
        #   LivelihoodProfile: +22
        #   AgricultureProfile: +26
        #   WarningResponseProfile: +18
        #   AccountabilityToAffectedPopulationsProfile: +40
        #   HealthFacilityProfile: +69
        #   CommunityNeedsProfile: +21
        # Phase 7 delta (Phase 6 Batch 2 baseline was 788):
        #   ProtectionProfile: +22
        #   MarketProfile: +27
        #   PastoralFoodSecurityProfile: +24
        #   ClimateAdaptationProfile: +29
        # Phase 8 delta (Phase 7 baseline was 890):
        #   IndividualGBVExperienceProfile: +66
        assert len(aidops_properties) == 956, (
            f"Expected 956 AidOps properties, got {len(aidops_properties)}"
        )

        # Update this count when adding/removing AidOps-owned vocabularies.
        # Batch 2 delta (Batch 1 baseline was 114):
        #   HealthAccessProfile: +11 vocabularies
        #   NFIProfile:          +3 vocabularies (managed by NFI author)
        # Batch 3 delta (Batch 2 baseline was 128):
        #   MentalHealthProfile:    +4 vocabularies
        #   ChildProtectionProfile: +7 vocabularies (6 specified + fgm-continuation-belief
        #                           added to satisfy the no-vocabulary:null-on-enumerated rule)
        # Post-Batch-3 PS-promotion: -1 (care-provider-type moved to PublicSchema)
        # Phase 6 delta (Batch 3 baseline was 138):
        #   GBVRiskProfile: +6 vocabularies (4 specified: site-path-lighting, route-safety-3,
        #                   safety-perception-3, gbv-service-type; + 2 added to satisfy the
        #                   no-vocabulary:null-on-enumerated rule: latrine-sex-segregation,
        #                   latrine-lock-status)
        # Phase 6 Batch 2 delta (Phase 6 Batch 1 baseline was 144):
        #   Community: +1 (community-type)
        #   LivelihoodProfile: +10
        #   AgricultureProfile: +9
        #   WarningResponseProfile: +5
        #   AccountabilityToAffectedPopulationsProfile: +13
        #   HealthFacilityProfile: +5
        #   CommunityNeedsProfile: +7
        # Phase 7 delta (Phase 6 Batch 2 baseline was 194):
        #   ProtectionProfile: +11
        #   MarketProfile: +9
        #   PastoralFoodSecurityProfile: +13
        #   ClimateAdaptationProfile: +8
        # PS-promotion pass: -4 (shelter-situation-type, maternity-care-provider,
        #                        occupancy-arrangement, document-status moved to PublicSchema)
        # Phase 8 delta (Phase 7 + PS-promotion baseline was 231):
        #   IndividualGBVExperienceProfile: +8 (ipv-freq-3, gbv-help-sources,
        #     gbv-helpseeking-barriers, gbv-partner-type, gbv-relationship-status,
        #     gbv-perpetrator-type, gbv-prev-partner-timing, gbv-severity-tier)
        assert len(aidops_vocabularies) == 239, (
            f"Expected 239 AidOps vocabularies, got {len(aidops_vocabularies)}"
        )

        # Every AidOps concept has a JSON Schema
        for concept_id in aidops_concepts:
            assert concept_id in result["concept_schemas"], (
                f"Missing JSON Schema for concept {concept_id}"
            )

        # JSON-LD context has entries for all AidOps concepts and properties
        ctx = result["context"]["@context"]
        for concept_id in aidops_concepts:
            assert concept_id in ctx, f"Missing context entry for concept {concept_id}"
        for prop_id in aidops_properties:
            assert prop_id in ctx, f"Missing context entry for property {prop_id}"

    def test_ps_concepts_present_with_source_tag(self):
        """Vendored PS concepts appear in output tagged source=publicschema so
        inherited-row rendering can access real type/label/definition."""
        result = build_vocabulary(SCHEMA_DIR)
        ps_concepts = {"Profile", "Event", "Person", "Household", "Group",
                        "Organization", "Location", "Instrument"}
        for cid in ps_concepts:
            assert cid in result["concepts"], f"PS concept {cid} missing from output"
            assert result["concepts"][cid]["source"] == "publicschema", (
                f"PS concept {cid} not tagged source=publicschema"
            )
            assert result["concepts"][cid]["uri"].startswith("https://publicschema.org/"), (
                f"PS concept {cid} has wrong URI: {result['concepts'][cid]['uri']}"
            )

    def test_aidops_uris(self):
        """All AidOps-sourced concepts use schema.aidops.org URIs."""
        result = build_vocabulary(SCHEMA_DIR)
        for cid, concept in result["concepts"].items():
            if concept.get("source") != "aidops":
                continue
            assert concept["uri"].startswith("https://schema.aidops.org/"), (
                f"{cid} has wrong URI: {concept['uri']}"
            )

    def test_supertype_links_to_publicschema(self):
        """Profile subtypes link to publicschema.org for their supertype."""
        result = build_vocabulary(SCHEMA_DIR)
        for cid in ["FoodSecurityProfile", "AnthropometricProfile", "ChildHealthProfile",
                    "DwellingDamageProfile", "EducationProfile", "EnergyAccessProfile",
                    "GenderEmpowermentProfile", "MaternalNewbornHealthProfile",
                    "NutritionPracticesProfile", "ReproductiveHealthProfile",
                    "WASHAssessmentProfile"]:
            concept = result["concepts"][cid]
            supertypes = concept.get("supertypes", [])
            assert "Profile" in supertypes, f"{cid} missing Profile supertype"


    # PS-promotion candidates from Phase 6 (GBVRiskProfile):
    # None of the six new GBVRiskProfile vocabs are candidates for PS promotion at this time.
    # All carry humanitarian-specific `standard:` metadata tied to AO-resident bibs
    # (iasc-gbv-guidelines-2015, gbvaor-risk-analysis-2021, irc-safety-audit-2013,
    # unfpa-gbv-minimum-standards-2019, oxfam-lighting-wash-gbv-2018). Per the PS-promotion
    # pass retrospective, moving vocabs to PS before their evidence bibs are in PS creates
    # informs_drift failures. Deferred pending PS bib additions for these sources.


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


class TestDistOutputs:
    """Verify that dist/ outputs are generated correctly."""

    def test_dist_files_exist(self):
        """The build produces all expected dist/ files."""
        result = build_vocabulary(SCHEMA_DIR)

        # Check key output sections
        assert result.get("context") is not None
        assert result.get("concept_schemas") is not None
        assert result.get("jsonld_docs") is not None

        # JSON-LD docs for all 11 concepts
        for cid in ["FoodSecurityProfile", "AnthropometricProfile",
                     "ChildHealthProfile", "DwellingDamageProfile",
                     "EducationProfile", "EnergyAccessProfile",
                     "GenderEmpowermentProfile", "MaternalNewbornHealthProfile",
                     "NutritionPracticesProfile", "ReproductiveHealthProfile",
                     "WASHAssessmentProfile"]:
            key = f"concepts/{cid}.jsonld"
            assert key in result["jsonld_docs"], f"Missing JSON-LD doc: {key}"
