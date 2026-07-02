# Build Journal

The story of how the console came together, told as a 30-day build log. Casual by design; the formal record lives in the ADRs.

## Week 1: figure out what we are actually building

**Day 1.** Wrote down the problem before touching code: five scanners, five report formats, the same SQL injection reported five ways, and no one able to say what actually matters. Decided the product is a deduplication and decision machine, not another scanner. Sketched the questions it must answer: what matters, what first, what can be automated, what is the business risk.

**Day 2.** Stack decisions. Went back and forth between Python, TypeScript, and Go for the backend. Python won because this project lives and dies by parsing weird security formats and calling intelligence feeds, and that ecosystem is just better in Python. FastAPI + Pydantic + SQLAlchemy. Wrote ADR-0001 so future me stops relitigating it.

**Day 3.** The big structural call: modular monolith, not microservices. Eleven bounded contexts in one codebase, talking through NATS events, deployed as one API and one worker. Independently deployable is a property of the design, not the number of containers. ADR-0002. Also picked NATS over RabbitMQ because replayable streams map perfectly onto an ingest pipeline, and one small binary beats an Erlang cluster in a homelab.

**Day 4.** Domain modeling day. The load-bearing idea landed here: raw findings are sacred and stored verbatim, canonical findings are what humans triage, and a deterministic fingerprint bridges the two. If the fingerprint is right, re-uploading a report changes nothing, and that is how users learn to trust the numbers. ADR-0007.

**Day 5.** Threat modeled our own product. Sobering: a vulnerability console is a target map plus a bag of leaked credentials from secret scanners. Wrote the STRIDE analysis, drew trust boundaries, and made peace (in writing) with the homelab shortcuts like OpenSearch running without its security plugin for now.

**Day 6.** Roadmap: eight milestones, each a vertical slice with acceptance criteria. Rule number one: no milestone starts until the previous one demonstrably works. Rule number two: refactor before expanding.

**Day 7.** Scaffolded the monorepo, wrote the docker-compose stack for the eight infrastructure services with healthchecks on everything, and stood up CI with a job that fails the build if an em dash sneaks into any file. Yes, really. House style is house style.

## Week 2: the walking skeleton, backend half

**Day 8.** Shared kernel: settings, JSON logging, async database plumbing, JWT + argon2, problem+json error responses, cursor pagination. Boring on purpose. Every context leans on this, so it has to be dull and dependable.

**Day 9.** Identity context. Users, four roles, permissions, and the decision that CI tokens can only ever push scans, never read findings. If a build agent gets popped, the attacker gets an upload slot, not the whole vulnerability map. Every mutation writes an audit event in the same transaction.

**Day 10.** Ingestion context. Connector protocol (sniff + parse), plugin registry, and the SARIF connector as the first citizen since half the industry can export SARIF. Artifacts go to MinIO untouched; parsing happens later, in the worker, where a hostile file cannot take down the API.

**Day 11.** Fingerprinting and normalization. Wrote fingerprint v1 (class + rule + repo + path) knowing v2 will need context hashing so line-number drift does not resurrect triaged findings. Versioned it from day one so the migration is boring when it comes.

**Day 12.** The worker. Went with plain nats-py over a framework (ADR-0013): the entire retry policy, nak with delay, give up after five deliveries, fits in twenty readable lines, and I would rather debug twenty lines than a framework.

**Day 13.** Findings API with keyset pagination and filters, scans API, the Alembic migration, and the operational CLI. First end-to-end moment in a REPL: SARIF in, two deduplicated findings out, third result correctly folded into an existing one. Genuinely grinned.

**Day 14.** Test day. Unit suite for the fingerprint, the SARIF connector, tokens, and pagination, plus an integration suite that drives the real API against the real stack and proves the acceptance criterion: upload the same report twice, get zero duplicates.

## Week 3: making it feel like a product

**Day 15.** Containerized everything. The api container runs migrations on boot and optionally seeds an admin; the worker refuses to start until the API is healthy, which quietly guarantees migration ordering. Traefik routes / to the SPA and /api to the backend, with security headers on both.

**Day 16.** Paused before writing UI code and wrote the design language instead. Called it Ledger: quiet neutral surfaces, color reserved exclusively for severity and state, tabular numerals everywhere, keyboard first. Wrote down what it must never look like: a template dashboard.

**Day 17.** Personas and journeys. Sana (staff security engineer, keyboard-only, three hours a day), Marco (developer who visits when a finding lands on his repo), Priya (manager who wants three trustworthy numbers). The findings workspace is designed for Sana's morning triage loop above all.

**Day 18.** Built the workspace shell: slim command bar, findings table with sticky header and severity chips, and the inspector panel that slides in beside the table so you never lose your place. No detail pages. Context switching is the enemy.

**Day 19.** Command palette (Ctrl+K), j/k row navigation, / to search, Escape to dismiss. Skeleton loading states, focus rings that only appear for keyboard users, full reduced-motion support. Self-hosted Inter and JetBrains Mono so the CSP stays locked to 'self'.

**Day 20.** Light theme, empty states that teach instead of apologize, and the upload sheet. Typecheck clean, production build green.

## Week 4: polish, docs, and the potholes

**Day 21.** Local tooling fought back: this machine's application control policy refuses to run unsigned native binaries, which kills ruff and mypy locally. Moved both to CI on Linux and kept pyflakes (pure Python) as the local safety net. Documented it so nobody rediscovers this the hard way.

**Day 22.** Second pothole: the repo lives under a folder with an ampersand in the name, and cmd.exe treats & as a command separator, which breaks npm run on Windows. Workaround: invoke node binaries directly. Also documented. The environment is part of the project.

**Day 23.** CI grew up: backend lint + unit tests, frontend typecheck + build, compose validation, the dash police, and an advisory mypy job to be promoted to blocking once its findings are triaged.

**Day 24.** Diagram pass. Redrew everything with color-coded node classes, labeled every edge, added a deployment topology and an auth-flow sequence. A diagram you have to squint at is a diagram nobody reads.

**Day 25.** Documentation for humans who are not me: a developer guide (including the add-a-connector walkthrough), an operator guide (backups, upgrades, account management), and a completely jargon-free explainer with a glossary for non-technical readers.

**Day 26.** Wrote the verification runbook: every acceptance check for the walking skeleton as copy-pasteable commands, from the UI walkthrough to the RBAC denial test to the audit-trail SQL query.

**Day 27.** Review day. Reread every ADR against the code. Tightened the ingestion size limits, confirmed secret evidence handling is on the M2 critical path, and confirmed the audit log has no update or delete path anywhere in the codebase.

**Day 28.** Dry-run day. Image builds for all three app containers, compose config validation, full unit suite, frontend build. Everything green that can be green without the full stack running.

**Day 29.** Buffer day, spent exactly as intended: on the backlog for Milestone 2. Trivy, Grype, and Gitleaks connectors; fingerprint v2 with context hashing; OpenSearch-backed search; encrypted secret evidence behind a dedicated permission.

**Day 30.** Shipped the walking skeleton. A scanner report goes in; deduplicated, evidence-linked, access-controlled findings come out, in an interface that respects the person using it. Small slice, real product. On to Milestone 2.
