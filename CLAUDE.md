# AidOps (schema.aidops.org)

## What this is

AidOps defines humanitarian assessment profiles and operational tooling, built on PublicSchema. It imports PublicSchema's core types as a dependency and extends them with domain-specific profiles, properties, and vocabularies.

See the sibling project at `../v2/` for PublicSchema itself.

## Architecture

- **schema/**: YAML source of truth. Concepts, properties, vocabularies, categories, bibliography.
- **vendor/publicschema/schema/**: Vendored PS schema (fetched via `just fetch-publicschema`, not committed).
- **build/**: Python build pipeline. Validates YAML, generates `dist/` outputs (JSON, CSV, XLSX, TTL, SHACL, JSON-LD).
- **dist/**: Generated artifacts. Never hand-edited.
- **site/**: Astro static site. Reads `dist/vocabulary.json` via Vite alias.
- **tests/**: Python tests (pytest).

Data flows: `schema/` + `vendor/publicschema/` -> `build/` -> `dist/` -> `site/` -> static HTML.

## Cross-schema resolution

The build pipeline loads YAML from both `schema/` (AidOps-owned) and `vendor/publicschema/schema/` (vendored PS) into a single merged lookup. All type resolution functions see the full type graph. The output step filters to emit only AidOps-owned types.

Key rules:
- AidOps concepts can reference PS supertypes (e.g., `supertypes: [Profile]`)
- AidOps properties can reference PS vocabularies (e.g., `vocabulary: acute-malnutrition-severity`)
- Inherited properties from PS supertypes appear in AidOps concept output
- PS types in output carry `"source": "publicschema"` and canonical publicschema.org URIs
- Validation skips supertype/subtype symmetry for cross-schema supertypes

## Vendor dependency

PublicSchema is version-pinned in `aidops.yaml`. Fetch it with:
```bash
just fetch-publicschema   # uses --local mode for development
```

The `vendor/` directory is gitignored. CI fetches it before build/validate.

## Development commands

```bash
just setup              # install all deps (uv sync + npm install)
just fetch-publicschema # vendor PublicSchema schema
just build              # generate dist/ from YAML sources
just validate           # validate all YAML source files
just dev                # build then start Astro dev server
just test               # uv run pytest
just check              # validate + lint + test + build
just site-build         # full production build
```

## Key design decisions

- **AidOps URI**: `https://schema.aidops.org/` for owned types.
- **RDF namespace**: Reuses PS's `ps:` meta-namespace for shared metadata predicates. AidOps-owned types get `aidops:` prefix.
- **dist/ variant**: dist-full/ only for now (PS types inlined with `"source": "publicschema"`).
- **No /systems/ section**: System mappings deferred to later.
- **`core: true` tier**: Profile properties may carry `core: true` to mark them as the must-ask subset for rapid-assessment variants. Form compilers (e.g. `aubex-compile --core-only`) can filter to core-only properties to derive a rapid form from a comprehensive profile without duplicating the schema. Defaults to `false` when omitted. Independent of `valid_instruments`.

## Known pitfalls

- `just fetch-publicschema` must run before validate/build/test. Without vendored PS, cross-schema references fail.
- `vendor/` is gitignored. CI must fetch it explicitly.
- The `dist/` directory is generated. Never hand-edit files there.
- When adding properties that reference PS vocabularies, the vocabulary must exist in vendored PS.
