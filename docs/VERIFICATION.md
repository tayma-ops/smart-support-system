# Verification record

## Real screenshots and focused browser review — 1 November 2026

Six real Chromium captures are now included in the [README gallery](../README.md#screenshots): employee dashboard, ticket list, ticket details, an actual AI suggestion copied into the unsent reply composer, Arabic RTL dashboard and the mobile customer ticket view. Only the existing synthetic demo data and genuine saved local-model analysis were used. No mocked responses, injected UI content or generated images were used.

The final PNGs were visually inspected. English/Arabic dashboards were checked at 1440, 1024, 768, 760, 390 and 320 pixels, and the RTL mobile ticket list was checked. One CSS containment rule fixes tablet overflow from a screen-reader label inside a scrollable table. No backend, template workflow, permission, data model or API code changed. The mobile menu opened, closed with Escape and restored focus; staff AI/internal-note controls were absent for the customer; an unrelated customer received 404. Clicking **Use draft in reply** populated the composer without submitting or changing the API record. No JavaScript exceptions or HTTP 5xx responses were observed.

Existing domain records and password hashes were preserved; ordinary demo sign-ins updated login timestamps and created browser sessions. The backend suite was not rerun for these screenshot/documentation/CSS changes. This focused review supersedes the older browser-unavailable and screenshot-pending statements below. It is not an exhaustive accessibility, cross-browser or production review. [Capture details](screenshots/README.md). Private evidence: `.local/screenshot-evidence/capture-results.json`.

## Published repository and GitHub Actions

The public repository is [tayma-ops/smart-support-system](https://github.com/tayma-ops/smart-support-system), on `main`. The initial application commit is `e629738ca376b3b34397be72ff5f10c873fa6d1c`. Its [first CI run, 41319932659](https://github.com/tayma-ops/smart-support-system/actions/runs/41319932659), completed successfully on 1 November 2026:

| Job | Observed result |
| --- | --- |
| `test` | 83 PostgreSQL tests passed in 3.651 seconds; dependencies, translation compilation, lint/format checks, Django/migration checks, OpenAPI validation and static collection passed |
| Worker/SMTP integration in `test` | Real PostgreSQL → Redis → Celery no-key fallback and a synthetic notification accepted by a local SMTP sink |
| `docker` | Image build and `docker compose up --build -d --wait` passed; containerized worker round trip and full HTTP smoke workflow passed; containers cleaned up |

These results establish Linux CI and Docker development-stack execution. They supersede the earlier pre-publication statements below about Docker/remote CI being unverified. Docker was not installed on the Windows workstation. The remote CI model check uses explicit no-key behavior; real local-model inference was verified separately on Windows. Cloud inference, external mailbox delivery and public application deployment remain unverified. The later screenshot review is recorded above.

Before the first push, all 130 Git index blobs were scanned for actual local secrets, demo passwords and common private-key/token patterns. Runtime files and local data were excluded. Local evidence: `.local/staged-release-scan.json`, `.local/github-first-ci.json` and `.local/github-first-ci.log`.

## Final application completion

After the clean-install review below, three regression tests were added for browser claiming: an employee's own ticket in another department does not expose a claim control, eligible claiming succeeds, and a validation race displays a message instead of raising HTTP 500. The corresponding permission helper, view and template were fixed without changing domain visibility or assignment services.

**All 83 PostgreSQL tests passed without skips; the final pre-repository run took 6.112 seconds.** SQLite discovered 83, passed 81 and skipped the two PostgreSQL concurrency tests in 8.467 seconds. Django migration checks and `migrate` passed with no pending migrations; schema validation and Ruff/Black/template formatting/template lint passed.

A real staff HTTP workflow created its own users/department/ticket, waited for real local inference through Celery, confirmed zero automatic replies, claimed the ticket, posted a private note, checked owner/unrelated-user scope, explicitly submitted the generated draft with an integration review prefix, and verified the public reply through REST. It also exercised REST triage, profile role protection, resolution, customer closing and staff reopening. It cleaned up all its synthetic records. This exercised HTTP forms and APIs; it did **not** click the JavaScript draft button in a browser or claim an actual human quality review of model output.

Compose passed validation against the [official Compose Specification JSON Schema](https://raw.githubusercontent.com/compose-spec/compose-spec/main/schema/compose-spec.json). The workflow passed [actionlint 1.7.12](https://github.com/rhysd/actionlint/releases/tag/v1.7.12), using a checksum-verified Windows binary; shellcheck and pyflakes integrations were disabled. Neither static check establishes that Docker, Linux workers or GitHub Actions have run. Local evidence: `.local/staff-http-workflow.json`, `.local/delivery-config-validation.json`, `.local/actionlint.log`.

## Earlier source-only installation

The final documentation/ignore review retained the application architecture and dependencies. A source-only copy, excluding `.env`, `.local`, media, local databases and the existing virtual environment, was installed into a new Python 3.14 virtual environment. Both runtime and development requirements installed successfully and passed `pip check`. Configure-only bootstrap preserved PostgreSQL as the default. Django checks, Ruff, Black, both template checks and Arabic catalog compilation passed in that isolated copy. **All 80 PostgreSQL tests passed in 8.800 seconds**, without skips. This is a clean source-installation check, not a remote Git clone or Linux/container verification.

The live PostgreSQL connection, shared Redis cache, Celery ping, web health and local-model health were checked again. Beat continued dispatching its recovery task every minute. No new cloud inference or remote SMTP delivery is claimed. Docker and remote GitHub Actions were reviewed statically and were not executed. See [the final Arabic report](GITHUB-READINESS.ar.md).

## Earlier full-stack verification

Observed on **1 November 2026**, using Windows, Python 3.14.7, Django 6.1.2, PostgreSQL 18.6, Redis 8.10.3 and Celery 5.6.3. This record supersedes the earlier SQLite-only verification.

| Check | Observed result |
| --- | --- |
| PostgreSQL suite: `python manage.py test --settings=config.ci_settings` | **83 tests passed**, none skipped; latest run 6.112 seconds |
| SQLite suite: `python manage.py test --settings=config.test_settings` | 83 discovered; 81 passed and 2 PostgreSQL-only tests skipped; latest run 8.467 seconds |
| Browser auth and admin regressions | Login/admin/registration budgets, cache eviction race, admin CSRF, password change/reset and deleted-account refresh tested |
| PostgreSQL concurrent ticket assignment | One employee claims the ticket; the competing claim is denied |
| PostgreSQL concurrent AI analysis | One provider call; the second task observes the active lease |
| `python manage.py check` | Passed; no issues |
| `python manage.py makemigrations --check --dry-run` | Passed; no changes detected |
| PostgreSQL migrations | Applied successfully |
| Fresh PostgreSQL database | All migrations applied from empty state; domain tables empty as expected; temporary database removed |
| Backup restoration | Pre-review custom-format dump restored into a separate database; original domain row counts matched; temporary database removed |
| Original data preservation after review | All original domain row digests and password-hash digests matched the pre-review baseline |
| OpenAPI validation with `--fail-on-warn` | Passed without schema warnings/errors |
| Static collection | Passed; assets collected and fingerprinted |
| Python compilation | Passed for application, scripts and tests |
| Ruff / Black / djLint formatting | Passed |
| djLint Django template lint | 27 templates checked, zero errors; no lint rules suppressed |
| JavaScript syntax | Parsed successfully with Tree-sitter; no browser execution claimed |
| Configure-only bootstrap | Generated PostgreSQL defaults without site packages; second invocation preserved the existing private configuration |
| `python -m pip check` | Passed; no broken requirements |
| `check --deploy --fail-level WARNING` under production security flags | Passed; no issues |
| Real HTTP workflow in English | Passed: login, CSRF, creation, upload, reply, scoped API, private download, close, metrics, logout |
| Real HTTP workflow in Arabic | Passed with translated HTML and RTL direction; same workflow and permissions |
| PostgreSQL -> Redis -> Celery no-key round trip | Passed with explicit AI-disabled result |
| PostgreSQL -> Redis -> Celery -> real local model | Passed; generated analysis saved, no customer reply created |
| Real SMTP protocol through a worker | Passed against a local SMTP sink using synthetic `example.invalid` recipients |
| Real model samples | Generated English and Arabic results with Qwen3-0.6B Q4_K_M through llama.cpp |
| Arabic gettext catalog | 363 translated messages compiled; language switch, forms, choices, charts and system events tested |
| SQLite -> PostgreSQL data migration | Counts and password hashes matched: 4 users, 12 tickets and 9 replies preserved |
| Original demo credentials and real AI visibility | All four original demo accounts logged in after migration; staff saw real analysis, the owner saw no draft, and another customer received 404 |
| Compose/CI YAML structure | Parsed and checked; execution of Docker remains unverified |
| Git exclusions and local-secret scan | Local databases, binaries, model weights, credentials, caches and logs excluded; generated secret values absent from deliverable source |
| Deliverable review | 129 source/documentation files; no broken local Markdown links; actual local signing/database values and all four demo passwords absent; UTF-8/LF text |

The production settings check explicitly enabled secure cookies and HTTPS redirects with `DJANGO_DEBUG=False`. It is not a production deployment, penetration test, load test or security certification.

The final portfolio review added six regression tests, atomic browser auth budgets, a throttled admin site, explicit refresh revocation, mobile keyboard navigation improvements, template semantic corrections, GitHub documentation and a web readiness healthcheck. See [the Arabic review](PORTFOLIO-REVIEW.ar.md) for the complete change record and score. The original 74 tests were retained.

## Runtime and inference details

PostgreSQL was downloaded as a portable archive from EDB, the provider linked by the PostgreSQL Windows download page. Redis was a checksum-verified **community Windows build** from redis-windows/redis-windows, compiled from Redis source. Celery used a `solo` worker for native development. This does not establish official Windows worker support or Linux container behavior.

The local model used an official llama.cpp Windows CPU binary (build b11960) and Unsloth's Qwen3-0.6B Q4_K_M GGUF. The GGUF SHA-256 matched `ac2d97712095a558e31573f62f466a3f9d93990898b0ec79d7c974c1780d524a`. All tool binaries and weights remain under ignored `.local` paths.

Initial real model trials produced a wrong category, text in the wrong language, and a draft requesting credentials. These findings led to clearer prompts, privacy-request rejection and Arabic text checks. Revised English/Arabic samples and a real background workflow completed. The small model still produces imperfect or irrelevant advice: there was **no statistical accuracy benchmark**, and staff review remains required. Prompt wording and heuristic checks cannot guarantee output safety.

The SMTP check ran a real server on an ephemeral loopback port. It accepted a generic synthetic notification; no external mailbox was contacted. The integration helper creates a private queue, starts a temporary worker and SMTP sink, verifies the result, and cleans up its own synthetic records.

## Current local state

The app is running at `http://127.0.0.1:8000/` with **PostgreSQL and asynchronous Redis/Celery**, a single beat scheduler and a local model endpoint. The original SQLite database and an ignored pre-migration backup remain available. Demo password hashes were preserved, so the original local demo credentials still work.

Beat's minute recovery dispatch and the worker's successful handling were observed in real logs after restart. The daily token purge remains configured; no full 24-hour schedule interval was observed during this review. English/Arabic HTTP and isolated no-key/real-local-model worker/SMTP checks were rerun successfully after the authentication changes.

See `docs/LOCAL-SETUP.ar.md` for this checkout's ports, local artifacts and restart instructions. These are development processes, not installed production services.

## Remaining verification limits

- Docker execution on the original Windows workstation: not performed. Linux image/Compose execution passed in the published CI run above.
- OpenAI cloud inference: its adapter was contract-tested with mocks; no cloud key was supplied. Real local inference was verified separately.
- Delivery to an external mailbox: SMTP protocol delivery was verified locally, not with a real external provider/account.
- Full accessibility and cross-browser review: the focused Chromium review above covers the six captures and listed interactions. It does not establish every browser, 200% zoom or an exhaustive assistive-technology audit.
- Public deployment, real customer workloads and model quality/accuracy benchmarking.

## Artifacts

- `README.md`: recruiter overview and installation; `docs/ENGINEERING.md`: detailed architecture, API and operations.
- `docs/PORTFOLIO-REVIEW.ar.md`: latest Arabic portfolio audit and honest readiness score.
- `docs/screenshots/README.md`: six real PNGs, capture details and focused review results; no image files are fabricated.
- `docs/REPORT.ar.md`: Arabic delivery report, GitHub description/topics and CV examples.
- `docs/FILES.md`: deliverable source inventory.
- `.local/postgres-tests.log`, `.local/sqlite-tests.log`: actual local suite output.
- `.local/worker-stack-result.log`: most recent isolated worker/SMTP verification.
- `.local/real-ai-analysis.json`: generated results for synthetic model samples.
- `.local/migration-result.json`: record-count and password-hash preservation result.
- `.local/demo-credentials.txt`: private demo credentials; never publish.
- `.local/portfolio-checks.log`, `.local/portfolio-checks.json`: actual quality, HTTP, worker/AI/SMTP and secure-settings results.
- `.local/database-review.json`, `.local/preservation-review.json`: fresh/restore verification and unchanged original data.
- `.local/static-review.json`, `.local/cleanup-review.json`: parser/bootstrap checks and scoped cleanup record.

CI action release tags were checked against their official releases: [actions/checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) and [actions/setup-python v7.1.0](https://github.com/actions/setup-python/releases/tag/v7.1.0). This verifies tag existence, not remote workflow success.

The source has been committed and pushed to the real public `origin` above. Earlier local-only records describe the state before this publication.
