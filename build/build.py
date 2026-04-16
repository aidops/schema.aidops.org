"""Builds AidOps outputs from YAML source files.

Loads both the AidOps schema/ and the vendored PublicSchema schema/ to
resolve the full type graph (inherited properties, supertype URIs, etc.),
then emits outputs for AidOps-owned items only.

Generates:
1. vocabulary.json: AidOps vocabulary as structured JSON
2. context.jsonld: JSON-LD context mapping IDs to URIs
3. schemas/*.schema.json: one JSON Schema per AidOps concept
4. jsonld/*.jsonld: per-concept, per-property, per-vocabulary JSON-LD documents
5. RDF exports: aidops.ttl, aidops.jsonld, aidops.shacl.ttl
6. CSV / XLSX downloads per concept
"""

import json
import re
import sys
from pathlib import Path

from build.loader import load_merged_schema, load_yaml
from build.utils import collect_inherited_ids

# Type mappings from YAML types to JSON Schema
TYPE_MAP = {
    "string": {"type": "string"},
    "date": {"type": "string", "format": "date"},
    "datetime": {"type": "string", "format": "date-time"},
    "integer": {"type": "integer"},
    "decimal": {"type": "number"},
    "boolean": {"type": "boolean"},
    "uri": {"type": "string", "format": "uri"},
    "geojson_geometry": {"$ref": "https://geojson.org/schema/Geometry.json"},
}

# Type mappings from YAML types to JSON-LD @type coercion values.
JSONLD_TYPE_COERCION = {
    "date": "xsd:date",
    "datetime": "xsd:dateTime",
    "integer": "xsd:integer",
    "decimal": "xsd:decimal",
    "boolean": "xsd:boolean",
    "uri": "@id",
    "geojson_geometry": "@json",
}

# Type mappings from YAML types to JSON-LD rangeIncludes values
RANGE_INCLUDES_MAP = {
    "string": "xsd:string",
    "date": "xsd:date",
    "datetime": "xsd:dateTime",
    "integer": "xsd:integer",
    "decimal": "xsd:decimal",
    "boolean": "xsd:boolean",
    "uri": "xsd:anyURI",
    "geojson_geometry": "https://purl.org/geojson/vocab#Geometry",
}

# Map external_equivalents match values to RDF predicates.
MATCH_PREDICATES = {
    "exact": "skos:exactMatch",
    "close": "skos:closeMatch",
    "broad": "skos:broadMatch",
    "narrow": "skos:narrowMatch",
    "related": "skos:relatedMatch",
}
MATCH_FALLBACK = "rdfs:seeAlso"

# PublicSchema base URI used when referencing vendored PS types
PS_BASE_URI = "https://publicschema.org/"


def _external_equivalents_triples(raw_data: dict) -> dict[str, list[str]]:
    """Extract RDF match triples from an entity's external_equivalents."""
    equivalents = raw_data.get("external_equivalents")
    if not equivalents:
        return {}
    entity_id = raw_data.get("id", "<unknown>")
    triples: dict[str, list[str]] = {}
    for system, entry in equivalents.items():
        uri = entry.get("uri")
        if not uri:
            print(
                f"WARNING: external_equivalents[{system}] on {entity_id} "
                f"is missing 'uri' field, skipping",
                file=sys.stderr,
            )
            continue
        match_type = entry.get("match")
        predicate = MATCH_PREDICATES.get(match_type, MATCH_FALLBACK)
        triples.setdefault(predicate, []).append(uri)
    return triples


def _to_snake_case(name: str) -> str:
    """Convert PascalCase to snake_case. e.g. PaymentEvent -> payment_event."""
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def _language_tagged(texts: dict) -> list[dict]:
    """Build a list of JSON-LD language-tagged value objects from a {lang: text} dict."""
    return [
        {"@value": text, "@language": lang}
        for lang, text in texts.items()
        if text
    ]


def _resolve_range_includes(
    prop_type: str, out_concepts: dict[str, dict],
) -> str:
    """Map a property type to a JSON-LD rangeIncludes value."""
    if prop_type.startswith("concept:"):
        ref_id = prop_type.split(":", 1)[1]
        if ref_id in out_concepts:
            return out_concepts[ref_id]["uri"]
        return ref_id
    return RANGE_INCLUDES_MAP.get(prop_type, "xsd:string")


