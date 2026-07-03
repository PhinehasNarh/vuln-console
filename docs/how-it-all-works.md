# How It All Works

A plain-language tour of the whole system: every tool, every moving part, and how they fit together. If you are new here, read this top to bottom once. By the end you should be able to picture what happens to a scan report from the moment someone uploads it, and know the name and job of every box in the diagram. No prior experience with these specific tools is assumed.

The golden rule to keep in your head: **this platform takes messy security scanner output and turns it into one clean, deduplicated, prioritized to-do list that people actually act on.** Everything below serves that one job.

---

## 1. The whole thing in one breath

A developer or a CI pipeline uploads a scanner report (a JSON or SARIF file). The system stores the original file untouched, reads it, and converts each issue into a standard shape called a **finding**. It removes duplicates (five scanners reporting the same bug become one finding), gives each finding a deadline based on how severe it is, lets a human assign an owner, and pings Slack, Teams, or email when something needs attention. People browse and triage all of this in a fast web app.

That is the entire product. The rest of this document is just naming the parts that make it happen and explaining why each one exists.

---

## 2. Follow one scan through the system

Let's trace a single upload. Don't worry about the tool names yet; they are all explained in section 4. Just watch the flow.

1. **You upload `trivy-report.json`** in the web app (or a CI job POSTs it to the API).
2. The **API** checks you are allowed to do this, then saves the raw file into **object storage** (think of it as a private, unlimited hard drive for files) so the original is never lost.
3. The API writes a row in the **database** saying "scan received," and drops a little note onto a **message queue**: "hey, there's a new scan to process."
4. A separate program, the **worker**, is subscribed to that queue. It picks up the note, fetches the file back from object storage, and runs the matching **connector** (a small parser that knows Trivy's format) to read every issue out of it.
5. For each issue, the worker computes a **fingerprint**, a short signature built from the vulnerability id, the package, and the location. If a finding with that fingerprint already exists, this is the *same* real issue seen again, so it just links the new evidence to the existing finding. If not, it creates a new finding. **This is how duplicates disappear.**
6. When a finding is created, the worker sets its **SLA due date** from the severity (a critical is due in 3 days, a low in 90).
7. Now the finding shows up in the web app. A security engineer opens it, reads the details, and **assigns an owner**. That assignment fires an event; the worker sees it and sends a **Slack/Teams/email** message to say "you now own this."
8. Time passes. A background loop in the worker notices a finding is past its due date and nobody closed it, so it fires an **SLA breach** event, which again becomes a notification.

That is the beating heart of the platform. Two programs (API and worker), a database, a file store, and a message queue, with a web app on top. Everything else is either one of those pieces explained in detail, or a supporting service that makes running it pleasant.

---

## 3. The two mental models a veteran carries

Before the cast list, internalize these two pictures. They explain 90% of the design decisions.

**Model A: "Write on the API, work on the worker."**
Anything a human triggers and waits for (log in, list findings, upload a file, assign an owner) happens in the **API**, which answers quickly. Anything slow, heavy, or triggered by an event (parsing a big file, sending emails, scanning for breaches) happens in the **worker**, which nobody waits on. They are the *same codebase* started two different ways. This split is why the app always feels fast even when it is doing heavy lifting.

**Model B: "Facts in Postgres, files in MinIO, messages in NATS, speed in Redis, search in OpenSearch."**
Each storage system has exactly one job, and we never ask it to do another one's job. When you wonder "where does X live," this sentence answers it.

---

## 4. Meet the cast (what each tool is, and its job here)

For each tool: what it is in plain terms, and the specific job it does for us. You do not need to memorize these; you need to recognize them.

### The two programs we wrote

- **The API (FastAPI, Python).** A web server that answers requests over HTTP. When the web app or a CI job asks "log me in," "give me the findings," or "assign this to Marco," the API is what answers. FastAPI is the Python framework we built it with; its selling point is that it checks every incoming request against a strict shape and auto-generates documentation. Job here: the front door for everything a human or pipeline does.

- **The worker (Python, same codebase).** A program with no web server that sits and waits for messages on the queue, then does the slow work: parsing uploads, matching duplicates, sending notifications, and periodically scanning for overdue findings. Job here: everything that shouldn't make a user wait.

### Where things are stored

- **PostgreSQL ("Postgres").** A relational database: the classic "tables with rows and columns" store, extremely reliable, with real guarantees that your data stays consistent. This is our **system of record** (the source of truth). Users, findings, assignments, audit logs, the deadline on each finding: all here. Job here: hold every fact the platform reasons about.

- **MinIO.** A file store that behaves exactly like Amazon S3 but runs on your own machine. It holds big blobs of data by key, like a giant key-to-file dictionary. Job here: keep every uploaded scan report in its original bytes, forever, so we can re-read or re-process it later and never lose the source.

- **Redis.** An in-memory data store, meaning it keeps things in RAM so reads and writes are almost instant. It forgets easily and that is fine; it is for fast, short-lived data. Job here: rate limiting (e.g. "no more than 10 login attempts a minute") and caching.

- **OpenSearch.** A search engine: the technology behind fast full-text search and analytics over huge piles of data. It is in the stack, ready, but not yet wired into features (that lands with the search milestone). Job here (soon): let you search findings by any field and power dashboards. For now it just sits there; if it is unhealthy it does not affect anything.

- **NATS (with JetStream).** A message queue / event bus: a tiny, fast post office. One program drops a message addressed to a subject like `ingestion.scan.received`; other programs subscribed to that subject receive it. JetStream is the part that makes messages durable (they survive a restart and can be replayed). Job here: let the API hand work to the worker without the two ever talking directly, and let features react to events ("a finding was assigned") without being bolted onto each other.

### The web app

- **React + TypeScript + Vite.** React is the library for building interactive web interfaces out of reusable components. TypeScript is JavaScript with type-checking, so mistakes are caught before the code runs. Vite is the build tool that bundles it all into the fast static files a browser loads. Job here: the screens you click through, the findings table, the detail panel, the assign button.

- **nginx.** A very fast, very boring web server whose job is to hand static files (the built React app) to your browser. In our setup it also **proxies** requests: when the app asks for `/api/...`, nginx quietly forwards that to the API program. Job here: serve the web app and route its API calls, so the whole thing works from one address.

### The edge and the watchtower

- **Traefik.** A reverse proxy: the single doorway that sits in front of everything and routes incoming web traffic to the right internal service, while adding TLS (the padlock in the browser) and security headers. Job here: be the one exposed entry point in production, so nothing else has to face the open network.

- **Prometheus.** A monitoring system that regularly asks each service "how are you doing? how many requests, how much memory?" and stores the numbers over time. Job here: collect metrics so we can see the system's health and history.

- **Grafana.** A dashboard tool that draws graphs from the numbers Prometheus collects. Job here: turn those metrics into charts a human can glance at.

### The tools that keep the code honest

These do not run in production; they run while we develop and in CI (the automated checks on every push).

- **Ruff.** A linter and formatter: it reads the Python code and flags mistakes, unused imports, and style violations, near-instantly. Job here: keep the code clean and consistent so nobody argues about style.
- **mypy.** A type checker: it reads the type annotations in the Python code and proves that, say, we never pass a number where a string is expected, without running anything. Job here: catch a whole class of bugs before they exist.
- **pytest.** The test runner: it executes our automated tests and reports pass/fail. Job here: prove the logic works, and keep it working as we change things.
- **import-linter.** A rule enforcer that fails the build if one part of the code imports another part it is not allowed to. Job here: keep the module boundaries (section 6) from eroding over time.
- **Alembic.** A database migration tool: it applies versioned, ordered changes to the database schema (add a column, create a table) so every environment's database matches the code. Job here: evolve the database safely; each change is a numbered script that can be applied or rolled back.

### The languages and runtimes underneath

- **Python 3.12.** The language the backend is written in. Chosen because the security world's file formats and tools all have great Python support, and because it has first-class libraries for talking to AI models later.
- **Node.js.** The runtime that *builds* the frontend (it runs Vite and TypeScript during the build). The browser runs the *result*; Node is only needed at build time.

---

## 5. What Docker is doing (and why nothing is installed on your machine)

You may have noticed you never installed Postgres, Redis, or nginx. That is **Docker**.

- **A container** is a lightweight, isolated box that holds one program plus everything it needs to run (its exact version of Python, its libraries, its config), so it runs identically on your laptop, a teammate's laptop, or a server. Think "a shipping container for software": sealed, standardized, portable.
- **An image** is the frozen blueprint a container is started from. We *build* an image for the API and worker (from `backend/Dockerfile`) and one for the frontend (from `frontend/Dockerfile`). Everything else (Postgres, Redis, MinIO, and so on) uses an official image someone else published.
- **A volume** is a container's permanent storage. Containers are disposable; delete one and it is gone. A volume is where the data (the actual Postgres database files, the MinIO objects) survives that. This is why `docker compose down` stops everything but your findings are still there next time, and why adding `-v` (which deletes volumes) wipes the slate.
- **A network** is the private lane containers use to talk to each other by name. Inside the stack, the API reaches Postgres at the address `postgres`, not some IP. We use two: an `edge` lane for traffic coming in from outside, and an `internal` lane for the databases, which never face the outside world.

**Docker Compose** is the conductor. One file, `deploy/compose/docker-compose.yml`, lists every service (its image, its settings, its volumes, what it depends on), and `docker compose up` starts the whole orchestra with one command in the right order (databases first, then the API which waits for them to be healthy, then the worker which waits for the API). This is why "clone the repo and run one command" gives you the entire working platform.

So the mental picture: about a dozen containers, each running one tool from the cast list, wired together on private networks by Compose, with their real data tucked away in volumes.

---

## 6. How the Python code is organized (the part that ages well)

Open `backend/src/vulnconsole/` and you will see three big folders. This structure is deliberate and worth understanding, because it is what lets the code grow for years without turning into spaghetti.

- **`contexts/`** holds the **bounded contexts**: self-contained slices of the business, each owning one area. `identity` (users, login, roles), `ingestion` (uploads and parsing), `normalization` (findings, deduplication, SLA, assignment), `notifications` (Slack/Teams/email), and a few more scaffolded for later. Think of each context as a small team that owns its own tables and its own rules.

- **`shared/`** is the **shared kernel**: the small set of things every context needs and that belong to no single one, like the database connection, the settings, the event envelope, and the login-token helpers. It is kept deliberately tiny.

- **`platform/`** holds the **composition roots**: `api.py` (starts the FastAPI web server), `worker.py` (starts the event consumers and the SLA loop), and `cli.py` (one-off commands like "create a user"). These are the only files allowed to reach across every context and wire them together. Remember Model A: **`api.py` and `worker.py` run the same contexts, just pressed into service differently.**

Inside each context, the code is split into layers that always mean the same thing:

- **`domain/`** is the pure business core: the data shapes and rules (for example, the SLA policy that maps a severity to a deadline). No web, no database plumbing, just the logic. It is the most valuable and most testable code.
- **`application/`** is the use cases: "assign this finding to this owner," "normalize this scan." It orchestrates the domain and the database. This layer is a context's public surface; other contexts are allowed to call it.
- **`infrastructure/`** is the plumbing to the outside world: talking to MinIO, sending an HTTP request to Slack.
- **`api/`** is the HTTP layer: the URL routes that turn a web request into an application call.

**The one rule that keeps it clean:** a context may talk to another context only through its `application` layer or through events; it must never reach into another context's `domain` or `infrastructure`. This is not a suggestion; `import-linter` fails the build if anyone breaks it. Why care? Because it means each context stays independently understandable and, the day we need to, any one of them can be lifted out into its own separately-running service with almost no rewrite. The boundaries are already drawn.

---

## 7. How the pieces actually talk

Four kinds of conversation happen, and each medium is chosen on purpose:

- **HTTP (request and immediate answer).** Browser to API, CI to API, nginx to API. Used when someone is waiting for a reply right now.
- **SQL (reliable read and write).** API and worker to Postgres. Used for every fact that must be correct and durable.
- **Events (fire and react later).** API and worker to each other, through NATS. The publisher does not know or care who listens. Used to connect features without gluing them together, so adding "also open a Jira ticket on breach" later means adding one more listener, touching nothing that exists.
- **Object get/put (big files).** API and worker to MinIO. Used for the raw uploads, which are too big and too opaque for a database row.

A veteran reads a new feature request and immediately sorts it into these lanes: "this is a user action, so an API route; it needs to store a file, so MinIO; and it should notify people, so it emits an event the notifications context already listens for."

---

## 8. Two concrete walkthroughs

**Uploading a scan** (the write-then-work pattern):
API receives the file → validates and stores it in MinIO → writes a `Scan` row in Postgres → publishes `ingestion.scan.received` to NATS → returns "accepted" to you immediately. Meanwhile the worker consumes that event → parses the file with the right connector → writes findings to Postgres (deduping by fingerprint) → publishes `normalization.finding.created`. You never waited for any of the slow part.

**Assigning an owner** (the event-to-notification pattern):
API receives `PUT /findings/{id}/assignment` → checks your permission → updates the finding's owner in Postgres → writes an audit record in the same transaction → publishes `triage.finding.assigned`. The worker consumes that event → looks up the finding → composes a message → sends it to every configured channel (Slack, Teams, email) and records each send in the notifications table. If no channel is configured, it still records the notification so there is always an audit trail.

Notice the shape is the same both times: **the API does the small, fast, must-be-correct part and hands off; the worker does the rest by reacting to an event.** Once you see that pattern, the whole system stops being a pile of tools and becomes one coherent machine.

---

## 9. If you remember only five things

1. **API = fast user actions; worker = slow and event-driven work.** Same code, two entry points.
2. **Postgres is the truth; MinIO holds files; NATS carries events; Redis is for speed; OpenSearch is for search.** One job each.
3. **A finding is the deduplicated unit of work, and the fingerprint is what collapses duplicates.** Everything (SLA, ownership, notifications) hangs off the finding.
4. **Docker containers make every tool run identically everywhere; Compose starts them all together; volumes keep the data.**
5. **Contexts own their area and only talk through published surfaces and events, and a linter enforces it.** That discipline is why this can grow.

Read the [architecture overview](architecture/overview.md) next for the diagrams, or the [developer guide](developer-guide.md) to start changing code. Welcome aboard.
