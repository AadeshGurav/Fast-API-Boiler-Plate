# Engineering standards

These are the standards this project is built to. **They are binding.** A pull request is
reviewed against them, and a pull request that does not meet them is sent back or closed,
whoever or whatever wrote it. The same rules apply to code written by people and code written
by AI agents.

The short version: understand before changing, change the smallest right thing in the right
layer, prove it with tests, document it in the same change.

## 1. Before writing code

1. **Look, don't guess.** Read the parts of the codebase the change touches. Start from the
   code graph (`graphify-out/GRAPH_REPORT.md`, `graphify query`, `graphify explain`; see
   [AGENTS.md](../AGENTS.md)), then read the files it points to.
2. **Understand what is there:** the existing pattern, naming, and the decision behind it
   (the [ADRs](adr/)).
3. **Understand the request.** If an ambiguity would change the approach, ask in the issue.
4. **Plan anything non-trivial** (a change across several files, a debugging investigation,
   an architectural shift) in the issue or pull request description before implementing.
5. **Get agreement before major changes.** New dependencies, data-model changes,
   restructuring, new public API shapes: agree on them in an issue first, and record the
   decision as an ADR (context, decision, alternatives considered, consequences).

## 2. Principles

- **Simple over clever; explicit over implicit; flat over nested.** If a design is hard to
  explain in two sentences, it is probably wrong.
- **One obvious way to do it.** Reuse the existing convention; do not add a second pattern for
  something the codebase already does.
- **Errors never pass silently.** Swallowing an error must be deliberate and commented.
- **Comments explain why, not what.** The code says what it does.
- **Fix at the source.** Configuration, setup scripts and docs carry the fix; never patch a
  running instance by hand.
- **Delete what you stop using** in the same change: dead code, unused dependencies, orphaned
  settings.

## 3. Architecture

