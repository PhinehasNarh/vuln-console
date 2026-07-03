"""Deterministic finding fingerprint, version 2 (ADR-0007).

v2 introduces class-specific identity so the same real-world issue correlates
across scanners:

- sca / container: rule = the vulnerability id (CVE/GHSA), location = the
  versionless purl. Trivy and Grype reporting CVE-X in pkg:pypi/requests
  produce the same fingerprint; upgrading the package does not mint a new one.
- secret: rule = the constant "secret", location = file path + hash of the
  secret value. Gitleaks and TruffleHog finding the same credential in the
  same file correlate regardless of their rule naming.
- cloud: rule = the check id (e.g. s3_bucket_public_access), location = the
  resource uid/ARN. The same failing control on the same cloud resource
  correlates across re-scans, and (where check ids align) across CSPM tools.
- sast / iac: rule = tool-namespaced rule id, location = file path.
  (Context hashing to survive line drift is a future fingerprint version.)

The version prefix makes any future change an explicit, migratable event.
v1 (path-only, tool-namespaced everything) shipped in M1 and was retired
before any production data existed.
"""

import hashlib

FINGERPRINT_VERSION = "v2"


def derive_identity(
    *,
    finding_class: str,
    tool: str,
    rule_id: str,
    file_path: str | None,
    hints: dict[str, str],
) -> tuple[str, str]:
    """Return (rule_key, location_key) for fingerprinting and display."""
    if finding_class in ("sca", "container"):
        vuln_id = hints.get("vuln_id")
        rule_key = vuln_id.upper() if vuln_id else f"{tool}:{rule_id}"
        location_key = (
            hints.get("purl_base") or hints.get("package") or file_path or ""
        )
        return rule_key, location_key
    if finding_class == "secret":
        secret_hash = hints.get("secret_hash", "")
        return "secret", f"{file_path or ''}|{secret_hash}"
    if finding_class == "cloud":
        # rule id is the check id; keep it un-namespaced so the same benchmark
        # control correlates across CSPM tools. Location is the resource.
        return rule_id, hints.get("resource_uid") or file_path or ""
    return f"{tool}:{rule_id}", file_path or ""


def compute_fingerprint(
    *, finding_class: str, rule_key: str, asset_key: str, location_key: str
) -> str:
    material = "|".join((FINGERPRINT_VERSION, finding_class, rule_key, asset_key, location_key))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
