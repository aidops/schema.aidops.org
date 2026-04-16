"""Tests for RDF export (Turtle, SHACL).

Validates namespaces, owl:imports, and correct content in RDF output.
"""

import pytest
import rdflib
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from build.build import build_vocabulary
from build.rdf_export import build_turtle, build_shacl
from tests.conftest import SCHEMA_DIR, VENDOR_DIR, make_concept, make_property, make_vocabulary

AIDOPS = rdflib.Namespace("https://schema.aidops.org/")
PS_PROFILE = rdflib.URIRef("https://publicschema.org/Profile")


@pytest.fixture(autouse=True)
def _require_vendor():
    if not VENDOR_DIR.exists():
        pytest.skip("Vendored PublicSchema not found; run `just fetch-publicschema`")


# ---------------------------------------------------------------------------
# Unit tests (synthetic schema)
# ---------------------------------------------------------------------------

class TestBuildTurtle:
    def test_turtle_is_valid_rdf(
        self, tmp_aidops, write_concept, write_property,
    ):
        write_concept("test.yaml", make_concept(id="Test", properties=["score"]))
        write_property("score.yaml", make_property(id="score", type="decimal"))
        result = build_vocabulary(tmp_aidops)

        ttl = build_turtle(result)
        g = rdflib.Graph()
        g.parse(data=ttl, format="turtle")
        assert len(g) > 0

    def test_turtle_uses_aidops_namespace(
        self, tmp_aidops, write_concept, write_property,
    ):
        write_concept("test.yaml", make_concept(id="Test", properties=["score"]))
        write_property("score.yaml", make_property(id="score", type="decimal"))
        result = build_vocabulary(tmp_aidops)

        ttl = build_turtle(result)
        g = rdflib.Graph()
        g.parse(data=ttl, format="turtle")

        test_uri = rdflib.URIRef("https://schema.aidops.org/Test")
        assert (test_uri, RDF.type, RDFS.Class) in g


# ---------------------------------------------------------------------------
# Integration tests (real schema)
# ---------------------------------------------------------------------------

class TestRealRdfExport:
    def test_real_turtle_contains_all_concepts(self):
        result = build_vocabulary(SCHEMA_DIR)
        ttl = build_turtle(result)
        g = rdflib.Graph()
        g.parse(data=ttl, format="turtle")

        for cid in ["FoodSecurityProfile", "AnthropometricProfile",
                     "DwellingDamageProfile"]:
            uri = AIDOPS[cid]
            assert (uri, RDF.type, RDFS.Class) in g, f"Missing class triple for {cid}"

    def test_turtle_has_owl_imports(self):
        """Turtle output has owl:imports for PublicSchema."""
        result = build_vocabulary(SCHEMA_DIR)
        ttl = build_turtle(result)
        g = rdflib.Graph()
        g.parse(data=ttl, format="turtle")

        ps_ttl = rdflib.URIRef("https://publicschema.org/publicschema.ttl")
        imports = list(g.objects(predicate=OWL.imports))
        assert ps_ttl in imports, f"Missing owl:imports; found: {imports}"

    def test_profile_subtypes_link_to_publicschema(self):
        """Profile subtypes use rdfs:subClassOf pointing to publicschema.org."""
        result = build_vocabulary(SCHEMA_DIR)
        ttl = build_turtle(result)
        g = rdflib.Graph()
        g.parse(data=ttl, format="turtle")

        for cid in ["FoodSecurityProfile", "AnthropometricProfile",
                     "DwellingDamageProfile"]:
            uri = AIDOPS[cid]
            supers = list(g.objects(uri, RDFS.subClassOf))
            assert PS_PROFILE in supers, (
                f"{cid} should be subClassOf publicschema.org/Profile, "
                f"found: {supers}"
            )

    def test_shacl_shapes_generated(self):
        result = build_vocabulary(SCHEMA_DIR)
        shacl = build_shacl(result)
        g = rdflib.Graph()
        g.parse(data=shacl, format="turtle")
        assert len(g) > 0
