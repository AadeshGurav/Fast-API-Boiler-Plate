# 0002: The service is API-only

**Status:** accepted (2026-10-08)

**Context.** The boilerplate shipped a demo UI (Jinja templates, 5k lines of JS/CSS, a class
registry) coupled to internals. It exposed unauthenticated writes, needed readable auth
cookies, and was the main reason auth state had to leak into the browser.

**Decision.** Remove the UI, the class store and static/template serving. Authentication
cookies are HttpOnly; clients use the JSON API.

**Alternatives considered.** Keep the demo behind `app_debug` (still needs JS-readable
tokens, still maintained against every change); move it to a separate repo (nothing depends
on it).

**Consequences.** Smaller attack surface and codebase. A front end, if wanted, is a separate
project that consumes the API.
