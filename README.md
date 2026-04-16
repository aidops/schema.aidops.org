# AidOps Schema (schema.aidops.org)

Humanitarian assessment profiles and operational tooling, built on [PublicSchema](https://publicschema.org).

## What this is

AidOps defines assessment profiles for humanitarian and social protection field operations: food security, anthropometry, dwelling damage, and more. Each profile captures item-level instrument responses alongside canonical scoring outputs.

AidOps imports PublicSchema's core types (Person, Household, Profile, Instrument, ScoringEvent) as a dependency and extends them with domain-specific profiles, properties, and vocabularies.

## Quick start

```bash
just setup                # install Python + Node dependencies
just fetch-publicschema   # vendor PublicSchema schema
just check                # validate + lint + test + build
just dev                  # start the dev server
```

## Architecture

- **schema/**: YAML source of truth. Concepts, properties, vocabularies, bibliography.
- **vendor/publicschema/**: Vendored PublicSchema schema (fetched, not committed).
- **build/**: Python build pipeline. Validates YAML, generates `dist/` outputs.
- **dist/**: Generated artifacts. Never hand-edited.
- **site/**: Astro static site at schema.aidops.org.
- **tests/**: Python tests (pytest).

Data flows one direction: `schema/` + `vendor/` -> `build/` -> `dist/` -> `site/` -> static HTML.

## Relationship to PublicSchema

AidOps depends on PublicSchema for universal concepts (Person, Household, Profile, etc.). The dependency is explicit and version-pinned in `aidops.yaml`. AidOps can extend but not fork the foundation.

| | PublicSchema | AidOps |
|---|---|---|
| Scope | Universal public service delivery | Humanitarian assessment & operations |
| URI | publicschema.org | schema.aidops.org |
| Cadence | Slower, formal governance | Faster, practitioner-oriented |

## Profiles

- **FoodSecurityProfile**: WFP FCS/rCSI/LCS, FAO HDDS/FIES/MDD-W/MAHFP, FANTA HHS
- **AnthropometricProfile**: SMART, WHO Anthro, CMAM screening
- **DwellingDamageProfile**: Shelter Cluster, DTM post-shock assessment
- **HazardEvent**: Natural/conflict hazard events that trigger damage assessments

## License

Apache-2.0
