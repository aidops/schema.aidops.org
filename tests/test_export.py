"""Tests for CSV and Excel export generation."""

import csv
import io

import pytest

from build.build import build_vocabulary
from build.export import generate_concept_csv, generate_definition_xlsx, generate_template_xlsx
from tests.conftest import SCHEMA_DIR, VENDOR_DIR, make_concept, make_property


@pytest.fixture(autouse=True)
def _require_vendor():
    if not VENDOR_DIR.exists():
        pytest.skip("Vendored PublicSchema not found; run `just fetch-publicschema`")


# ---------------------------------------------------------------------------
# Unit tests (synthetic)
# ---------------------------------------------------------------------------

class TestCsvGeneration:
    def test_csv_files_created(
        self, tmp_aidops, write_concept, write_property, tmp_path
    ):
        write_property("score.yaml", make_property(id="score", type="decimal"))
        write_concept("test.yaml", make_concept(id="Test", properties=["score"]))
        result = build_vocabulary(tmp_aidops)

        output_dir = tmp_path / "out"
        output_dir.mkdir()
        generate_concept_csv("Test", result, output_dir)
        csv_path = output_dir / "Test.csv"
        assert csv_path.exists()
        reader = csv.reader(io.StringIO(csv_path.read_text()))
        header = next(reader)
        assert "property" in header
        assert "type" in header


# ---------------------------------------------------------------------------
# Integration tests (real schema)
# ---------------------------------------------------------------------------

class TestRealExports:
    def test_food_security_csv_generated(self, tmp_path):
        result = build_vocabulary(SCHEMA_DIR)
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        generate_concept_csv("FoodSecurityProfile", result, output_dir)
        csv_path = output_dir / "FoodSecurityProfile.csv"
        assert csv_path.exists()
        reader = csv.reader(io.StringIO(csv_path.read_text()))
        header = next(reader)
        assert "property" in header
        rows = list(reader)
        prop_ids = [r[header.index("property")] for r in rows]
        assert "fcs_staples_days" in prop_ids
        assert "subject" in prop_ids, "Inherited PS property 'subject' missing from CSV"
        assert "observation_date" in prop_ids, "Inherited PS property 'observation_date' missing from CSV"

    def test_food_security_definition_xlsx_generated(self, tmp_path):
        result = build_vocabulary(SCHEMA_DIR)
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        generate_definition_xlsx("FoodSecurityProfile", result, output_dir)
        xlsx_path = output_dir / "FoodSecurityProfile-definition.xlsx"
        assert xlsx_path.exists()
        assert xlsx_path.stat().st_size > 0

    def test_food_security_template_xlsx_generated(self, tmp_path):
        result = build_vocabulary(SCHEMA_DIR)
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        generate_template_xlsx("FoodSecurityProfile", result, output_dir)
        xlsx_path = output_dir / "FoodSecurityProfile-template.xlsx"
        assert xlsx_path.exists()
        assert xlsx_path.stat().st_size > 0

    def test_all_concepts_have_csv(self, tmp_path):
        result = build_vocabulary(SCHEMA_DIR)
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        for cid, concept in result["concepts"].items():
            if concept.get("source") != "aidops":
                continue
            generate_concept_csv(cid, result, output_dir)
            csv_path = output_dir / f"{cid}.csv"
            assert csv_path.exists(), f"Missing CSV for {cid}"
            assert csv_path.stat().st_size > 0, f"Empty CSV for {cid}"
