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

# Fetch vendored PublicSchema schema (local mode for development)
fetch-publicschema:
    uv run python -m build.fetch_dependency --local

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
    uv run python -m build.build
    rsync -a --include='*.csv' --include='*.xlsx' --include='*/' --exclude='*' {{dist_dir}}/downloads/ {{site_dir}}/public/
    cp {{dist_dir}}/schemas/*.schema.json {{site_dir}}/public/
    cp {{dist_dir}}/jsonld/concepts/*.jsonld {{site_dir}}/public/
    cp {{dist_dir}}/jsonld/properties/*.jsonld {{site_dir}}/public/
    mkdir -p {{site_dir}}/public/vocabularies
    cp {{dist_dir}}/jsonld/vocab/*.jsonld {{site_dir}}/public/vocabularies/
    cp {{dist_dir}}/vocabulary.json {{site_dir}}/public/vocabulary.json
    mkdir -p {{site_dir}}/public/preview
    cp {{dist_dir}}/preview/*.json {{site_dir}}/public/preview/

# Validate all YAML source files (schema, referential integrity, translations)
validate:
    uv run python -m build.validate

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

# Lint schema content for quality and style issues
lint:
    uv run python -m build.lint

# Validate, lint, test, build, and check everything is clean
check: validate lint test build
    @echo "All checks passed."

# Install all dependencies (Python + Node)
setup:
    uv sync
    cd {{site_dir}} && npm install

# Create a versioned release snapshot from dist/
release: build
    uv run python -m build.release

# Fetch PS, install deps, validate, build data, build site
all: setup fetch-publicschema validate build site-build
