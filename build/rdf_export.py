"""Generates RDF serialization outputs (Turtle, SHACL) from AidOps build results.

Separate from export.py, which handles tabular formats (CSV, XLSX).
This module handles linked data serializations that consumers can load
into RDF toolchains (Protege, SPARQL endpoints, pySHACL, etc.).

The aidops: namespace covers AidOps-owned types.
The ps: prefix is used for shared PublicSchema meta-predicates.
owl:imports points at the published PublicSchema ontology so reasoners
can resolve vendored PS supertypes without re-declaring them here.
"""

import json
from pathlib import Path

import rdflib
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

AIDOPS = rdflib.Namespace("https://schema.aidops.org/")
SCHEMA = rdflib.Namespace("https://schema.org/")
PS = rdflib.Namespace("https://publicschema.org/meta/")

# Canonical URI for the published PublicSchema ontology.
# Added via owl:imports so reasoners can resolve PS supertypes.
PS_ONTOLOGY_URI = rdflib.URIRef("https://publicschema.org/publicschema.ttl")


def _build_context_with_coercions(ctx_inline: dict) -> dict:
    """Return the inline context with @type:@id coercions for URI-valued predicates.

    Without these coercions, rdflib's JSON-LD parser treats URI strings in
    predicates like schema:domainIncludes and rdfs:subClassOf as plain
    literals instead of URIRefs.
    """
    ctx = dict(ctx_inline)
    ctx["schema:domainIncludes"] = {
        "@id": "https://schema.org/domainIncludes",
        "@type": "@id",
    }
    ctx["schema:rangeIncludes"] = {
        "@id": "https://schema.org/rangeIncludes",
        "@type": "@id",
    }
    ctx["rdfs:subClassOf"] = {
        "@id": "http://www.w3.org/2000/01/rdf-schema#subClassOf",
        "@type": "@id",
        "@container": "@set",
    }
    ctx["ps:subtypes"] = {
        "@id": "https://publicschema.org/meta/subtypes",
        "@type": "@id",
        "@container": "@set",
    }
    ctx["ps:references"] = {
        "@id": "https://publicschema.org/meta/references",
        "@type": "@id",
    }
    ctx["ps:vocabulary"] = {
        "@id": "https://publicschema.org/meta/vocabulary",
        "@type": "@id",
    }
    return ctx


def load_graph(result: dict) -> rdflib.Graph:
    """Load all JSON-LD documents from a build result into a single rdflib graph.

    Replaces the hosted @context URL in each document with the inline
    context (plus URI coercions) so parsing works without network access.

    Also adds an owl:imports triple pointing at the PS ontology so reasoners
    can resolve vendored PS supertypes.
    """
    ctx = _build_context_with_coercions(result["context"]["@context"])

    g = rdflib.Graph()
    g.bind("aidops", AIDOPS)
    g.bind("ps", PS)
    g.bind("schema", SCHEMA)
    g.bind("skos", SKOS)
    g.bind("xsd", XSD)

    for _path, doc in result["jsonld_docs"].items():
        copy = dict(doc)
        copy["@context"] = ctx
        g.parse(data=json.dumps(copy), format="json-ld")

    # Declare this as an OWL ontology and import PublicSchema so reasoners
    # can resolve inherited PS classes and properties.
    meta = result.get("meta", {})
    base_uri = meta.get("base_uri", "https://schema.aidops.org/")
    ontology_node = rdflib.URIRef(base_uri)
    g.add((ontology_node, RDF.type, OWL.Ontology))
    g.add((ontology_node, OWL.imports, PS_ONTOLOGY_URI))

    return g


def build_turtle(result: dict) -> str:
    """Build a Turtle serialization of the AidOps vocabulary."""
    g = load_graph(result)
    return g.serialize(format="turtle")


def write_turtle(result: dict, dist_dir: Path) -> Path:
    """Write the Turtle file to dist/aidops.ttl. Returns the output path."""
    ttl = build_turtle(result)
    out_path = dist_dir / "aidops.ttl"
    out_path.write_text(ttl)
    return out_path


def build_full_jsonld(result: dict) -> str:
    """Build a single JSON-LD document containing the full AidOps vocabulary."""
    g = load_graph(result)
    meta = result["meta"]
    base_uri = meta["base_uri"]
    version = meta["version"]
    maturity = meta.get("maturity", "draft")
    version_label = "draft" if maturity == "draft" else ".".join(version.split(".")[:2])
    context_url = f"{base_uri}ctx/{version_label}.jsonld"
    ctx = result["context"]["@context"]
    raw = g.serialize(format="json-ld", context=ctx)
    doc = json.loads(raw)
    doc["@context"] = context_url
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def write_full_jsonld(result: dict, dist_dir: Path) -> Path:
    """Write the full vocabulary JSON-LD to dist/aidops.jsonld. Returns the output path."""
    content = build_full_jsonld(result)
    out_path = dist_dir / "aidops.jsonld"
    out_path.write_text(content)
    return out_path


