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

# Generate dist/ from YAML sources (AidOps + vendored PublicSchema)
build:
    uv run python -m build.build
    rsync -a --include='*.csv' --include='*.xlsx' --include='*/' --exclude='*' {{dist_dir}}/downloads/ {{site_dir}}/public/
    rsync -a {{dist_dir}}/schemas/ {{site_dir}}/public/schemas/
    cp {{dist_dir}}/vocabulary.json {{site_dir}}/public/vocabulary.json

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

# Fetch PS, install deps, validate, build data, build site
all: setup fetch-publicschema validate build site-build