- **Modular monolith, layered.** Routes → services → data layer → backend services → engines
  ([Layers](ARCHITECTURE.md#layers)). Each layer calls only the one below.
  - Routes parse, call one service, and shape the reply. No business logic.
  - Services hold the rules. They never import a database or cache driver.
  - The data layer (`DataService` + `*_ops.py`) holds queries and cache keys. No domain rules.
  - Engines (`database/`, `cache/`, `storage/`) know only their technology.
- **Storage stays swappable.** No driver (`motor`, `pymongo`, `redis`, `boto3`) is imported
  outside its backend module. New queries use only the documented
  [filter vocabulary](how-to/write-a-backend.md#the-filter-vocabulary); extending it means
  updating every backend and that document.
- **Patterns answer a failure or a change, not a fashion.** Before adding one, state what it
  protects against and what it costs. No CQRS for a CRUD form, no message broker for two
  functions in one process.
- **Resilience on every outbound call:** a timeout always; retries only for transient errors,
  with backoff; degrade or fail clearly when a dependency is down, never hang.
- **Unsafe operations are safe to retry.** Anything that creates, moves or sends works with
  `Idempotency-Key`.
- **Transactions have one boundary** per operation; a write path that can partly fail cleans
  up after itself (see how `FileService.upload_stream` removes stored bytes when its record fails).

## 4. API contract

- Resources are nouns; HTTP methods are the verbs. Accurate status codes; never `200` with an
  error in the body.
- Errors are RFC 9457 `application/problem+json` with a stable `code`; no internals, no stack
  traces, no echoed input.
- Everything lives under `/api/v1`. Breaking changes (removed or renamed fields, changed types)
  need a new version; added optional fields and new endpoints do not.
- Every collection endpoint is paged (`page`, `page_size` ≤ 200, `total`, `has_next`). One that
  can grow without bound (per-user files, logs, queues) also offers `cursor` / `next_cursor`
  (`app/services/data/cursor.py`); small bounded ones (users, tokens) need only pages.
- Every route's permission (`<resource>:<action>`) is granted to a role in `config.toml`.
- Ownership is checked in the service; other users' resources answer 404.
- The OpenAPI schema (`/openapi.json`) is the contract: routes declare `response_model` and
  status codes, and [the API reference](reference/api.md) changes with them. The schema is committed
  as `docs/reference/openapi.json`; run `make openapi` and commit the diff (a test enforces it).

## 5. Code

- **Small, single-purpose functions**; dependencies passed in, no globals or hidden state.
- **Intent-revealing names**, verb-noun for functions (`resolve_user_permissions`). Not `data`,
  `info`, `util`, `helper`, `manager` on their own.
- **File size is a signal:** past roughly 300 lines a module usually does two jobs; split along
  the natural seam. A few existing modules are larger: do not grow them, split when you touch them.
- **Typed:** annotations on public functions; Pydantic models at the boundary.
- **Async all the way:** blocking work (hashing, image and spreadsheet processing, boto3, SMTP)
  runs in a worker thread, never on the event loop.

## 6. Tests

- New logic gets tests, including every decision branch and failure path, not only the happy path.
- Every bug fix gets a regression test that fails without the fix.
- Test behaviour, not implementation: prefer the real app through the `env` fixture over mocks.
- Tests are fast and independent; no reliance on order, network or local files outside `tmp_path`.
- A flaky test is fixed or removed, never re-run until green.
- `make fuzz` (Schemathesis) must stay green: no operation may answer 5xx or anything the OpenAPI
  contract does not declare. A new route that answers a new status declares it.

## 7. Security and configuration

- **No secrets in code, tests, logs or examples.** Secrets come from the environment or
  `config.secrets.toml`; settings that hold them are `repr=False`.
- **Configuration lives in config:** limits, thresholds, timeouts, feature switches are
  settings in `app/settings.py` with a type, a default and a description; run
  `make config-docs`.
- **Validate at the boundary** with Pydantic; services can trust their inputs.
- **Least privilege:** new endpoints are authenticated and permission-checked by default;
  public or admin-only paths are an explicit, reviewed choice.
- **Security decisions read the database, not the cache.**
- Never log payloads that may hold passwords, tokens or personal data.

## 8. Errors and observability

- Errors say what went wrong and what to do next, in logs and in `detail`.
- Log lines carry identifiers (user id, request id, entity id) in `extra`, not only prose.
- The request id travels through every log line of a request.

## 9. Dependencies

- Every new dependency is a decision: prefer the standard library or what is installed.
- Pin exact versions in `requirements*.txt`; upgrade deliberately after reading the changelog.
- Optional integrations stay optional (`requirements-s3.txt`, settings that default to off).

## 10. Style, docs and commits

- `make fmt && make lint` (Ruff, 100 columns) must pass; fix warnings, do not suppress them
  without a commented reason.
- **Docs change in the same pull request as behaviour.** Follow [Diátaxis](https://diataxis.fr):
  tutorial, how-to, reference, explanation. Update diagrams (`docs/diagrams/src`) when the
  structure they show changes.
- **Small, coherent commits** in Conventional Commits style (`feat:`, `fix:`, `docs:`,
  `refactor:`, `test:`, `chore:`), each message saying what changed and why.
- User-visible changes get a `CHANGELOG.md` entry under *Unreleased*.
- Branches: `feature/…`, `fix/…`, `docs/…`, `arch/…`, from and into `develop`.

## 11. Definition of done

A change is done only when all of these hold:

1. It works end to end, including failure paths, and `make test` passes.
2. `make lint` passes.
3. Errors are handled explicitly and surface as problem+json.
4. New values are settings, not constants; `docs/CONFIGURATION.md` is regenerated.
5. New or changed endpoints meet [§4](#4-api-contract) and the API reference is updated.
6. Docs, diagrams and `CHANGELOG.md` are updated.
7. The code graph is current (`make graph`, or let the post-commit hook do it).
8. Commits are small and well described.

## 12. AI-written contributions

AI agents are welcome contributors and are held to every rule above, plus these:

- Read [AGENTS.md](../AGENTS.md) and navigate with the code graph before editing.
- Say in the pull request that it was AI-assisted, and include the real output of
  `make lint` and `make test`. Claims without evidence are not accepted.
- Do not invent APIs, settings or files: everything referenced must exist in the code graph or
  be added in the same change.
- Keep the change to what the issue asks; unrelated refactors go in their own pull request.

## When standards conflict with a deadline

Cut scope, not quality: never ship lost data or a security hole; fail visibly rather than
silently; ship a smaller thing done properly; write down what was cut and why, in the pull
request or an issue.
