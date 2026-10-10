# Contributing

Thank you for helping. Every contribution counts: a typo fix, a clearer sentence, a test for
an edge case, a new storage backend. This guide gets you from clone to a merged pull request.

## Ways to help

- **Report a bug** or **suggest a feature** with the
  [issue templates](https://github.com/AadeshGurav/Fast-API-Boiler-Plate/issues/new/choose).
- **Improve the docs.** If something confused you, it will confuse the next person.
- **Pick an issue** labelled `good first issue` or `help wanted`.
- **Add a backend:** a `CacheInterface`, `DatabaseInterface` or `StorageInterface`
  implementation, or a new OAuth provider.
- **Security issues** go privately through [SECURITY.md](SECURITY.md), never as public issues.

## Set up (about ten minutes)

```bash
git clone https://github.com/AadeshGurav/Fast-API-Boiler-Plate.git
cd Fast-API-Boiler-Plate
make setup       # venv, dependencies, .env, config.local.toml
make test        # 197 tests, no services needed
make up && make run   # optional: the real API against Docker MongoDB and Redis
pre-commit install    # optional: ruff before every commit
```

[Getting started](docs/tutorials/getting-started.md) walks through the running API;
[Architecture](docs/ARCHITECTURE.md) explains how it fits together.

## Workflow

1. Open or comment on an issue first for anything larger than a small fix, so effort is not
   duplicated and the approach is agreed.
2. Branch from `develop` with a prefix: `feature/…`, `fix/…`, `docs/…`, `arch/…`.
3. Make the change, with tests and docs in the same pull request.
4. Run `make fmt && make lint && make test` (CI runs the same).
5. Open a pull request into `develop` and fill in the template.

### Commits

Small, focused commits in the [Conventional Commits](https://www.conventionalcommits.org/)
style, written for the next reader: what changed and why.

```text
fix(files): reject chunk numbers above total_chunks

A client could stage chunk 9 of 2 and grow storage beyond total_size.
```

## Conventions

- **Layers:** routes parse and respond; services hold rules; the data layer holds queries and
  cache keys; backends know only their engine. See [Layers](docs/ARCHITECTURE.md#layers).
- **One way to do things.** Reuse the existing pattern (follow `files` for a resource,
  `DataService.update` for edits, `HTTPException` for client errors) rather than adding a second one.
- **Configuration:** every new setting is a field in `app/settings.py` with a type, a default
  and a description; run `make config-docs` (a test fails if `docs/CONFIGURATION.md` is stale).
- **Data changes:** append a migration in `services/data/migrations.py`; never edit a released one.
- **Errors** are specific and never leak internals; responses are problem+json.
- **Style:** Ruff (format + lint, 100 columns). Comments explain *why*, not *what*.
- **Dependencies** are a decision: prefer the standard library or what is already installed,
  pin versions in `requirements*.txt`, and say why in the pull request.

## Tests

- New logic gets tests, including the failure branches, not only the happy path.
- A bug fix gets a regression test.
- Test behaviour through the real app where possible: the `env` fixture in `tests/conftest.py`
  builds the full application with in-memory MongoDB and Redis stand-ins.
- Tests must be fast and independent. A flaky test is fixed or removed, never re-run.

## Documentation

Docs change in the same pull request as the behaviour they describe. The docs follow
[Diátaxis](https://diataxis.fr): tutorial, how-to, reference, explanation; see the
[hub](docs/README.md). Significant design decisions get an ADR in `docs/adr/` (context,
decision, alternatives considered, consequences).

Diagrams are built from `docs/diagrams/src/` with the
[diagram-design](https://github.com/cathrynlavery/diagram-design) skill installed:
`python3 docs/diagrams/src/build.py` regenerates both light and dark versions.

## Pull request checklist

- [ ] Tests added or updated; `make test` passes
- [ ] `make lint` passes
- [ ] Docs updated (and `make config-docs` if settings changed)
- [ ] `CHANGELOG.md` has an entry under *Unreleased* for user-visible changes
- [ ] No secrets, credentials or personal data in code, tests or logs

## Releases

Maintainers move *Unreleased* entries in `CHANGELOG.md` under a new version, bump
`app_version` in `app/settings.py`, tag `vX.Y.Z` on `develop` (the default branch), and publish a
GitHub release.

## Code of Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