def _concept_property_jsonld(
    prop_out: dict, prop_raw: dict, concept_uri: str,
    out_concepts: dict, out_vocabularies: dict,
) -> dict:
    """Build a property node for inclusion in a concept's @graph array."""
    prop_type = prop_raw.get("type", "string")
    entry: dict = {
        "@id": prop_out["uri"],
        "@type": "rdf:Property",
        "rdfs:label": _language_tagged(prop_raw.get("label", {})) or _language_tagged({"en": prop_out["id"]}),
        "rdfs:comment": _language_tagged(prop_raw.get("definition", {})),
        "ps:maturity": prop_out["maturity"],
        "schema:domainIncludes": {"@id": concept_uri},
        "schema:rangeIncludes": _resolve_range_includes(prop_type, out_concepts),
        "ps:cardinality": prop_out.get("cardinality"),
    }
    if prop_out.get("vocabulary"):
        vocab = out_vocabularies.get(prop_out["vocabulary"])
        entry["ps:vocabulary"] = vocab["uri"] if vocab else prop_out["vocabulary"]
    if prop_raw.get("references"):
        ref_concept = out_concepts.get(prop_raw["references"])
        entry["ps:references"] = ref_concept["uri"] if ref_concept else prop_raw["references"]
    if prop_raw.get("immutable_after_status"):
        entry["ps:immutableAfterStatus"] = prop_raw["immutable_after_status"]
    for predicate, uris in _external_equivalents_triples(prop_raw).items():
        entry[predicate] = uris if len(uris) > 1 else uris[0]
    return entry


def _concept_to_jsonld(
    concept_out: dict, concept_raw: dict, context_url: str,
    out_concepts: dict, out_properties: dict, properties_raw: dict,
    out_vocabularies: dict,
) -> dict:
    """Build a JSON-LD document for a concept using a @graph array."""
    concept_node: dict = {
        "@id": concept_out["uri"],
        "@type": "rdfs:Class",
        "rdfs:label": concept_out["id"],
        "rdfs:comment": _language_tagged(concept_raw.get("definition", {})),
        "ps:maturity": concept_out["maturity"],
    }
    if concept_out.get("domain"):
        concept_node["ps:domain"] = concept_out["domain"]
    if concept_out.get("abstract"):
        concept_node["ps:abstract"] = True
    supertypes = concept_out.get("supertypes", [])
    if supertypes:
        concept_node["rdfs:subClassOf"] = [
            out_concepts[s]["uri"] if s in out_concepts else s
            for s in supertypes
        ]
    subtypes = concept_out.get("subtypes", [])
    if subtypes:
        concept_node["ps:subtypes"] = [
            out_concepts[s]["uri"] if s in out_concepts else s
            for s in subtypes
        ]
    for predicate, uris in _external_equivalents_triples(concept_raw).items():
        concept_node[predicate] = uris if len(uris) > 1 else uris[0]
    graph = [concept_node]
    props = concept_out.get("properties", [])
    if props:
        for ref in props:
            if ref["id"] in out_properties and ref["id"] in properties_raw:
                graph.append(
                    _concept_property_jsonld(
                        out_properties[ref["id"]], properties_raw[ref["id"]],
                        concept_out["uri"], out_concepts, out_vocabularies,
                    )
                )
    return {"@context": context_url, "@graph": graph}


def _property_to_jsonld(
    prop_out: dict, prop_raw: dict, context_url: str,
    out_concepts: dict, out_vocabularies: dict,
) -> dict:
    """Build a complete JSON-LD document for a standalone property."""
    prop_type = prop_raw.get("type", "string")
    doc: dict = {
        "@context": context_url,
        "@id": prop_out["uri"],
        "@type": "rdf:Property",
        "rdfs:label": _language_tagged(prop_raw.get("label", {})) or _language_tagged({"en": prop_out["id"]}),
        "rdfs:comment": _language_tagged(prop_raw.get("definition", {})),
        "ps:maturity": prop_out["maturity"],
        "schema:rangeIncludes": _resolve_range_includes(prop_type, out_concepts),
        "ps:cardinality": prop_out.get("cardinality"),
    }
    if prop_out.get("vocabulary"):
        vocab = out_vocabularies.get(prop_out["vocabulary"])
        doc["ps:vocabulary"] = vocab["uri"] if vocab else prop_out["vocabulary"]
    if prop_raw.get("references"):
        ref_concept = out_concepts.get(prop_raw["references"])
        doc["ps:references"] = ref_concept["uri"] if ref_concept else prop_raw["references"]
    if prop_raw.get("immutable_after_status"):
        doc["ps:immutableAfterStatus"] = prop_raw["immutable_after_status"]
    for predicate, uris in _external_equivalents_triples(prop_raw).items():
        doc[predicate] = uris if len(uris) > 1 else uris[0]
    used_by = prop_out.get("used_by", [])
    if used_by:
        doc["schema:domainIncludes"] = [
            out_concepts[cid]["uri"] if cid in out_concepts else cid
            for cid in used_by
        ]
    return doc


