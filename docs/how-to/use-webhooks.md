# Send webhooks to other systems

Webhooks tell your other systems (a CRM, a data warehouse, Slack, Zapier) what happened here, as
it happens. Deliveries are background jobs: retried with backoff, and visible at
`/api/v1/admin/jobs?status=dead` if a receiver keeps failing.

## Subscribe

An administrator creates a subscription; the response is the only time the signing secret is
shown:

```bash
curl -X POST https://api.example.com/api/v1/admin/webhooks \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"url": "https://crm.example.com/hooks/fabp", "events": ["user.*", "rbac.role_assigned"]}'
```

`events` are types or patterns: `user.registered`, `user.*`, or `*` for everything. Every action
in the [audit log](../reference/api.md#administration) is published (except `webhook.*`), and
your services can publish their own:

```python
await self.webhook_service.publish("order.paid", {"order_id": order_id, "amount": amount})
```

`POST /api/v1/admin/webhooks/{id}/test` queues a `webhook.test` delivery to check the receiver.

## What the receiver gets

```http
POST /hooks/fabp
content-type: application/json
webhook-id: msg_6f1c...          (the same on every retry: de-duplicate on it)
webhook-timestamp: 1791712800
webhook-signature: v1,K5o3...

{"type":"user.registered","timestamp":"2026-10-11T09:30:00+00:00",
 "data":{"actor_id":"…","target_type":"user","target_id":"…","details":{}}}
```

Answer any 2xx within `webhooks_timeout_seconds` (10). Anything else, or no answer, is retried
up to `jobs_max_attempts` (5) times with growing delays. IP addresses and user agents are never
included.

## Verify the signature

The format is the [Standard Webhooks](https://www.standardwebhooks.com) spec, so its libraries
work (`pip install standardwebhooks`, `npm install standardwebhooks`). By hand, in Python:

```python
import base64, hashlib, hmac, time

def verify(secret: str, headers, body: bytes) -> bool:
    msg_id, ts, sig = headers["webhook-id"], headers["webhook-timestamp"], headers["webhook-signature"]
    if abs(time.time() - int(ts)) > 300:          # refuse old or replayed requests
        return False
    key = base64.b64decode(secret.removeprefix("whsec_"))
    expected = base64.b64encode(hmac.new(key, f"{msg_id}.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
    return any(hmac.compare_digest(expected, s.removeprefix("v1,")) for s in sig.split())
```

Verify against the raw body bytes, before parsing the JSON.

## Safety

Destinations must be `https` and may not resolve to private, loopback or link-local addresses,
checked when subscribing and again before every delivery. Redirects are not followed. For local
testing set `webhooks_allow_http = true` and `webhooks_allow_private_networks = true` in
`config.local.toml`, never in production.
