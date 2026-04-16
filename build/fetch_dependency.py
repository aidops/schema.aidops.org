"""Fetch the vendored PublicSchema schema/ directory.

Usage:
    python -m build.fetch_dependency [--local] [--version TAG]

    --local      Copy schema/ from the local path configured in aidops.yaml.
                 This is the default when no flag is given.
    --version    (stub) Download schema/ from a GitHub release tag.

The fetched content is written to vendor/publicschema/schema/.
After fetching, the script validates that a _meta.yaml is present.
"""

import shutil
import sys
from pathlib import Path

import yaml


def _load_config(project_root: Path) -> dict:
    """Load aidops.yaml from the project root."""
    config_path = project_root / "aidops.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"aidops.yaml not found at {config_path}")
    with config_path.open() as f:
        return yaml.safe_load(f) or {}


def fetch_local(project_root: Path) -> None:
    """Copy schema/ from the local PS path configured in aidops.yaml."""
    config = _load_config(project_root)

    ps_section = config.get("publicschema")
    if not ps_section:
        raise ValueError("aidops.yaml is missing the 'publicschema' section")

    local_path_str = ps_section.get("local_path")
    if not local_path_str:
        raise ValueError("aidops.yaml publicschema.local_path is not set")

    # Resolve relative paths relative to the project root
    local_path = (project_root / local_path_str).resolve()
    if not local_path.exists():
        raise FileNotFoundError(
            f"PublicSchema local_path does not exist: {local_path}\n"
            f"  (configured as '{local_path_str}' in aidops.yaml)"
        )

    if local_path == (project_root / "schema").resolve():
        raise ValueError(
            "local_path points to AidOps's own schema/ directory; "
            "it must point to PublicSchema's schema/"
        )

    dest = project_root / "vendor" / "publicschema" / "schema"
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"Copying {local_path} -> {dest}")

    # Remove the old vendor copy so we start clean, then copy fresh
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(local_path, dest)

    _validate_fetched(dest)
    print("Done. PublicSchema schema/ is up to date in vendor/.")


def fetch_release(version: str, project_root: Path) -> None:
    """Download schema/ from a GitHub release tag. (Stub: not yet implemented.)"""
    raise NotImplementedError(
        f"Downloading from GitHub release '{version}' is not yet implemented.\n"
        "Use --local for now."
    )


def _validate_fetched(schema_dir: Path) -> None:
    """Confirm the fetched schema/ directory looks valid."""
    meta = schema_dir / "_meta.yaml"
    if not meta.exists():
        raise RuntimeError(
            f"Fetched schema directory is missing _meta.yaml: {schema_dir}\n"
            "The source may not be a valid PublicSchema schema/ directory."
        )
    print(f"Validated: {meta} exists.")


def main() -> None:
    """CLI entry point."""
    args = sys.argv[1:]
    project_root = Path.cwd()

    if "--version" in args:
        idx = args.index("--version")
        if idx + 1 >= len(args):
            print("ERROR: --version requires a tag argument", file=sys.stderr)
            sys.exit(1)
        version = args[idx + 1]
        fetch_release(version, project_root)
    else:
        # Default to --local (most common dev use)
        fetch_local(project_root)


if __name__ == "__main__":
    main()
