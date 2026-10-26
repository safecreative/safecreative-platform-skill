# Error codes

Every error response of the API carries a stable code, a message, retryable (whether repeating the same request may succeed) and a doc_url that points to the code's row on this page; validation errors of a request body list every field problem in errors. Branch on the code, never on the message. Generated automatically from the API contract.

What to do with each error and how to retry is explained in the guide: [Errors and retries](/docs/9-errors-and-retries.md).

| Code | HTTP | Retryable | Meaning | Operations |
|---|---|---|---|---|
| `validation_error` | 400 | No | Invalid body, parameters or range, or a body that does not match the channel's modality. Fix the request: repeating it as is fails again. Problems in the fields of a body are listed one by one in `errors`. | `POST /events`, `GET /events`, `POST /certifications`, `GET /certifications` |
| `invalid_key` | 401 | No | The API key is missing, malformed or unknown. | Any operation |
| `revoked_key` | 401 | No | The API key was revoked in the console. | Any operation |
| `account_not_operational` | 402 | No | The owner account has unpaid events or a negative balance, so certifications are rejected until a purchase settles them. | `POST /certifications` |
| `unpaid_limit_exceeded` | 402 | No | The owner account reached its unpaid-events limit: new events are rejected until a purchase settles the debt. | `POST /events` |
| `insufficient_balance` | 402 | No | Not enough credits for the certification issuance fee, when one is set. | `POST /certifications` |
| `not_found` | 404 | No | The resource does not exist on this channel, or the event has no content to download (hash-only modality). | `GET /events/{event_id}`, `GET /events/{event_id}/content`, `GET /certifications/{certification_id}` |
| `client_ref_conflict` | 409 | No | The `client_ref` was already used on this channel with different content; the original event is kept. It points to a bug in the emitter. | `POST /events` |
| `payload_too_large` | 413 | No | The body is over the modality limit (256 KB of canonical JSON, 10 MB per file). | `POST /events` |
| `limit_blocked` | 422 | No | A consumption limit set to block in the console was reached: registrations are rejected until its next period (UTC day or month). | `POST /events` |
| `rate_limited` | 429 | Yes | Too many requests with this key: wait `Retry-After` seconds and lower the sustained rate. | Any operation |
| `test_quota_exceeded` | 429 | Yes | With a test key, a daily test-mode limit (events, declared content or certifications) was reached: wait `Retry-After`, until the next UTC day. | Any operation |
| `internal` | 5xx | Yes | Unexpected server error (HTTP 5xx), with `incident_id`. Retry with exponential backoff (with the same `client_ref` when registering events) and quote `incident_id` to support if it persists. | Any operation |
| `temporarily_unavailable` | 503 | Yes | Transient storage failure; nothing was acknowledged. Retry after `Retry-After` (with the same `client_ref` when registering events). | `POST /events`, `POST /certifications` |
| `account_suspended` | 403 | No | Safe Creative suspended the owner account: event registration and certifications are rejected, queries keep working. Contact support. | Any operation |
| `channel_suspended` | 403 | No | Safe Creative suspended the channel: every call with its keys is rejected, queries included. Contact support. | Any operation |
| `account_disabled` | 403 | No | The owner account is disabled (after a year without operations, or by Safe Creative): every call is rejected until support reactivates it. | Any operation |
