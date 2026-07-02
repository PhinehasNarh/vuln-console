# ADR-0007: Canonical finding model and fingerprinting

- Status: Accepted
- Date: 2026-07-02

## Context

The same real-world issue is reported by multiple scanners in different shapes, and by the same scanner on every run. Alert fatigue reduction, the platform's core promise, depends on collapsing these into one canonical unit that workflow state can attach to.

## Decision

Two-tier model: **RawFinding** preserves scanner output verbatim; **Finding** is the canonical, deduplicated record keyed by a deterministic fingerprint computed from finding class, normalized rule key, asset key, and a class-specific location key (full sketch in docs/architecture/domain-model.md). Every connector must emit the fields the fingerprint needs; the fingerprint algorithm is versioned so it can evolve with a managed migration.

## Consequences

- Positive: re-scans and multi-scanner overlap update one Finding instead of minting duplicates; triage state survives re-ingestion; scanner disagreements stay visible through the linked RawFindings.
- Negative: fingerprinting is genuinely hard (line drift, refactors, package renames); wrong collisions merge distinct issues, wrong misses resurrect triaged ones.
- Mitigation: class-specific location keys (context hashing for SAST, versionless purl for SCA, value hash for secrets); fingerprint versioning; a correlation review UI in Milestone 2 to inspect merges.