# ---------------------------------------------------------------------------
# SHACL shapes
# ---------------------------------------------------------------------------

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")

# Map YAML property types to XSD datatypes for sh:datatype.
SHACL_DATATYPE_MAP = {
    "string": XSD.string,
    "date": XSD.date,
    "datetime": XSD.dateTime,
    "integer": XSD.integer,
    "decimal": XSD.decimal,
    "boolean": XSD.boolean,
    "uri": XSD.anyURI,
}

# Vocabulary value count threshold: vocabularies with more values than this
# are excluded from sh:in constraints to keep SHACL files readable.
VOCAB_SIZE_THRESHOLD = 50


def _resolve_all_properties(concept_id: str, concepts: dict) -> list:
    """Collect property entries from a concept and all its supertypes."""
    visited = set()
    all_props = []
    seen_ids = set()

    def walk(cid):
        if cid in visited or cid not in concepts:
            return
        visited.add(cid)
        for st in concepts[cid].get("supertypes", []):
            walk(st)
        for entry in concepts[cid].get("properties", []):
            pid = entry["id"] if isinstance(entry, dict) else entry
            if pid not in seen_ids:
                seen_ids.add(pid)
                all_props.append({"id": pid})

    walk(concept_id)
    return all_props


def build_shacl(result: dict) -> str:
    """Build SHACL shapes from the AidOps build result.

    Generates one sh:NodeShape per AidOps concept, with sh:property entries
    for each of the concept's properties (including inherited from PS supertypes).
    Constraints are derived from property type, cardinality, and vocabulary.
    """
    g = rdflib.Graph()
    g.bind("sh", SH)
    g.bind("xsd", XSD)
    g.bind("aidops", AIDOPS)

    # Use the full merged concept/property/vocabulary views so that
    # inherited PS properties are included in shapes.
    concepts = result.get("_all_concepts", result["concepts"])
    properties = result.get("_all_properties", result["properties"])
    vocabularies = result.get("_all_vocabularies", result["vocabularies"])

    # Generate shapes only for AidOps-owned concepts
    for concept_id, concept in result["concepts"].items():
        concept_uri = rdflib.URIRef(concept["uri"])
        shape_uri = rdflib.URIRef(concept["uri"] + "Shape")

        g.add((shape_uri, RDF.type, SH.NodeShape))
        g.add((shape_uri, SH.targetClass, concept_uri))
        g.add((shape_uri, RDFS.label, rdflib.Literal(f"{concept_id} shape")))

        for prop_entry in _resolve_all_properties(concept_id, concepts):
            prop_id = prop_entry["id"]
            if prop_id not in properties:
                continue
            prop = properties[prop_id]
            prop_uri = rdflib.URIRef(prop["uri"])

            prop_shape = rdflib.BNode()
            g.add((shape_uri, SH.property, prop_shape))
            g.add((prop_shape, SH.path, prop_uri))
            g.add((prop_shape, SH.name, rdflib.Literal(prop_id)))

            prop_type = prop.get("type", "string")
            cardinality = prop.get("cardinality", "single")

            if cardinality == "single":
                g.add((prop_shape, SH.maxCount, rdflib.Literal(1)))

            if prop_type.startswith("concept:"):
                ref_id = prop_type.split(":", 1)[1]
                if ref_id in concepts:
                    g.add((prop_shape, SH["class"], rdflib.URIRef(concepts[ref_id]["uri"])))
                g.add((prop_shape, SH.nodeKind, SH.BlankNodeOrIRI))
            elif prop_type == "geojson_geometry":
                g.add((prop_shape, SH.datatype, RDF.JSON))
            elif prop_type == "uri":
                g.add((prop_shape, SH.nodeKind, SH.IRI))
            elif prop_type in SHACL_DATATYPE_MAP:
                g.add((prop_shape, SH.datatype, SHACL_DATATYPE_MAP[prop_type]))

            vocab_id = prop.get("vocabulary")
            if vocab_id and vocab_id in vocabularies:
                vocab = vocabularies[vocab_id]
                values = vocab.get("values", [])
                if 0 < len(values) <= VOCAB_SIZE_THRESHOLD:
                    collection = rdflib.BNode()
                    items = [rdflib.Literal(v["code"], datatype=XSD.string) for v in values]
                    rdflib.collection.Collection(g, collection, items)
                    g.add((prop_shape, SH["in"], collection))

    return g.serialize(format="turtle")


def write_shacl(result: dict, dist_dir: Path) -> Path:
    """Write the SHACL shapes file to dist/aidops.shacl.ttl. Returns the output path."""
    shacl_ttl = build_shacl(result)
    out_path = dist_dir / "aidops.shacl.ttl"
    out_path.write_text(shacl_ttl)
    return out_path
