# For designers

The service has no screens of its own ([ADR 0002](../adr/0002-api-only.md)): every screen is
designed in the product that consumes it. This page translates the API into what a designer
needs: the flows, the states each screen must cover, and the copy rules that security imposes.

## The account journey

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../diagrams/account-journey-dark.svg">
  <img alt="Account journey: sign up and sign in feel good, everyday use stays signed in, the low point is a lockout or forgotten password, and recovery by email restores confidence." src="../diagrams/account-journey.svg">
</picture>

The low point is deliberate on the server's side: after five wrong passwords the account locks for
15 minutes, but the API answers exactly as it does for a typo, so that attackers learn nothing.
The product has to make that moment bearable without contradicting it.

## Screens and the states they need

| Screen | Endpoint | States to design |
| --- | --- | --- |
| Sign up | `POST /auth/register` | Password rules shown **before** the first attempt (8+ characters, upper, lower, digit, symbol by default); duplicate username or email (400 with a message); success. |
| Sign in | `POST /auth/login` | One generic error ("Username or password is incorrect"); "remember me" (30 days instead of 7); too many attempts (429 with `Retry-After`). |
| Forgot password | `POST /auth/reset-password-request` | Always the same confirmation, whether or not the email exists. |
| Reset password | `POST /auth/reset-password-confirm` | Expired or used link (400); password rules; success, which also signs out every device. |
| Signed-in shell | any | Session refresh is silent; only a real 401 should send the user to sign in. |
| Profile | `GET`/`PATCH /auth/me` | First and last name. |
| Change password | `POST /auth/change-password` | Wrong current password (403); success says how many other devices were signed out. |
| Devices | `/sessions/active` | Device, browser, last used, "this device"; sign out one or all. |
| Files | `/files/...` | Empty state; upload progress; type not allowed; too large; quota full; versions history; tags; soft-deleted. |
| Spreadsheet | `/files/{id}/spreadsheet/...` | Sheet tabs; save creates a new version (offer "view previous"); the last sheet cannot be deleted. |
| Admin: users | `/users` | Paged list with status filter; suspend/reactivate (suspending signs the person out everywhere); admins cannot disable themselves. |

## Turning errors into states

Errors arrive as [problem documents](../reference/api.md#errors) with `status`, `detail` and a
`code`. Map by status; show `detail` only where noted (it is written for people, but may be
technical).

| Status | Show | Notes |
| --- | --- | --- |
| 400 | `detail`, next to the field it concerns | Password policy, duplicate email, unsupported file type, quota. |
| 401 | Send to sign-in, keep the user's place | After a silent refresh failed. |
| 403 | "You don't have access to this" | Better: hide the control. The login response lists the user's `permissions`. |
| 404 | "Not found" | Also what another user's file looks like; never imply it exists. |
| 409 | "Still working on it, try again in a moment" | Same request already in progress, or an incomplete chunked upload. |
| 413 | "This file is larger than 100 MB" | Use the configured limit. |
| 422 | Field errors from `errors[].loc` | Malformed input; prevent with client-side validation. |
| 429 | "Too many attempts. Try again in N seconds" | Count down from `Retry-After`. |
| 503 | "Temporarily unavailable, retrying…" | Retry automatically with backoff. |
| 500 | Generic apology + the `X-Request-ID` value | So support can find the request. |

## Patterns the API expects

- **Retry buttons are safe** when the client sends an `Idempotency-Key` header (a random id per
  user action, reused on retry). A second click replays the first result instead of creating a
  duplicate. Design retry affordances freely for uploads and edits.
- **Large uploads** use chunks: `POST /files/upload/chunk` answers `chunks_received` of
  `total_chunks`, which is the progress bar. Chunks may arrive in any order and be retried.
- **Lists are paged** (`page`, `page_size` up to 200, `total`, `has_next`): design pagination or
  "load more", not infinite unbounded lists.
- **Downloads** always arrive as attachments (never rendered in the browser), so a preview must
  be built from thumbnails (150, 300, 600 px for images) or spreadsheet data.
- **Every edit is a version.** Uploading to an existing file or editing a spreadsheet keeps the
  previous version; a history view costs nothing on the server.

## Copy rules from security

- Never confirm whether an account or email exists on sign-in or password reset. (Sign-up does
  say when a username or email is taken: the usual trade-off for a usable registration form.)
- Never say "your account is locked": say "Try again later, or reset your password".
- After a password reset or change, tell the user other devices were signed out.
- Explain password rules up front; the server message is the fallback, not the design.