def _vocabulary_to_jsonld(
    vocab_out: dict, vocab_raw: dict, context_url: str,
) -> dict:
    """Build a complete JSON-LD document for a vocabulary using SKOS."""
    doc: dict = {
        "@context": context_url,
        "@id": vocab_out["uri"],
        "@type": "skos:ConceptScheme",
        "rdfs:label": vocab_out["id"],
        "rdfs:comment": _language_tagged(vocab_raw.get("definition", {})),
        "ps:maturity": vocab_out["maturity"],
    }
    if vocab_out.get("domain"):
        doc["ps:domain"] = vocab_out["domain"]
    for predicate, uris in _external_equivalents_triples(vocab_raw).items():
        doc[predicate] = uris if len(uris) > 1 else uris[0]
    standard = vocab_raw.get("standard")
    if standard:
        std_entry: dict = {"schema:name": standard.get("name", "")}
        if standard.get("uri"):
            std_entry["@id"] = standard["uri"]
        if standard.get("notes"):
            std_entry["ps:notes"] = standard["notes"]
        doc["ps:standardReference"] = std_entry
    values = vocab_out.get("values", [])
    if values:
        doc["skos:hasTopConcept"] = []
        for v in values:
            entry: dict = {
                "@id": v["uri"],
                "@type": "skos:Concept",
                "skos:notation": v["code"],
                "skos:prefLabel": _language_tagged(v.get("label", {})),
                "skos:definition": _language_tagged(v.get("definition", {})),
            }
            if v.get("standard_code"):
                entry["ps:standardCode"] = v["standard_code"]
            doc["skos:hasTopConcept"].append(entry)
    return doc


def _normalize_property_entry(entry) -> dict:
    """Normalize a property entry to {id}."""
    if isinstance(entry, str):
        return {"id": entry}
    return {"id": entry["id"]}


def _collect_all_properties(concept_id: str, merged_concepts: dict) -> list:
    """Collect property entries from a concept and all its supertypes.

    merged_concepts maps concept_id to {data, source} tagged dicts.
    Traversal sees both AidOps and PS concepts so inherited properties
    from PS supertypes (like Profile.subject) are included.
    """
    visited = set()
    all_props = []
    seen_ids = set()

    def walk(cid):
        if cid in visited or cid not in merged_concepts:
            return
        visited.add(cid)
        concept = merged_concepts[cid]["data"]
        for st in concept.get("supertypes", []):
            walk(st)
        for entry in concept.get("properties", []):
            norm = _normalize_property_entry(entry)
            if norm["id"] not in seen_ids:
                seen_ids.add(norm["id"])
                all_props.append(entry)

    walk(concept_id)
    return all_props


def _compute_uri(base_uri: str, domain: str | None, id_str: str) -> str:
    """Compute a URI with optional domain namespace segment."""
    if domain:
        return f"{base_uri}{domain}/{id_str}"
    return f"{base_uri}{id_str}"


def _compute_path(domain: str | None, id_str: str) -> str:
    """Compute a URL path with optional domain namespace segment."""
    if domain:
        return f"/{domain}/{id_str}"
    return f"/{id_str}"


def _compute_property_domain_namespace(
    prop_id: str,
    merged_concepts: dict,
    properties_raw: dict | None = None,
) -> str | None:
    """Derive a property's domain namespace from the concepts that use it.

    If the property has an explicit domain_override, that value is used.
    Otherwise, if all AidOps concepts using this property share the same
    non-null domain, the property gets that domain. Otherwise universal.
    """
    if properties_raw and prop_id in properties_raw:
        prop_data = properties_raw[prop_id]
        if "domain_override" in prop_data:
            return prop_data["domain_override"]

    domains = set()
    for tagged in merged_concepts.values():
        if tagged.get("source") != "aidops":
            continue
        concept_data = tagged["data"]
        for entry in concept_data.get("properties", []):
            pid = entry["id"] if isinstance(entry, dict) else entry
            if pid == prop_id:
                domains.add(concept_data.get("domain"))
    if len(domains) == 1:
        sole_domain = next(iter(domains))
        if sole_domain is not None:
            return sole_domain
    return None


