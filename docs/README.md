# Documentation

`fastapi_boilerplate` is a production-ready, storage-agnostic FastAPI back end (MongoDB and Redis built in, any database pluggable): sign-in and
sessions, role-based access, per-user files with versions, and the safety nets a public API
needs. You add your product's resources on top. Release history: [CHANGELOG](../CHANGELOG.md).
Want to help? [CONTRIBUTING](../CONTRIBUTING.md).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagrams/system-context-dark.svg">
  <img alt="System context: clients reach one FastAPI service through an optional reverse proxy; the service uses MongoDB, Redis and file storage, and optionally Google sign-in, SMTP and observability tools." src="diagrams/system-context.svg">
</picture>

## Start here, by role

| You are… | Read first | Then |
| --- | --- | --- |
| **Deciding** whether to build on it | [For decision makers](overview/for-decision-makers.md) | [Security model](explanation/security-model.md), [Deploy](how-to/deploy.md) |
| **Building** features on it | [Getting started](tutorials/getting-started.md) | [Architecture](ARCHITECTURE.md), [Add a resource](how-to/add-a-resource.md), [API reference](reference/api.md) |
| **Running** it | [Deploy](how-to/deploy.md) | [Operations runbook](how-to/operate.md), [Configure common features](how-to/configure.md) |
| **Designing** the product's screens | [For designers](design/for-designers.md) | [Errors](reference/api.md#errors), [Account journey](design/for-designers.md#the-account-journey) |
| **Reviewing** security | [Security model](explanation/security-model.md) | [Request pipeline](ARCHITECTURE.md#the-request-pipeline), [ADRs](adr/) |

## Every document

The docs follow [Diátaxis](https://diataxis.fr): each page answers one kind of question.

**Tutorial** (learn by doing)
- [Getting started](tutorials/getting-started.md): clone to a running API, a first admin and a first upload.

**How-to guides** (do one task)
- [Add a resource](how-to/add-a-resource.md): the five places a new feature touches.
- [Bring your own database, cache or storage](how-to/write-a-backend.md): the backend contract.
- [Configure common features](how-to/configure.md): CORS, proxies, workers, S3, email, Google sign-in, observability.
- [Send webhooks](how-to/use-webhooks.md): subscriptions, signed deliveries, verifying them on the receiver.
- [Run background jobs](how-to/run-background-jobs.md): handlers, enqueueing, workers, and the dead-letter queue.
- [Generate a typed client](how-to/generate-a-client.md): TypeScript and other clients from the committed OpenAPI contract.
- [Deploy](how-to/deploy.md): the image, Docker Compose, and a production checklist.
- [Operations runbook](how-to/operate.md): probes, outages, lockouts, secrets, data resets.

**Reference** (look something up)
- [API](reference/api.md): every endpoint, its permission, pagination, idempotency and errors.
- [Configuration](CONFIGURATION.md): every setting with type and default (generated from code).
- [Data model](reference/data-model.md): collections, fields, indexes, expiry and migrations.

**Explanation** (understand why)
- [Engineering standards](STANDARDS.md): the rules every change, human or AI, must meet.
- [For decision makers](overview/for-decision-makers.md): business value, use cases, cost, scope.
- [Architecture](ARCHITECTURE.md): layers, wiring, the request pipeline, RBAC, files, resilience.
- [Security model](explanation/security-model.md): threats and the control that answers each.
- [For designers](design/for-designers.md): what the API means for screens, states and copy.
- [Architecture decision records](adr/): the decisions, and the options they rejected.

## Diagrams

Nineteen diagrams, one idea each, in light and dark. Open the `.html` file for the full page;
the `.svg` is what the docs embed. They are rebuilt from [`diagrams/src`](diagrams/src/build.py).

| Diagram | For | Shown in |
| --- | --- | --- |
| [System context](diagrams/system-context.html) | decision makers | [here](#documentation), [decision makers](overview/for-decision-makers.md) |
| [What you get](diagrams/what-you-get.html) | decision makers | [decision makers](overview/for-decision-makers.md) |
| [Deployment](diagrams/deployment.html) | operators | [deploy](how-to/deploy.md) |
| [Configuration layers](diagrams/config-layers.html) | operators, developers | [configure](how-to/configure.md) |
| [Cache outage states](diagrams/cache-outage.html) | operators, SRE | [runbook](how-to/operate.md#redis-is-down) |
| [Code layers](diagrams/code-layers.html) | developers | [architecture](ARCHITECTURE.md#layers) |
| [Request pipeline](diagrams/request-pipeline.html) | developers, security | [architecture](ARCHITECTURE.md#the-request-pipeline) |
| [Auth sequence](diagrams/auth-sequence.html) | developers, security | [security model](explanation/security-model.md#sessions-and-tokens) |
| [RBAC resolution](diagrams/rbac-resolution.html) | developers | [architecture](ARCHITECTURE.md#access-control) |
| [File upload](diagrams/file-upload.html) | developers | [architecture](ARCHITECTURE.md#files) |
| [Data model](diagrams/data-model.html) | developers | [data model](reference/data-model.md) |
| [Account journey](diagrams/account-journey.html) | designers, product | [for designers](design/for-designers.md#the-account-journey) |
| [Two-factor sign-in](diagrams/mfa-sign-in.html) | developers, designers, security | [security model](explanation/security-model.md#two-factor-sign-in), [for designers](design/for-designers.md) |
| [API token check](diagrams/api-token-check.html) | developers, security | [security model](explanation/security-model.md#api-tokens) |
| [Audit trail](diagrams/audit-trail.html) | operators, auditors, security | [security model](explanation/security-model.md#audit-trail) |
| [Security data](diagrams/security-data.html) | developers, security | [data model](reference/data-model.md) |
| [Job lifecycle](diagrams/job-lifecycle.html) | developers, operators | [background jobs](how-to/run-background-jobs.md), [architecture](ARCHITECTURE.md#background-jobs) |
| [Backend contract](diagrams/backend-contract.html) | developers, decision makers | [write a backend](how-to/write-a-backend.md), [architecture](ARCHITECTURE.md#bring-your-own-backend) |
| [CI pipeline](diagrams/ci-pipeline.html) | contributors, reviewers | [CONTRIBUTING](../CONTRIBUTING.md#documentation) |
