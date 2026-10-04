"""Canonical deterministic identity generation shared by seed and load clients."""

import uuid

NAMESPACE = uuid.UUID("1ee280e4-0ae9-463f-840f-637ea5b8c439")


def seeded_uuid_value(kind: str, index: int, seed_id: str) -> uuid.UUID:
    """Generate the stable UUID for one seed entity and configured seed ID."""
    return uuid.uuid5(NAMESPACE, f"{seed_id}:{kind}:{index}")
