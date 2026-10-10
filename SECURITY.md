# Security policy

Security is the point of a boilerplate: thank you for helping keep it sound.

## Supported versions

| Version | Supported |
| --- | --- |
| 1.x | Yes |
| 0.x | No (see the [CHANGELOG](CHANGELOG.md) upgrade notes) |

## Reporting a vulnerability

**Please do not open a public issue.** Report it privately through
[GitHub private vulnerability reporting](https://github.com/AadeshGurav/Fast-API-Boiler-Plate/security/advisories/new)
with:

- what an attacker can do, and the affected endpoint, setting or module;
- steps or a minimal request to reproduce;
- the version or commit you tested.

You can expect an acknowledgement within a few days and a fix or a plan as soon as the impact is
understood. Credit is given in the advisory and the changelog unless you prefer otherwise.

## Scope

In scope: the code in this repository and its default configuration. Out of scope:
misconfiguration of a deployment (for example `app_debug` enabled in production), third-party
services, and denial of service that needs traffic beyond the documented limits.

How the service defends itself is described in the [security model](docs/explanation/security-model.md).
