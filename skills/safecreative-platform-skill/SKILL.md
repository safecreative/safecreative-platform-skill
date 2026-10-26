---
name: safecreative-platform-skill
description: Integrates code with the Safe Creative Platform API (platform.safecreative.org/v1), which registers events with a sequence number, chained hash and qualified timestamp and issues signed certifications anyone can verify. Use when writing or reviewing code that calls POST /events or /certifications, handles sc_live_/sc_test_ API keys, client_ref idempotency, hash-only digests, retries on 429/503, error codes, or verifies Safe Creative webhooks (X-SC-Signature).
license: Apache-2.0
metadata:
  publisher: Safe Creative S.L.
  homepage: https://platform.safecreative.org/docs
---

# Safe Creative Platform API

Safe Creative, an independent trusted third party, receives **declarations** of events from the customer's systems at the
moment they happen. Each event gets a gapless sequence number per channel, a hash chained to the previous event and the
qualified timestamp (eIDAS) of its sealed segment. On demand, a **certification** of a range produces signed PDF reports
(Spanish and English), an evidence ZIP and a public verification code.

What is certified is that a declaration **was received, exactly when, and has not been altered since** — never that the
declared fact is true. Do not write code, comments or UI text that claims otherwise.

## Essentials

- **Base URL**: `https://platform.safecreative.org/v1`. Read it from configuration (e.g. `SC_API_BASE`) so it can change.
- **Auth**: `Authorization: Bearer <key>`. A key belongs to **one channel** and decides the **mode**: `sc_live_…` (real,
  one credit per event, probative value) or `sc_test_…` (same API and contract, separate chain, simulated timestamps, no
  cost, no probative value, purged after 30 days). Read the key from an environment variable or secret store (e.g.
  `SC_API_KEY`); never hardcode it, log it or commit it. **Develop and test with a `sc_test_` key.**
- Channels and keys are created only in the console (platform.safecreative.org/console); the API cannot create them.
- Each channel has a **modality**, fixed at creation: `content` (JSON `payload` or a file) or `hash_only` (only a digest is
  sent; the data never leaves the customer). Check it with `GET /channel` (`current_config.modality`).
- Timestamps in responses are UTC RFC 3339 with six fractional digits; requests accept any RFC 3339 with offset.

## Core workflow

1. `GET /channel` — confirm the key works and read the modality.
2. `POST /events` — declare each event when it happens, with a `client_ref` (see rules below). `201` = registered; `200` =
   idempotent replay of the same `client_ref` and content (the original event is returned). Store the acknowledgment
   (`event_id`, `sequence`, `received_at`, `hash`, `chain_hash`): it is the customer's receipt.
3. `GET /events`, `GET /events/{event_id}` — query what is registered (cursor pagination with `next_cursor`).
4. `POST /certifications` with a range (`from`/`to` dates **or** `seq_from`/`seq_to`) → `202` with `status: processing`.
   Poll `GET /certifications/{id}` every few seconds (or use the `certification.completed` webhook) until `completed` or
   `failed`. Then download the reports and evidence (URLs expire after 7 days; fetch the certification again for fresh ones)
   and keep the `verification_code`.

Details and code: [registering events](references/registering-events.md) · [certifications](references/certifications.md).

## Rules that integrations get wrong

1. **`client_ref` is the idempotency key** (unique per channel, up to 256 chars). Derive it from the source fact (a
   transaction id, a persisted UUID, `scan.completed/<repo>/<sha>`) and persist it **before** the call.
2. **Retry with the same `client_ref` and the same body** on timeouts, network errors, `429`, `503` and other `5xx`. A retry
   never duplicates. **Never generate a new `client_ref` to retry**: that registers the event twice.
3. A `409 client_ref_conflict` means the same `client_ref` was used with different content: a bug in the emitter. Do not
   retry; the original event is kept.
4. A **live event is irreversible** and costs one credit. Nothing in the API deletes or edits events.
5. The sequence follows **reception order**. If order matters, send events sequentially, not in parallel.
6. `occurred_at` is optional and is part of the declaration (when the emitter says the fact happened); what is attested is
   `received_at`.