def _property_to_json_schema(
    prop_data: dict, vocabularies: dict, out_vocabularies: dict | None = None,
) -> dict:
    """Convert a property definition to a JSON Schema property definition."""
    prop_type = prop_data.get("type", "string")
    cardinality = prop_data.get("cardinality", "single")
    vocab_ref = prop_data.get("vocabulary")

    if vocab_ref and vocab_ref in vocabularies:
        vocab = vocabularies[vocab_ref]
        codes = [v["code"] for v in vocab.get("values", [])]
        item_schema: dict = {"type": "string", "enum": codes}
        if out_vocabularies and vocab_ref in out_vocabularies:
            item_schema["$comment"] = out_vocabularies[vocab_ref]["uri"]
    elif prop_type.startswith("concept:"):
        item_schema = {"type": ["object", "string"]}
    else:
        item_schema = dict(TYPE_MAP.get(prop_type, {"type": "string"}))

    if cardinality == "multiple":
        return {"type": "array", "items": item_schema}
    return item_schema


def _concept_uri_for(concept_id: str, out_concepts: dict) -> str:
    """Return the URI for a concept, using canonical PS URI for vendored concepts."""
    if concept_id in out_concepts:
        return out_concepts[concept_id]["uri"]
    # Fall back to canonical PS URI for vendored types not in out_concepts
    return f"{PS_BASE_URI}{concept_id}"


