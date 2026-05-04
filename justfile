# AidOps build system
# Run `just` to see available recipes, `just dev` to start working.

set dotenv-load := false

schema_dir := "schema"
dist_dir := "dist"
site_dir := "site"

# List available recipes
default:
    @just --list

# --- Dependencies ---

# Fetch vendored PublicSchema schema and synthesize project.yaml for dep resolution
fetch-publicschema:
    uv run python scripts/fetch_publicschema.py

# --- Build ---

# Remove generated artifacts from dist/ and site/public/
clean:
    rm -rf {{dist_dir}}/
    rm -f {{site_dir}}/public/vocabulary.json
    rm -rf {{site_dir}}/public/preview/
    rm -f {{site_dir}}/public/*.csv {{site_dir}}/public/*.xlsx
    rm -f {{site_dir}}/public/*.jsonld {{site_dir}}/public/*.schema.json
    rm -rf {{site_dir}}/public/schemas/
    rm -rf {{site_dir}}/public/vocabularies/*.jsonld

# Generate dist/ from YAML sources (AidOps + vendored PublicSchema)
build: clean
    uv run publicschema build --profile-dir "$PWD" --out "$PWD/{{dist_dir}}"
    cp {{dist_dir}}/vocabulary.json {{site_dir}}/public/vocabulary.json
    mkdir -p {{site_dir}}/public/preview
    rsync -a {{dist_dir}}/preview/ {{site_dir}}/public/preview/
    rsync -a --exclude='preview/' --include='*/' --include='*.jsonld' --include='*.schema.json' --include='*.csv' --include='*.xlsx' --exclude='*' {{dist_dir}}/ {{site_dir}}/public/

# Validate schema (loads project.yaml, resolves deps, compiles embedded profiles)
validate:
    uv run publicschema validate --profile-dir "$PWD"

# --- Site ---

# Start the dev server (rebuilds generated data first)
dev: build
    cd {{site_dir}} && npm run dev

# Production build of the site (validates and rebuilds data first)
site-build: validate build
    cd {{site_dir}} && npm run build

# Preview the production build locally
site-preview:
    cd {{site_dir}} && npm run preview

# Install site dependencies
site-install:
    cd {{site_dir}} && npm install

# --- Development ---

# Run all tests
test:
    uv run pytest

# Validate, test, and build
check: validate test build
    @echo "All checks passed."

# Install all dependencies (Python + Node)
setup:
    uv sync
    cd {{site_dir}} && npm install

# Fetch PS, install deps, validate, build data, build site
all: setup fetch-publicschema validate build site-build
