# 0001: Tokens are bound to a server-side session

**Status:** accepted (2026-10-08)

**Context.** Stateless JWTs could not be revoked: logout, password reset and a stolen refresh
token all left valid tokens in circulation until expiry. The code kept session records but
nothing tied tokens to them.

**Decision.** Put the session id in both tokens (`sid`). Authentication checks the session
(one cached lookup per request). Refresh tokens rotate and are stored hashed; reuse of a
rotated token revokes the session.

**Alternatives considered.** Pure stateless JWT with a deny-list (needs a store anyway and
cannot express "all sessions of user X"); opaque session cookies only (loses Bearer clients);
long-lived refresh tokens without rotation (a stolen token is valid for weeks, silently).

**Consequences.** One cache read per authenticated request; sessions must stay available
(Redis/Mongo). Revocation is immediate. A 30 s grace window tolerates parallel refreshes.