def build_vocabulary(schema_dir: Path) -> dict:
    """Build the full AidOps vocabulary output from YAML source files.

    Loads both schema/ (AidOps) and vendor/publicschema/schema/ (PS) to
    resolve the full type graph. Output is filtered to AidOps-owned items.

    Returns a dict with keys: meta, concepts, properties, vocabularies,
    context, concept_schemas, jsonld_docs, credential_schemas.
    """
    meta = load_yaml(schema_dir / "_meta.yaml")
    base_uri = meta.get("base_uri", "https://schema.aidops.org/")

    vendor_schema_dir = schema_dir.parent / "vendor" / "publicschema" / "schema"
    merged = load_merged_schema(schema_dir, vendor_schema_dir)

    # Convenience: flat dicts of raw YAML data for each source
    all_concepts_raw: dict[str, dict] = {
        cid: tagged["data"] for cid, tagged in merged["concepts"].items()
    }
    all_properties_raw: dict[str, dict] = {
        pid: tagged["data"] for pid, tagged in merged["properties"].items()
    }
    all_vocabularies_raw: dict[str, dict] = {
        vkey: tagged["data"] for vkey, tagged in merged["vocabularies"].items()
    }

    # AidOps-owned subsets
    aidops_concepts_raw: dict[str, dict] = {
        cid: tagged["data"] for cid, tagged in merged["concepts"].items()
        if tagged["source"] == "aidops"
    }
    aidops_properties_raw: dict[str, dict] = {
        pid: tagged["data"] for pid, tagged in merged["properties"].items()
        if tagged["source"] == "aidops"
    }
    aidops_vocabularies_raw: dict[str, dict] = {
        vkey: tagged["data"] for vkey, tagged in merged["vocabularies"].items()
        if tagged["source"] == "aidops"
    }
    aidops_bibliography_raw: dict[str, dict] = {
        bid: tagged["data"] for bid, tagged in merged["bibliography"].items()
        if tagged["source"] == "aidops"
    }

    categories_path = schema_dir / "categories.yaml"
    categories_raw = load_yaml(categories_path) if categories_path.exists() else {}

    # Compute property domains (which AidOps concepts use each property)
    property_domains: dict[str, list[str]] = {
        pid: [] for pid in aidops_properties_raw
    }
    for concept_id, concept_data in aidops_concepts_raw.items():
        for entry in concept_data.get("properties", []):
            prop_id = entry["id"] if isinstance(entry, dict) else entry
            if prop_id in property_domains:
                property_domains[prop_id].append(concept_id)

    # Build output concepts (AidOps-owned only).
    # Supertypes and subtypes may reference PS concepts; we include their
    # canonical PS URIs in the output.
    out_concepts: dict[str, dict] = {}
    for concept_id, data in aidops_concepts_raw.items():
        domain = data.get("domain")
        out_concepts[concept_id] = {
            "id": concept_id,
            "source": "aidops",
            "domain": domain,
            "uri": _compute_uri(base_uri, domain, concept_id),
            "path": _compute_path(domain, concept_id),
            "maturity": data.get("maturity"),
            "abstract": data.get("abstract", False),
            "featured": bool(data.get("featured", False)),
            "label": data.get("label", {}),
            "definition": data.get("definition", {}),
            "properties": [
                _normalize_property_entry(e)
                for e in data.get("properties", [])
            ],
            "subtypes": data.get("subtypes", []),
            "supertypes": data.get("supertypes", []),
            "convergence": data.get("convergence"),
            "external_equivalents": data.get("external_equivalents"),
            "property_groups": data.get("property_groups"),
        }

    # Also include PS concepts referenced as supertypes/subtypes so that
    # URI resolution works in JSON-LD documents (with source tag and PS URI).
    for concept_id, tagged in merged["concepts"].items():
        if tagged["source"] != "publicschema":
            continue
        data = tagged["data"]
        domain = data.get("domain")
        out_concepts[concept_id] = {
            "id": concept_id,
            "source": "publicschema",
            "domain": domain,
            "uri": _compute_uri(PS_BASE_URI, domain, concept_id),
            "path": _compute_path(domain, concept_id),
            "maturity": data.get("maturity"),
            "abstract": data.get("abstract", False),
            "featured": False,
            "label": data.get("label", {}),
            "definition": data.get("definition", {}),
            "properties": [
                _normalize_property_entry(e)
                for e in data.get("properties", [])
            ],
            "subtypes": data.get("subtypes", []),
            "supertypes": data.get("supertypes", []),
            "convergence": data.get("convergence"),
            "external_equivalents": data.get("external_equivalents"),
            "property_groups": data.get("property_groups"),
        }

    # Build output properties. AidOps properties get AidOps URIs;
    # PS properties get canonical PS URIs (for inheritance resolution).
    out_properties: dict[str, dict] = {}
    for prop_id, data in all_properties_raw.items():
        source = merged["properties"][prop_id]["source"]
        prop_ns = _compute_property_domain_namespace(
            prop_id, merged["concepts"], all_properties_raw,
        )
        if source == "aidops":
            prop_uri = _compute_uri(base_uri, prop_ns, prop_id)
            prop_path = _compute_path(prop_ns, prop_id)
        else:
            prop_uri = _compute_uri(PS_BASE_URI, prop_ns, prop_id)
            prop_path = _compute_path(prop_ns, prop_id)
        out_properties[prop_id] = {
            "id": prop_id,
            "source": source,
            "uri": prop_uri,
            "path": prop_path,
            "maturity": data.get("maturity"),
            "label": data.get("label", {}),
            "definition": data.get("definition", {}),
            "type": data.get("type"),
            "cardinality": data.get("cardinality"),
            "vocabulary": data.get("vocabulary"),
            "references": data.get("references"),
            "used_by": property_domains.get(prop_id, []),
            "schema_org_equivalent": data.get("schema_org_equivalent"),
            "sensitivity": data.get("sensitivity"),
            "system_mappings": data.get("system_mappings"),
            "external_equivalents": data.get("external_equivalents"),
            "convergence": data.get("convergence"),
            "category": data.get("category"),
            "core": data.get("core"),
            "age_applicability": data.get("age_applicability"),
            "valid_instruments": data.get("valid_instruments"),
            "immutable_after_status": data.get("immutable_after_status"),
        }

    # Build output vocabularies (same URI logic: AidOps vs. PS).
    out_vocabularies: dict[str, dict] = {}
    for vocab_key, tagged in merged["vocabularies"].items():
        data = tagged["data"]
        source = tagged["source"]
        # vocab_id is the bare name from YAML (e.g. "status").
        # vocab_key is the path-based dict key (e.g. "sp/status") and is what
        # drives URI construction below; vocab_id is kept for reference/output.
        vocab_id = data["id"]
        vocab_ns = data.get("domain")
        if source == "aidops":
            vocab_base = f"{base_uri}vocab/{vocab_key}"
        else:
            vocab_base = f"{PS_BASE_URI}vocab/{vocab_key}"
        vocab_path = f"/vocab/{vocab_key}"
        values = []
        for v in data.get("values", []):
            value_out = {
                "code": v["code"],
                "uri": f"{vocab_base}/{v['code']}",
                "label": v.get("label", {}),
                "standard_code": v.get("standard_code"),
                "definition": v.get("definition", {}),
            }
            if v.get("group_type_applicability") is not None:
                value_out["group_type_applicability"] = list(v["group_type_applicability"])
            if v.get("level") is not None:
                value_out["level"] = v["level"]
            if v.get("parent_code") is not None:
                value_out["parent_code"] = v["parent_code"]
            values.append(value_out)
        out_vocabularies[vocab_key] = {
            "id": vocab_id,
            "source": source,
            "domain": vocab_ns,
            "uri": vocab_base,
            "path": vocab_path,
            "maturity": data.get("maturity"),
            "label": data.get("label", {}),
            "definition": data.get("definition", {}),
            "standard": data.get("standard"),
            "values": values,
            "system_mappings": data.get("system_mappings"),
            "external_equivalents": data.get("external_equivalents"),
            "same_standard_systems": data.get("same_standard_systems"),
            "external_values": data.get("external_values", False),
            "references": data.get("references", []),
        }

    # Build bibliography output (AidOps-owned only)
    out_bibliography: dict[str, dict] = {}
    concept_bib_refs: dict[str, list[str]] = {
        cid: [] for cid in aidops_concepts_raw
    }
    vocab_bib_refs: dict[str, list[str]] = {
        vid: [] for vid in aidops_vocabularies_raw
    }
    property_bib_refs: dict[str, list[str]] = {
        pid: [] for pid in aidops_properties_raw
    }

    for bib_id, data in aidops_bibliography_raw.items():
        informs = data.get("informs") or {"concepts": [], "vocabularies": [], "properties": []}
        out_bibliography[bib_id] = {
            "id": bib_id,
            "title": data.get("title"),
            "short_title": data.get("short_title"),
            "standard_number": data.get("standard_number"),
            "publisher": data.get("publisher"),
            "authors": data.get("authors", []),
            "year": data.get("year"),
            "version": data.get("version"),
            "type": data.get("type"),
            "domain": data.get("domain"),
            "uri": data.get("uri"),
            "access": data.get("access"),
            "status": data.get("status"),
            "informs": {
                "concepts": list(informs.get("concepts", [])),
                "vocabularies": list(informs.get("vocabularies", [])),
                "properties": list(informs.get("properties", [])),
            },
        }
        for cid in informs.get("concepts", []):
            if cid in concept_bib_refs:
                concept_bib_refs[cid].append(bib_id)
            else:
                print(
                    f"WARNING: bibliography {bib_id!r} informs concept {cid!r} which is not defined",
                    file=sys.stderr,
                )
        for vid in informs.get("vocabularies", []):
            if vid in vocab_bib_refs:
                vocab_bib_refs[vid].append(bib_id)
            else:
                print(
                    f"WARNING: bibliography {bib_id!r} informs vocabulary {vid!r} which is not defined",
                    file=sys.stderr,
                )
        for pid in informs.get("properties", []):
            if pid in property_bib_refs:
                property_bib_refs[pid].append(bib_id)
            else:
                print(
                    f"WARNING: bibliography {bib_id!r} informs property {pid!r} which is not defined",
                    file=sys.stderr,
                )

    for cid, refs in concept_bib_refs.items():
        out_concepts[cid]["bibliography_refs"] = sorted(refs)
    for vid, refs in vocab_bib_refs.items():
        if vid in out_vocabularies:
            out_vocabularies[vid]["bibliography_refs"] = sorted(refs)
    for pid, refs in property_bib_refs.items():
        if pid in out_properties:
            out_properties[pid]["bibliography_refs"] = sorted(refs)

    # Build JSON-LD context (AidOps URIs for owned items; PS URIs for vendored).
    context_map: dict[str, object] = {
        "@vocab": base_uri,
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "schema": "https://schema.org/",
        "ps": "https://publicschema.org/meta/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "dpv": "https://w3id.org/dpv#",
        "dpv-pd": "https://w3id.org/dpv/pd#",
        "dpv-gdpr": "https://w3id.org/dpv/legal/eu/gdpr#",
        "dpv-tech": "https://w3id.org/dpv/tech#",
        "dpv-loc": "https://w3id.org/dpv/loc#",
        "aidops": base_uri,
        "type": "@type",
    }
    context_map["schema:domainIncludes"] = {
        "@id": "https://schema.org/domainIncludes",
        "@type": "@id",
    }
    context_map["schema:rangeIncludes"] = {
        "@id": "https://schema.org/rangeIncludes",
        "@type": "@id",
    }
    context_map["rdfs:subClassOf"] = {
        "@id": "http://www.w3.org/2000/01/rdf-schema#subClassOf",
        "@type": "@id",
        "@container": "@set",
    }
    context_map["ps:subtypes"] = {
        "@id": "https://publicschema.org/meta/subtypes",
        "@type": "@id",
        "@container": "@set",
    }
    context_map["ps:references"] = {
        "@id": "https://publicschema.org/meta/references",
        "@type": "@id",
    }
    context_map["ps:vocabulary"] = {
        "@id": "https://publicschema.org/meta/vocabulary",
        "@type": "@id",
    }
    skos_base = "http://www.w3.org/2004/02/skos/core#"
    for skos_pred in MATCH_PREDICATES.values():
        local = skos_pred.split(":", 1)[1]
        context_map[skos_pred] = {"@id": f"{skos_base}{local}", "@type": "@id"}
    context_map["rdfs:seeAlso"] = {
        "@id": "http://www.w3.org/2000/01/rdf-schema#seeAlso",
        "@type": "@id",
    }
    for concept_id, concept_out in out_concepts.items():
        context_map[concept_id] = concept_out["uri"]
    for prop_id, prop_out in out_properties.items():
        prop_uri = prop_out["uri"]
        prop_raw = all_properties_raw.get(prop_id, {})
        prop_type = prop_raw.get("type", "string")
        cardinality = prop_raw.get("cardinality", "single")
        if prop_type.startswith("concept:"):
            entry: dict[str, str] = {"@id": prop_uri, "@type": "@id"}
        elif prop_type in JSONLD_TYPE_COERCION:
            entry = {"@id": prop_uri, "@type": JSONLD_TYPE_COERCION[prop_type]}
        elif cardinality == "multiple":
            entry = {"@id": prop_uri}
        else:
            context_map[prop_id] = prop_uri
            entry = None
        if entry is not None:
            if cardinality == "multiple":
                entry["@container"] = "@set"
            context_map[prop_id] = entry
        schema_eq = prop_raw.get("schema_org_equivalent")
        if schema_eq and schema_eq.startswith("schema:"):
            alias = schema_eq.split(":", 1)[1]
            context_map[alias] = context_map[prop_id]

    version = meta.get("version", "0.1.0")
    maturity = meta.get("maturity", "draft")
    version_label = "draft" if maturity == "draft" else ".".join(version.split(".")[:2])
    context = {"@context": context_map}

    # Build JSON Schema per AidOps concept.
    # _collect_all_properties traverses the full merged type graph so
    # inherited PS properties (e.g. subject, observation_date) are included.
    concept_schemas: dict[str, dict] = {}
    for concept_id, data in aidops_concepts_raw.items():
        schema_props: dict[str, dict] = {}
        for entry in _collect_all_properties(concept_id, merged["concepts"]):
            norm = _normalize_property_entry(entry)
            prop_id = norm["id"]
            if prop_id in all_properties_raw:
                schema_props[prop_id] = _property_to_json_schema(
                    all_properties_raw[prop_id], all_vocabularies_raw, out_vocabularies,
                )

        concept_domain = data.get("domain")
        schema_base = f"{base_uri}{concept_domain}/" if concept_domain else base_uri
        concept_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{schema_base}schemas/{concept_id}.schema.json",
            "title": concept_id,
            "type": "object",
            "properties": schema_props,
        }
        concept_schemas[concept_id] = concept_schema

    # Build JSON-LD documents for AidOps-owned concepts, properties, vocabularies.
    context_url = f"{base_uri}ctx/{version_label}.jsonld"
    jsonld_docs: dict[str, dict] = {}

    for concept_id, concept_out in out_concepts.items():
        if concept_out.get("source") != "aidops":
            continue
        domain = concept_out.get("domain")
        key = f"concepts/{domain}/{concept_id}.jsonld" if domain else f"concepts/{concept_id}.jsonld"
        jsonld_docs[key] = _concept_to_jsonld(
            concept_out, aidops_concepts_raw[concept_id], context_url,
            out_concepts, out_properties, all_properties_raw,
            out_vocabularies,
        )

    for prop_id, prop_out in out_properties.items():
        if prop_out.get("source") != "aidops":
            continue
        prop_ns = _compute_property_domain_namespace(prop_id, merged["concepts"], all_properties_raw)
        key = f"properties/{prop_ns}/{prop_id}.jsonld" if prop_ns else f"properties/{prop_id}.jsonld"
        jsonld_docs[key] = _property_to_jsonld(
            prop_out, aidops_properties_raw[prop_id], context_url,
            out_concepts, out_vocabularies,
        )

    for vocab_key, vocab_out in out_vocabularies.items():
        if vocab_out.get("source") != "aidops":
            continue
        key = f"vocab/{vocab_key}.jsonld"
        jsonld_docs[key] = _vocabulary_to_jsonld(
            vocab_out, aidops_vocabularies_raw[vocab_key], context_url,
        )

    # Build categories output
    out_categories: dict[str, dict] = {}
    for cat_id, cat_data in categories_raw.items():
        out_categories[cat_id] = {"label": cat_data.get("label", {})}

    # Filter out_concepts/out_properties/out_vocabularies for the main output:
    # emit only AidOps-owned items. PS items were needed for resolution but
    # should not appear in vocabulary.json or the manifest.
    aidops_out_concepts = {
        cid: c for cid, c in out_concepts.items() if c.get("source") == "aidops"
    }
    aidops_out_properties = {
        pid: p for pid, p in out_properties.items() if p.get("source") == "aidops"
    }
    aidops_out_vocabularies = {
        vid: v for vid, v in out_vocabularies.items() if v.get("source") == "aidops"
    }

    return {
        "meta": meta,
        "concepts": aidops_out_concepts,
        "properties": aidops_out_properties,
        "vocabularies": aidops_out_vocabularies,
        "bibliography": out_bibliography,
        "categories": out_categories,
        "context": context,
        "concept_schemas": concept_schemas,
        "credential_schemas": {},
        "jsonld_docs": jsonld_docs,
        # Full merged views for RDF / SHACL generation that needs all types
        "_all_concepts": out_concepts,
        "_all_properties": out_properties,
        "_all_vocabularies": out_vocabularies,
    }


