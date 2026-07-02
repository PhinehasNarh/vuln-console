"""Deterministic finding fingerprint, version 1 (ADR-0007).

v1 keys location by file path only; class-specific location keys (context
hashing, versionless purls, secret value hashes) arrive with v2 in Milestone 2.
The version prefix makes migration explicit.
"""

import hashlib

FINGERPRINT_VERSION = "v1"


def compute_fingerprint(
    *, finding_class: str, rule_key: str, asset_key: str, location_key: str
) -> str:
    material = "|".join((FINGERPRINT_VERSION, finding_class, rule_key, asset_key, location_key))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
