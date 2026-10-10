# Getting started

By the end of this tutorial you will have the API running on your machine against real
MongoDB and Redis, an administrator account, a normal user, and a file uploaded and listed
through the API. It takes about ten minutes.

**You need:** Python 3.11, Docker (for MongoDB and Redis), `make`, and `curl`.

## 1. Set up

```bash
git clone git@github.com:AadeshGurav/Fast-API-Boiler-Plate.git
cd Fast-API-Boiler-Plate
make setup
```

`make setup` creates `.venv`, installs dependencies, and writes two git-ignored files:

- `.env` with random database passwords, a JWT secret, and **free host ports**. If port 8000
  is busy on your machine, it picks 8001, and so on. Check `FABP_APP_PORT` in `.env`; the
  examples below use `8000`.
- `config.local.toml`, which turns on development conveniences: debug mode, interactive docs
  at `/docs`, readable logs.

## 2. Start the databases

```bash
make up        # MongoDB 8 and Redis 7 in Docker, bound to 127.0.0.1 only
```

## 3. Create the first administrator

There is no built-in admin account (a default login would be a backdoor on every
deployment). Open `config.local.toml` and uncomment the three `bootstrap_admin_*` lines:

```toml
bootstrap_admin_username = "admin"
bootstrap_admin_email = "admin@example.com"
bootstrap_admin_password = "change-me-Please1!"
```

On start-up, if there are no users yet, this account is created with the `admin` role.

## 4. Run the API

```bash
make run
```

In a second terminal, check it is ready:

```bash
API=http://127.0.0.1:8000/api/v1
curl -s $API/ready
# {"status":"ready", ... "database":{"status":"ready"...}, "cache":{"status":"ready"...}}
```

Now comment the `bootstrap_admin_*` lines out again: the admin exists, and its password should
not stay in a file.

## 5. Register and sign in

```bash
curl -s -X POST $API/auth/register -H 'Content-Type: application/json' \
  -d '{"username":"ada","email":"ada@example.com","password":"Str0ng!Passw0rd","first_name":"Ada","last_name":"Lovelace"}'
```

The reply is the new user with `"roles":["user"]`. Public registration can never pick its
own role. Sign in and keep the access token:

```bash
TOKEN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"ada","password":"Str0ng!Passw0rd"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["tokens"]["access_token"])')

curl -s $API/auth/me -H "Authorization: Bearer $TOKEN"
```

Browsers do not need the token: login also sets HttpOnly cookies, and the API refreshes them
silently. Scripts like this one use the `Authorization: Bearer` header.

## 6. Upload and list a file

```bash
echo "hello" > hello.txt
curl -s -X POST $API/files/upload -H "Authorization: Bearer $TOKEN" -F file=@hello.txt -F tags=demo
curl -s "$API/files/?page=1&page_size=10" -H "Authorization: Bearer $TOKEN"
```

The upload reply carries a `file_id` and a `download_url`. Upload the same bytes again and you
get the same `file_id` back: identical content is de-duplicated per user.

## 7. See access control at work

```bash
curl -s $API/users -H "Authorization: Bearer $TOKEN"
# {"type":"about:blank","title":"Forbidden","status":403,"detail":"Permission denied: users:read",...}

ADMIN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"change-me-Please1!"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["tokens"]["access_token"])')
curl -s "$API/users?page_size=5" -H "Authorization: Bearer $ADMIN"
```

The normal user is refused with a problem document; the admin gets a page of users. Every
endpoint needs a `<resource>:<action>` permission derived from its URL and method; roles grant
them in `config.toml`.

## 8. Explore and test

- Open `http://127.0.0.1:8000/docs` for the interactive API (debug mode only).
- `make test` runs the 197 tests; they need no running services.
- `make config` lists every effective setting and the file it came from.
- `make down` stops the databases and keeps their data; `make reset-data` deletes it.

## Where next

- Build your first feature: [add a resource](../how-to/add-a-resource.md).
- Understand what you just used: [architecture](../ARCHITECTURE.md) and
  [security model](../explanation/security-model.md).
- Every endpoint: [API reference](../reference/api.md).
