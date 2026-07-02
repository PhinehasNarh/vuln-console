# ADR-0001: Python + FastAPI backend

- Status: Accepted
- Date: 2026-07-02

## Context

The platform's workload is dominated by parsing heterogeneous security formats (SARIF, CycloneDX, SPDX, native JSON from a dozen scanners), synchronizing intelligence feeds (NVD, OSV, EPSS, KEV), and an AI layer over multiple LLM providers. Candidates considered: Python + FastAPI, TypeScript + NestJS, Go, and a polyglot split.

## Decision

Python 3.12 with FastAPI, Pydantic v2 for validation and settings, SQLAlchemy 2.0 (async) with Alembic migrations, and httpx for outbound calls.

## Rationale

- Strongest ecosystem for security file formats and feed clients; most reference tooling in this space is Python.
- First-class LLM SDKs (Anthropic, OpenAI, Ollama) for the AI milestone.
- FastAPI generates OpenAPI automatically, which the API-first principle requires anyway.
- Pydantic v2 gives runtime validation at every trust boundary with static typing support (mypy).

## Consequences

- Positive: fastest path to working vertical slices; one language across API, workers, and CLI.
- Negative: raw parsing throughput below Go; acceptable at homelab scale, and ingestion workers are the designated first extraction point if it ever matters (ADR-0002).
- Mitigation: all code strictly typed (mypy) and async-native to avoid the common Python service pitfalls.
