# Errors, retries and limits

Every error is JSON:

```json
{ "code": "client_ref_conflict", "message": "…", "retryable": false, "doc_url": "https://platform.safecreative.org/docs/errors#client_ref_conflict" }
```
```json
{ "code": "validation_error", "message": "2 invalid fields (client_ref, hash): see errors", "retryable": false,
  "doc_url": "https://platform.safecreative.org/docs/errors#validation_error",
  "errors": [ { "field": "client_ref", "message": "client_ref is required" },
              { "field": "hash", "message": "hash must be a 64-character hex digest for sha-256" } ] }
```

`code` is stable: branch on it. `message` is localized (English by default, Spanish with `Accept-Language: es`) and may
change. `retryable` is `true` on `429`, `503` and other `5xx` (repeat the same request, same `client_ref`) and `false`
otherwise. `errors` appears on validation errors of a request body (`POST /events`, `POST /certifications`), with every
field problem at once. `incident_id` appears on `5xx`. The catalog with every code, its HTTP status and the operations that return it:
https://platform.safecreative.org/docs/errors.md

| Code | HTTP | Retry | Meaning and action |
|---|---|---|---|
| `validation_error` | 400 | No | Invalid body, parameters or range, or a body that does not match the channel modality. Fix the request. |
| `invalid_key` | 401 | No | Missing, malformed or unknown key. |
| `revoked_key` | 401 | No | The key was revoked in the console. |
| `account_not_operational` | 402 | No | Unpaid events or negative balance: certifications are rejected until a purchase settles them. Registrations keep working (as unpaid). |
| `unpaid_limit_exceeded` | 402 | No | The unpaid-events limit was reached: new events are rejected until a purchase. |
| `insufficient_balance` | 402 | No | Not enough credits for the certification issuance fee, when one is set. |
| `account_suspended` | 403 | No | Account suspended by Safe Creative: registrations and certifications rejected, queries work. Contact support. |
| `channel_suspended` | 403 | No | Channel suspended: every call with its keys is rejected. Contact support. |
| `account_disabled` | 403 | No | Account disabled (a year without operations, or by Safe Creative): every call rejected. Contact support. |
| `not_found` | 404 | No | Unknown id, an id of another channel or mode, or content of a hash-only event. |
| `client_ref_conflict` | 409 | No | `client_ref` already used with different content; the original is kept. Emitter bug. |
| `payload_too_large` | 413 | No | JSON body over 256 KB or file over 10 MB. |
| `limit_blocked` | 422 | Next period | A consumption limit set to "block" in the console was reached (UTC day or month). |
| `rate_limited` | 429 | After `Retry-After` | Too many requests for this key. Lower the sustained rate. |
| `test_quota_exceeded` | 429 | After `Retry-After` (next UTC day) | A daily test-mode limit was reached. |
| `temporarily_unavailable` | 503 | After `Retry-After` | Transient storage failure; nothing was acknowledged. Same `client_ref`. |
| `internal` | 5xx | Exponential backoff | Unexpected error. Same `client_ref`; quote `incident_id` if it persists. |

Retry `POST /events` and every `GET` on unknown outcomes (timeouts, network errors, `5xx`). Retry `POST /certifications`
only on `429` and `503`.

## Rate limits

- Per key: 50 requests/s sustained for live keys (bursts ×4; an account may have its own limit), 10/s for test keys.
- Every response carries `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset` (seconds): slow down before reaching 0.
- Do not parallelize registrations of one channel beyond what the limit allows; for order-sensitive flows, send sequentially.

## Balance

- Live events cost one credit each, bought in prepaid packs in the console. Test events are free.
- With the balance exhausted, live events are still registered (`status: unpaid`, sealed and chained) up to a limit; after
  it, `402 unpaid_limit_exceeded`. While any event is unpaid, certifications answer `402 account_not_operational`. A purchase
  settles unpaid events automatically.
- `GET /account/balance` lets a system monitor itself (`balance`, `unpaid_events`, `operational`). Prefer the `balance.low`
  webhook to polling.
