# ADR-0008: Plugin-based ingestion connectors

- Status: Accepted
- Date: 2026-07-02

## Context

The platform must ingest 19+ source formats today and be extensible to new scanners without touching core code.

## Decision

A `Connector` protocol in the ingestion context:

```python
class Connector(Protocol):
    format_id: str                      # "sarif", "trivy-json", "gitleaks-json", ...
    def sniff(self, artifact: bytes) -> bool: ...
    def parse(self, artifact: bytes) -> Iterable[RawFindingDraft]: ...
```

Connectors are discovered through the `vulnconsole.connectors` Python entry-point group, so third-party packages can register connectors without forking. Built-in connectors ship in-tree under `contexts/ingestion/connectors/`. Generic format connectors (SARIF, CycloneDX, SPDX) cover every tool that emits standard formats; native connectors exist only where the native output is richer than the tool's standard export.

## Consequences

- Positive: adding a scanner is one self-contained module plus tests; standard formats give broad coverage immediately.
- Negative: a plugin API is a compatibility contract; changing `RawFindingDraft` breaks third-party connectors.
- Mitigation: the draft model is versioned with the fingerprint algorithm (ADR-0007); connector conformance tests ship as a reusable pytest fixture set.