7. **Hash-only**: compute the digest locally over the exact bytes being declared, lowercase hex, `hash_alg` `sha-256` or
   `sha-512`. Use the language's standard library or [scripts/sc_hash.py](scripts/sc_hash.py); never "compute" a hash
   by reasoning. Keep the original file: it is what the digest anchors.
8. If the process cannot afford to lose declarations during an outage, add a persistent **outbound queue** and resend from it.
9. **Branch on the error `code`, never on `message`** (which is localized). Every error has `doc_url`.
   Full handling: [errors, retries and limits](references/errors-and-limits.md).

## Errors at a glance

Error bodies are flat JSON: `{"code": "client_ref_conflict", "message": "…", "retryable": false, "doc_url": "https://…/docs/errors#client_ref_conflict"}`,
plus `incident_id` on `5xx`. `retryable` says whether repeating the same request may succeed. A `validation_error` of a
request body lists every problem at once in `errors` (`[{"field": "hash", "message": "…"}]`): fix them all before
retrying. `429` and `503` carry `Retry-After` (seconds).

| Code | HTTP | Retry? | Action |
|---|---|---|---|
| `validation_error` | 400 | No | Fix the request (body must match the channel modality) |
| `invalid_key`, `revoked_key` | 401 | No | Check the key configuration |
| `account_not_operational`, `unpaid_limit_exceeded`, `insufficient_balance` | 402 | No | Balance issue: buy credits in the console |
| `account_suspended`, `channel_suspended`, `account_disabled` | 403 | No | Contact Safe Creative support |
| `not_found` | 404 | No | Wrong id, or an event/certification of another channel or mode |
| `client_ref_conflict` | 409 | No | Emitter bug: same `client_ref`, different content |
| `payload_too_large` | 413 | No | JSON over 256 KB or file over 10 MB |
| `limit_blocked` | 422 | Next period | The owner's consumption limit blocks registrations |
| `rate_limited`, `test_quota_exceeded` | 429 | Yes, after `Retry-After` | Slow down |
| `temporarily_unavailable` | 503 | Yes, after `Retry-After` | Same `client_ref` |
| `internal` | 5xx | Yes, exponential backoff | Same `client_ref`; quote `incident_id` to support |

## Webhooks

Deliveries are signed: `X-SC-Signature: v1=<hex>` = HMAC-SHA256(endpoint secret `whsec_…`, `"<X-SC-Timestamp>.<raw body>"`).
Verify over the **raw** body in constant time, reject timestamps older than 5 minutes, answer any 2xx quickly, and
de-duplicate by `X-SC-Webhook-Id`. Code in [webhooks](references/webhooks.md); a checker in
[scripts/sc_verify_webhook.py](scripts/sc_verify_webhook.py).

## Test mode

Same calls with a `sc_test_` key. Force hard cases with `X-SC-Test-Scenario: unpaid | unpaid_limit | rate_limited`
(ignored with live keys). Daily limits apply. See [test mode](references/test-mode.md).

## Trying the API

[scripts/sc_api.py](scripts/sc_api.py) (Python 3.9+, standard library only) calls the API with `SC_API_KEY`:
`channel`, `register-json`, `register-hash`, `register-file`, `events`, `certify`, `certification`, `wait`. Run it with
`--help`. Use it with a test key to explore, and as a reference for retries and multipart uploads.

## MCP server

To call the API as tools instead of writing code, connect the MCP server `https://platform.safecreative.org/mcp`
(Streamable HTTP): one tool per operation, with the same rules. Two ways to authenticate: **OAuth**, with the URL only
(the user signs in with their Safe Creative account and chooses the channel and mode; no key to create), or a channel
key in `Authorization: Bearer <key>` for clients without OAuth and unattended processes.

## Documentation

When something is not covered here, read the official docs in Markdown (append `.md` to any docs URL):

- Guide: https://platform.safecreative.org/docs/guide.md
- API reference: https://platform.safecreative.org/docs/reference.md
- Error codes: https://platform.safecreative.org/docs/errors.md
- OpenAPI contract: https://platform.safecreative.org/q/openapi
- Everything in one file: https://platform.safecreative.org/llms-full.txt

Spanish versions: add `?lang=es`.
