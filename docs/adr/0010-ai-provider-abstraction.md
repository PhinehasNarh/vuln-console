# ADR-0010: AI provider abstraction

- Status: Accepted
- Date: 2026-07-02

## Context

The AI layer (summaries, exploitability explanations, remediation guidance, NL Q&A, clustering) must support multiple LLM providers, including fully local operation, and must not leak sensitive finding data to providers unintentionally.

## Decision

A thin `LLMProvider` protocol in the AI Services context (complete, chat, embed), with an Anthropic adapter first and an Ollama adapter for local models. Provider choice is per-capability configuration, so e.g. NL Q&A can use a hosted model while secret-adjacent summarization stays local. All prompts pass through a redaction step that strips secret values and credentials before leaving the platform boundary.

Implementation detail deferred to Milestone 6, where the `claude-api` skill reference will be consulted for current model selection and API usage.

## Consequences

- Positive: swappable providers; local-only mode possible; redaction is structural, not per-callsite.
- Negative: an abstraction over providers flattens provider-specific strengths (tool use, caching).
- Mitigation: the protocol is intentionally minimal and adapters may expose provider-native extensions behind capability flags rather than lowest-common-denominator emulation.