def write_outputs(result: dict, dist_dir: Path):
    """Write build outputs to the dist directory."""
    from build.export import generate_all_downloads
    from build.rdf_export import write_full_jsonld, write_shacl, write_turtle

    dist_dir.mkdir(parents=True, exist_ok=True)
    schemas_dir = dist_dir / "schemas"
    schemas_dir.mkdir(exist_ok=True)

    # vocabulary.json (AidOps-owned items only)
    vocabulary = {
        "meta": result["meta"],
        "concepts": result["concepts"],
        "properties": result["properties"],
        "vocabularies": result["vocabularies"],
        "bibliography": result.get("bibliography", {}),
        "categories": result.get("categories", {}),
    }
    (dist_dir / "vocabulary.json").write_text(
        json.dumps(vocabulary, indent=2, ensure_ascii=False) + "\n"
    )

    # context.jsonld
    (dist_dir / "context.jsonld").write_text(
        json.dumps(result["context"], indent=2, ensure_ascii=False) + "\n"
    )

    # Per-concept JSON Schemas
    for concept_id, schema in result["concept_schemas"].items():
        filename = f"{concept_id}.schema.json"
        (schemas_dir / filename).write_text(
            json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
        )

    # Per-concept/property/vocabulary JSON-LD documents
    jsonld_docs = result.get("jsonld_docs", {})
    if jsonld_docs:
        jsonld_dir = dist_dir / "jsonld"
        jsonld_dir.mkdir(exist_ok=True)
        for rel_path, doc in jsonld_docs.items():
            out_path = jsonld_dir / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
            )

    # RDF exports (Turtle, JSON-LD, SHACL)
    write_turtle(result, dist_dir)
    write_full_jsonld(result, dist_dir)
    write_shacl(result, dist_dir)

    # CSV and Excel downloads per concept
    downloads_dir = dist_dir / "downloads"
    generate_all_downloads(result, downloads_dir)

    # Machine-readable artifact index
    meta = result["meta"]
    base_uri = meta.get("base_uri", "https://schema.aidops.org/")
    version = meta.get("version", "0.1.0")
    maturity = meta.get("maturity", "draft")
    version_label = "draft" if maturity == "draft" else ".".join(version.split(".")[:2])

    manifest = {
        "name": meta.get("name", "AidOps"),
        "version": version,
        "maturity": maturity,
        "base_uri": base_uri,
        "artifacts": {
            "context": f"/ctx/{version_label}.jsonld",
            "vocabulary": "/vocabulary.json",
            "turtle": f"/v/{version_label}/aidops.ttl",
            "jsonld": f"/v/{version_label}/aidops.jsonld",
            "shacl": f"/v/{version_label}/aidops.shacl.ttl",
        },
        "concepts": {},
        "vocabularies": {},
        "credentials": {},
    }

    for concept_id, concept in result["concepts"].items():
        path = concept["path"]
        domain = concept.get("domain")
        dl_prefix = f"/downloads/{domain}" if domain else "/downloads"
        manifest["concepts"][concept_id] = {
            "schema": f"/schemas/{concept_id}.schema.json",
            "jsonld": f"{path}.jsonld",
            "csv": f"{dl_prefix}/{concept_id}.csv",
            "xlsx_definition": f"{dl_prefix}/{concept_id}-definition.xlsx",
            "xlsx_template": f"{dl_prefix}/{concept_id}-template.xlsx",
        }

    for vocab_id in result.get("vocabularies", {}):
        manifest["vocabularies"][vocab_id] = {
            "jsonld": f"/vocab/{vocab_id}.jsonld",
        }

    (dist_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )


def main():
    """CLI entry point for build."""
    schema_dir = Path("schema")
    dist_dir = Path("dist")

    if len(sys.argv) > 1:
        schema_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        dist_dir = Path(sys.argv[2])

    result = build_vocabulary(schema_dir)
    write_outputs(result, dist_dir)
    print(
        f"Built {len(result['concepts'])} concepts, "
        f"{len(result['properties'])} properties, "
        f"{len(result['vocabularies'])} vocabularies, "
        f"{len(result.get('bibliography', {}))} bibliography entries."
    )


if __name__ == "__main__":
    main()
