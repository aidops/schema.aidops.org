"""Tests for preview.json generation (hover-card data source)."""

import pytest

from build.build import build_vocabulary
from build.preview_export import (
    build_preview,
    truncate_excerpt,
    LOCALE_EXCERPT_LIMIT,
)
from tests.conftest import SCHEMA_DIR, VENDOR_DIR, make_concept, make_property, make_vocabulary


@pytest.fixture(autouse=True)
def _require_vendor():
    if not VENDOR_DIR.exists():
        pytest.skip("Vendored PublicSchema not found; run `just fetch-publicschema`")


class TestTruncateExcerpt:
    def test_short_text_untruncated(self):
        text = "A short definition."
        assert truncate_excerpt(text, limit=220) == text

    def test_long_text_cut_at_word_boundary(self):
        text = "word " * 200  # 1000 chars, always on word boundary
        result = truncate_excerpt(text, limit=50)
        assert len(result) <= 50 + 1  # + 1 for trailing ellipsis character
        assert not result.rstrip("…").endswith(" ")
        # Does not cut mid-word: last run before ellipsis is a full "word"
        stripped = result.rstrip("…").strip()
        assert all(tok == "word" for tok in stripped.split())

    def test_cut_point_respects_word(self):
        text = "alpha beta gammalongword delta"
        result = truncate_excerpt(text, limit=15)
        # must not cut "gammalongword" partway through
        assert "gammalon" not in result.rstrip("…")

    def test_ends_with_ellipsis_when_truncated(self):
        text = "A" * 500
        result = truncate_excerpt(text, limit=100)
        assert result.endswith("…")

    def test_empty_text(self):
        assert truncate_excerpt("", limit=220) == ""


class TestBuildPreviewSynthetic:
    def test_aidops_concept_keyed_by_path(
        self, tmp_aidops, write_concept, write_property
    ):
        write_property("score.yaml", make_property(id="score", type="decimal"))
        write_concept("test.yaml", make_concept(id="Test", properties=["score"]))
        result = build_vocabulary(tmp_aidops)

        preview = build_preview(result)

        # AidOps concept keyed by local path
        test_path = result["concepts"]["Test"]["path"]
        assert test_path in preview
        entry = preview[test_path]
        assert "en" in entry and "fr" in entry and "es" in entry
        assert entry["en"]["kind"] == "concept"
        assert entry["en"]["source"] == "aidops"
        assert entry["en"]["href"] == test_path

    def test_aidops_property_has_type_and_vocabulary(
        self, tmp_aidops, write_concept, write_property, write_vocabulary
    ):
        write_vocabulary("severity.yaml", make_vocabulary(id="severity"))
        write_property("sev.yaml", make_property(id="sev", type="string", vocabulary="severity"))
        write_concept("test.yaml", make_concept(id="Test", properties=["sev"]))
        result = build_vocabulary(tmp_aidops)

        preview = build_preview(result)

        sev_path = result["properties"]["sev"]["path"]
        entry = preview[sev_path]["en"]
        assert entry["kind"] == "property"
        assert entry["type"] == "string"
        assert entry["vocabulary"] == "severity"

    def test_ps_concept_keyed_by_uri(self, tmp_aidops, write_concept):
        write_concept("test.yaml", make_concept(id="Test", supertypes=["Profile"]))
        result = build_vocabulary(tmp_aidops)

        preview = build_preview(result)

        profile_uri = result["concepts"]["Profile"]["uri"]
        assert profile_uri.startswith("https://publicschema.org/")
        assert profile_uri in preview
        assert preview[profile_uri]["en"]["source"] == "publicschema"
        assert preview[profile_uri]["en"]["href"] == profile_uri

    def test_locale_fallback_marked(
        self, tmp_aidops, write_concept, write_property
    ):
        """Property with only English definition renders fr/es entries flagged as fallback."""
        en_only = make_property(id="en_only", type="string")
        en_only["definition"] = {"en": "English only definition."}
        en_only["label"] = {"en": "English only"}
        write_property("en_only.yaml", en_only)
        write_concept("test.yaml", make_concept(id="Test", properties=["en_only"]))
        result = build_vocabulary(tmp_aidops)

        preview = build_preview(result)

        path = result["properties"]["en_only"]["path"]
        entry = preview[path]
        assert entry["en"]["locale_used"] == "en"
        assert entry["fr"]["locale_used"] == "en"
        assert entry["es"]["locale_used"] == "en"
        assert entry["fr"]["definition_excerpt"] == "English only definition."

    def test_excerpt_respects_locale_limits(
        self, tmp_aidops, write_concept, write_property
    ):
        """Definition excerpt fits per-locale char cap with word-boundary safety."""
        long_text_en = "word " * 100  # 500 chars
        long_text_fr = "mot " * 100  # 400 chars
        long_text_es = "palabra " * 100  # 800 chars
        prop = make_property(id="wordy", type="string")
        prop["definition"] = {"en": long_text_en, "fr": long_text_fr, "es": long_text_es}
        write_property("wordy.yaml", prop)
        write_concept("test.yaml", make_concept(id="Test", properties=["wordy"]))
        result = build_vocabulary(tmp_aidops)

        preview = build_preview(result)
        path = result["properties"]["wordy"]["path"]
        entry = preview[path]

        assert len(entry["en"]["definition_excerpt"]) <= LOCALE_EXCERPT_LIMIT["en"] + 1
        assert len(entry["fr"]["definition_excerpt"]) <= LOCALE_EXCERPT_LIMIT["fr"] + 1
        assert len(entry["es"]["definition_excerpt"]) <= LOCALE_EXCERPT_LIMIT["es"] + 1

    def test_vocabulary_included(self, tmp_aidops, write_vocabulary):
        write_vocabulary("severity.yaml", make_vocabulary(id="severity"))
        result = build_vocabulary(tmp_aidops)

        preview = build_preview(result)
        sev_path = result["vocabularies"]["severity"]["path"]
        assert sev_path in preview
        assert preview[sev_path]["en"]["kind"] == "vocabulary"


class TestBuildPreviewRealSchema:
    def test_anthropometric_profile_present(self):
        result = build_vocabulary(SCHEMA_DIR)
        preview = build_preview(result)
        path = result["concepts"]["AnthropometricProfile"]["path"]
        assert path in preview
        assert preview[path]["en"]["label"]
        assert preview[path]["en"]["source"] == "aidops"

    def test_ps_person_keyed_by_external_uri(self):
        result = build_vocabulary(SCHEMA_DIR)
        preview = build_preview(result)
        person_uri = result["concepts"]["Person"]["uri"]
        assert person_uri == "https://publicschema.org/Person"
        assert person_uri in preview
        assert preview[person_uri]["en"]["source"] == "publicschema"

    def test_preview_covers_all_referenced_items(self):
        """Every concept/property/vocabulary in vocabulary.json appears in preview."""
        result = build_vocabulary(SCHEMA_DIR)
        preview = build_preview(result)

        for c in result["concepts"].values():
            key = c["path"] if c.get("source") == "aidops" else c["uri"]
            assert key in preview, f"Concept {c['id']} missing from preview"
        for p in result["properties"].values():
            key = p["path"] if p.get("source") == "aidops" else p["uri"]
            assert key in preview, f"Property {p['id']} missing from preview"
