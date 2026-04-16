"""Tests for the AidOps validation pipeline.

Covers: cross-schema resolution, symmetry skip for vendored supertypes,
referential integrity across both schema dirs, multilingual checks.
"""

from build.validate import validate_schema_dir
from tests.conftest import make_concept, make_property, make_vocabulary


# ---------------------------------------------------------------------------
# Happy path: valid schemas with cross-schema references
# ---------------------------------------------------------------------------

class TestValidSchemas:
    def test_empty_schema_passes(self, tmp_aidops):
        """A schema dir with no concepts/properties/vocabularies is valid."""
        errors = validate_schema_dir(tmp_aidops)
        assert errors == []

    def test_concept_with_vendored_supertype_passes(
        self, tmp_aidops, write_concept, write_property
    ):
        """Concept referencing vendored PS supertype (Profile) passes validation."""
        write_property("fcs_score.yaml", make_property(id="fcs_score", type="decimal"))
        write_concept("food-security.yaml", make_concept(
            id="FoodSecurity",
            supertypes=["Profile"],
            properties=["fcs_score"],
        ))
        errors = validate_schema_dir(tmp_aidops)
        assert errors == []

    def test_property_with_vendored_vocabulary_passes(
        self, tmp_aidops, write_concept, write_property, write_ps_vocabulary
    ):
        """AidOps property referencing a vendored PS vocabulary passes."""
        write_ps_vocabulary("severity.yaml", make_vocabulary(id="severity"))
        write_property("sev.yaml", make_property(id="sev", vocabulary="severity"))
        write_concept("test.yaml", make_concept(id="Test", properties=["sev"]))
        errors = validate_schema_dir(tmp_aidops)
        assert errors == []


# ---------------------------------------------------------------------------
# Cross-schema supertype/subtype symmetry
# ---------------------------------------------------------------------------

class TestCrossSchemaSymmetry:
    def test_symmetry_skipped_for_vendored_supertype(
        self, tmp_aidops, write_concept, write_property
    ):
        """Vendored PS Profile does not list AidOps subtypes; no error."""
        write_property("score.yaml", make_property(id="score", type="decimal"))
        write_concept("assessment.yaml", make_concept(
            id="Assessment",
            supertypes=["Profile"],
            properties=["score"],
        ))
        errors = validate_schema_dir(tmp_aidops)
        # Profile's subtypes list is empty, but no symmetry error because
        # the supertype is vendored.
        symmetry_errors = [e for e in errors if "symmetry" in str(e) or "does not list" in str(e)]
        assert symmetry_errors == []

    def test_symmetry_enforced_for_aidops_only_concepts(
        self, tmp_aidops, write_concept, write_property
    ):
        """Symmetry is still enforced between two AidOps-owned concepts."""
        write_property("score.yaml", make_property(id="score", type="decimal"))
        write_concept("parent.yaml", make_concept(
            id="Parent", subtypes=[],
        ))
        write_concept("child.yaml", make_concept(
            id="Child", supertypes=["Parent"], properties=["score"],
        ))
        errors = validate_schema_dir(tmp_aidops)
        symmetry_errors = [e for e in errors if "does not list" in str(e)]
        assert len(symmetry_errors) == 1


# ---------------------------------------------------------------------------
# Referential integrity
# ---------------------------------------------------------------------------

class TestReferentialIntegrity:
    def test_concept_references_missing_property(
        self, tmp_aidops, write_concept
    ):
        write_concept("test.yaml", make_concept(
            id="Test", properties=["nonexistent_prop"],
        ))
        errors = validate_schema_dir(tmp_aidops)
        assert any("nonexistent_prop" in str(e) for e in errors)

    def test_property_references_missing_vocabulary(
        self, tmp_aidops, write_concept, write_property
    ):
        write_property("field.yaml", make_property(
            id="field", vocabulary="nonexistent-vocab",
        ))
        write_concept("test.yaml", make_concept(
            id="Test", properties=["field"],
        ))
        errors = validate_schema_dir(tmp_aidops)
        assert any("nonexistent-vocab" in str(e) for e in errors)

    def test_orphaned_property_reported(self, tmp_aidops, write_property):
        write_property("orphan.yaml", make_property(id="orphan"))
        errors = validate_schema_dir(tmp_aidops)
        assert any("orphan" in str(e) for e in errors)


# ---------------------------------------------------------------------------
# Multilingual completeness
# ---------------------------------------------------------------------------

class TestMultilingualCompleteness:
    def test_draft_missing_french_is_warning(self, tmp_aidops, write_concept):
        data = make_concept(maturity="draft")
        del data["definition"]["fr"]
        write_concept("warn.yaml", data)
        issues = validate_schema_dir(tmp_aidops)
        fr_issues = [e for e in issues if "fr" in str(e)]
        assert len(fr_issues) == 1
        assert fr_issues[0].severity == "warning"

    def test_candidate_missing_french_is_error(self, tmp_aidops, write_concept):
        data = make_concept(maturity="candidate")
        del data["definition"]["fr"]
        write_concept("bad.yaml", data)
        issues = validate_schema_dir(tmp_aidops)
        fr_errors = [e for e in issues if "fr" in str(e) and e.severity == "error"]
        assert len(fr_errors) == 1


# ---------------------------------------------------------------------------
# Property groups with cross-schema inherited properties
# ---------------------------------------------------------------------------

class TestPropertyGroups:
    def _write_categories(self, tmp_aidops, categories=None):
        import yaml
        if categories is None:
            categories = {
                "administrative": {"label": {"en": "Administrative"}},
                "scores": {"label": {"en": "Scores"}},
            }
        (tmp_aidops / "categories.yaml").write_text(
            yaml.dump(categories, allow_unicode=True)
        )

    def test_property_groups_with_inherited_ps_props_pass(
        self, tmp_aidops, write_concept, write_property
    ):
        """property_groups including inherited PS properties pass validation."""
        self._write_categories(tmp_aidops)
        write_property("score.yaml", make_property(id="score", type="decimal"))
        write_concept("assessment.yaml", make_concept(
            id="Assessment",
            supertypes=["Profile"],
            properties=["score"],
            property_groups=[
                {"category": "administrative", "properties": ["subject", "observation_date"]},
                {"category": "scores", "properties": ["score"]},
            ],
        ))
        errors = validate_schema_dir(tmp_aidops)
        prop_group_errors = [e for e in errors if "property_groups" in str(e)]
        assert prop_group_errors == []

    def test_missing_inherited_property_in_groups_is_error(
        self, tmp_aidops, write_concept, write_property
    ):
        """Inherited PS properties not in groups produce an error."""
        self._write_categories(tmp_aidops)
        write_property("score.yaml", make_property(id="score", type="decimal"))
        write_concept("assessment.yaml", make_concept(
            id="Assessment",
            supertypes=["Profile"],
            properties=["score"],
            property_groups=[
                # Missing subject and observation_date (inherited from Profile)
                {"category": "scores", "properties": ["score"]},
            ],
        ))
        errors = validate_schema_dir(tmp_aidops)
        missing_errors = [e for e in errors if "missing properties" in str(e)]
        assert len(missing_errors) == 1
        assert "subject" in str(missing_errors[0])
        assert "observation_date" in str(missing_errors[0])
