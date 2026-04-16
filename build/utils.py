"""Shared utility functions for the AidOps build and validation pipeline."""


def collect_inherited_ids(
    concept_data: dict,
    merged_concepts: dict,
    result: set[str],
    visited: set[str],
) -> None:
    """Walk the supertype chain and collect all inherited property IDs.

    merged_concepts maps concept_id to {data, source} tagged dicts.
    """
    for st in concept_data.get("supertypes", []):
        if st in visited or st not in merged_concepts:
            continue
        visited.add(st)
        parent_data = merged_concepts[st]["data"]
        for prop_entry in parent_data.get("properties", []):
            pid = prop_entry["id"] if isinstance(prop_entry, dict) else prop_entry
            result.add(pid)
        collect_inherited_ids(parent_data, merged_concepts, result, visited)
