# Generate a typed client

The API's contract is committed as [`docs/reference/openapi.json`](../reference/openapi.json)
(OpenAPI 3.1). A test fails whenever the application's schema and that file disagree, so the
file is always current, and every contract change shows up in review as a diff.

## TypeScript (web and React Native)

[Hey API](https://heyapi.dev) is the generator the FastAPI documentation recommends. In your
front-end project:

```bash
npm install --save-dev @hey-api/openapi-ts
npx @hey-api/openapi-ts \
  -i https://raw.githubusercontent.com/<you>/<repo>/develop/docs/reference/openapi.json \
  -o src/client
```

Point `-i` at a local copy or at `http://127.0.0.1:8000/openapi.json` while developing. Treat
`src/client` as generated: regenerate it, never edit it. Its plugins can also emit TanStack
Query hooks and Zod schemas.

Function names are the route function names (`login_user`, `list_files`), because
`AppFactory` sets each operation's `operationId` to the function name. Renaming a route
function therefore renames a client method: the snapshot diff shows it.

### Calling the API from a browser

- Send `credentials: "include"` so the HttpOnly session cookies travel; add your origin to
  `cors_origins`.
- Every error is `application/problem+json` with a stable `code`; branch on `code`, not on
  `detail` ([errors](../reference/api.md#errors)).
- Retries of unsafe requests should carry an `Idempotency-Key` header.

## Other languages

Any OpenAPI 3.1 generator works on the same file: `openapi-python-client` for Python,
`oapi-codegen` for Go, `openapi-generator` for Kotlin or Swift.

## When you change the API

```bash
make openapi   # rewrites docs/reference/openapi.json
git diff docs/reference/openapi.json
```

Commit the regenerated file in the same change. A removed or renamed field, or a changed type,
is a breaking change and needs a new API version ([standards §4](../STANDARDS.md#4-api-contract)).
