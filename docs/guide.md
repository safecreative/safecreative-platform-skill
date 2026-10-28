# Safe Creative Platform — API Guide

## 1. What this service is

Safe Creative Platform is the Safe Creative service built for **systems**: your processes declare
events through an API call at the moment they happen, and Safe Creative — an independent
trusted third party — computes the cryptographic digest of each declaration, assigns it a
sequence number, **chains** it to the previous event and covers it with the **qualified
timestamp** of its segment, with legal presumption in the EU. When you need the proof, you request a
**certification**: a report signed by Safe Creative with the evidence archive for the period,
verifiable by anyone on a public page.

**What exactly is certified** — worth being clear about from the start: Safe Creative attests
that your declaration **was received, exactly when, and that nobody has altered it since**. It
does not certify that the declared fact is true — the same logic as a notarized statement of
record. What you gain is what your own systems can never give you: proof that is
**contemporaneous with the fact, prior to any dispute, and held by a third party you don't
control**.

## 2. Concepts

| Concept | What it is |
|---|---|
| **Channel** | The conduit for one type of process. Created in the console; its configuration is **sealed with a timestamp** at creation (a commitment made before the facts). Changes create **versions**; none is ever rewritten. Each account can have up to 10 channels; if you need more, ask support. |
| **Event** | One declaration sent to the channel. Immutable: it gets a sequence number, digest, timestamp coverage and chaining. |
| **Modality** | Per channel: **content** (you send the data — a JSON token from your process, or a file — and the certification is self-contained) or **hash-only** (you send the digest; the content never leaves your perimeter). |
| **Declarant** | The person or entity on whose behalf events are declared. Designated when configuring the channel; part of the sealed configuration. In reports it appears as a declaration of the channel owner. |
| **Certification** | A PDF report signed by Safe Creative + evidence ZIP, covering a range of dates or sequence numbers. Issued on demand, asynchronously. |
| **API key** | A channel credential. **Live** (`sc_live_…`) or **test** (`sc_test_…`): same contract, but test mode consumes no balance and produces no probative value. |

## 3. Up and running in ten minutes

1. **Account**: sign in to the platform.safecreative.org console with your Safe Creative account — any
   type works, including the free one. No account? Signing up is free and self-service.
2. **Channel**: create your first channel in the console (name, modality, declarant). You'll
   get configuration v1, sealed, plus your first key. Start with a **test key**.
3. **First event**:

```
curl -X POST https://platform.safecreative.org/v1/events \
  -H "Authorization: Bearer sc_test_xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
        "client_ref": "run-2026-08-27-0001",
        "payload": { "action": "review.completed", "case": "EXP-4411" },
        "occurred_at": "2026-08-27T10:14:03Z"
      }'
```

Response (the acknowledgment is your receipt — store it):

```
{
  "event_id": "evt_9f3k27",
  "sequence": 1,
  "received_at": "2026-08-27T10:14:04.112Z",
  "hash": "b5bb9d8014a0f9b1d61e21e796d78dcc…",
  "chain_hash": "7d865e959b2466918c9863afca942d0f…",
  "status": "test",
  "config_version": 1,
  "mode": "test"
}
```

4. **Certify and verify**: request a certification for the range, download the test report
   (it will carry the "TEST — NO PROBATIVE VALUE" watermark) and check its code on the public verification page.
5. **Go live**: swap the test key for a live one. The contract is identical.

## 4. Registering events

### 4.1 The call

[`POST /events`](/docs/reference.md#registerEvent) with your channel key. Depending on the channel's modality:

- **Content (JSON)**: `client_ref` + `payload` (up to 256 KB in canonical form, the one that is hashed).
- **Content (file)**: multipart with `client_ref` + `file` (up to 10 MB, with a name of up to 255 characters).
- **Hash-only**: `client_ref` + `hash` + `hash_alg` (`sha-256` or `sha-512`). You compute the
  digest of the data you hold; the data itself is never sent.

`occurred_at` is optional and is **part of your declaration**: it states when you claim the
fact happened. What Safe Creative attests with the timestamp is `received_at` — when it was
received. Reports always keep the two apart.

### 4.2 Idempotency: retry without fear

`client_ref` is your unique event id (per channel and mode: live and test keep separate chains). If you retry the same call — timeout,
network drop — the event is **not duplicated**: you get `200` with the original event. If you
reuse a `client_ref` with different content, you get `409`: nothing is ever overwritten. Only the
content (its hash) is compared: a retry with another `occurred_at` or another file name returns the
original event as it was registered.

Rule of thumb: generate the `client_ref` **before** calling (your transaction id, a persisted
UUID) and retry with exponential backoff on `5xx` or timeouts. That makes your integration
outage-proof. And if your process cannot afford to drop declarations during a longer outage,
add a **local outbound queue** (a persistent buffer you resend from): your events will come in
once the service is back, each with its actual reception time.

### 4.3 Sequence and ordering

The sequence number is assigned by the service **at reception**: strictly increasing, gapless,
per channel. The probative order is the order of reception, not `occurred_at`. If the order of
your events matters, send them in order or serialize your calls.

## 5. Querying what's registered

- [`GET /events`](/docs/reference.md#listEvents) — paginated, with filters by dates, sequences and status.
- [`GET /events/{event_id}`](/docs/reference.md#getEvent) — one event with its full proof elements: digest, timestamp (or
  sealed-segment reference), sequence, chained digest, and the configuration version in force.
  Its `modality` field says whether it is a content event (`content`) or hash-only (`hash_only`).
- [`GET /events/{event_id}/content`](/docs/reference.md#getEventContent) — in content modality, the content held by Safe Creative: the
  JSON in its canonical form (the one hashed) or the file with its original name. For a hash-only
  event, `404`.
- [`GET /channel`](/docs/reference.md#getChannel) — the channel configuration and all its sealed versions.
- [`GET /account/balance`](/docs/reference.md#getAccountBalance) — balance and operational status, so your systems can self-monitor.

## 6. Certifications

[`POST /certifications`](/docs/reference.md#requestCertification) with the range (dates or sequence numbers). Issuance is
**asynchronous**: you get `202` with an id, and poll [`GET /certifications/{id}`](/docs/reference.md#getCertification) — or get
notified via the `certification.completed` webhook. When completed you'll have:

- the **signed PDF report**, in **two versions, Spanish and English**, so it holds up before
  recipients in any jurisdiction without translation: a synthesis and attestation of the range's
  sequence integrity, with the configuration versions in force and the declarant designation.
  Both versions are signed separately, carry the same verification code and the same evidence, are
  equally authentic and each is verified on its own. `reports` lists both (language, URL and
  SHA-256); `report_url` is the one in the language of your `Accept-Language`;
- the **evidence ZIP**: data or digests, timestamps, sequences and chained digests;
- the **verification code**: anyone can check the report on the public verification page,
  without being a customer.

Registering and certifying are separate moments: evidence accumulates quietly and you may
never need it — like insurance. Certify when you do.

Want to see one? The [example certification](/docs/example-certification) is a real one, from a
Safe Creative channel: its two reports, its evidence and its verification.

## 7. Webhooks

Configure endpoints in the console and pick what to receive: `certification.completed` /
`.failed`, `balance.low`, `balance.exhausted`, `events.unpaid_limit_reached`,
`consumption.limit_reached`, `recharge.auto_completed` / `.auto_failed`. From the console you can also request a test delivery
(`webhook.test`) to any endpoint.

Every delivery shares the same JSON envelope: `id` (the same on retries), `type`, `created_at`,
`mode` (`live` or `test`: balance and limit notices are always `live`; certification notices carry
the certification's mode) and `data`, whose model depends on `type`:

| `type` | Sent when | `data` fields |
|---|---|---|
| `certification.completed` | The certification has been issued | `certification_id`, `channel_id`, `status`, `event_count`, `verification_code` |
| `certification.failed` | The certification could not be issued (the charge is refunded) | `certification_id`, `channel_id`, `status`, `event_count`, `incident_id` |
| `balance.low` | The balance drops below an alert threshold (once per crossing) | `threshold_id`, `threshold`, `balance` |
| `balance.exhausted` | The first event is registered as unpaid | `channel_id` |
| `events.unpaid_limit_reached` | The unpaid-events limit is reached: the API rejects registrations with `402` | `unpaid_limit`, `unpaid_events`, `unpaid_credits` |
| `consumption.limit_reached` | A consumption limit reaches its maximum for the period | `limit_id`, `scope`, `channel_id`, `key_id`, `period`, `period_key`, `max_events`, `action` |
| `recharge.auto_completed` | An automatic top-up was charged and its credits are in the balance | `recharge_id`, `pack_id`, `credits`, `amount`, `currency`, `threshold`, `balance` |
| `recharge.auto_failed` | An automatic top-up failed and was turned off | `recharge_id`, `pack_id`, `credits`, `amount`, `currency`, `threshold`, `reason`, `payment_url`, `auto_recharge_disabled` |
| `webhook.test` | You request a test delivery in the console | `endpoint_id`, `message` |

```json
{
  "id": "ntc_…",
  "type": "balance.low",
  "created_at": "2026-09-28T07:00:16.526317Z",
  "mode": "live",
  "data": { "threshold_id": "thr_…", "threshold": 1000, "balance": 999 }
}
```

Credits are integers and timestamps are UTC with six fractional digits. Each field is described in
the API reference (`Webhook…Data` schemas). We may add fields to `data` over time: ignore the ones
you do not know.

Every delivery is **signed** with the endpoint secret and retried with exponential backoff for
about 44 hours: up to seven retries, 1 min, 5 min, 30 min, 2 h, 6 h, 12 h and 24 h after the previous
attempt. The delivery log lives in the console;
an endpoint that keeps failing is disabled and we notify you by email.

How to verify a delivery before processing it:

1. Read the `X-SC-Timestamp` (Unix seconds) and `X-SC-Signature` (`v1=<hex>`) headers.
2. Compute HMAC-SHA256 with your secret (`whsec_…`) over `<X-SC-Timestamp>.<raw body>` and compare
   it with `<hex>` in constant time.
3. Reject timestamps older than 5 minutes.
4. Reply with any 2xx; de-duplicate by `X-SC-Webhook-Id` (the envelope `id`, the same on retries).

## 8. Pricing and balance

- **Prepaid, by volume**: buy **credit packs** in the console; each registered event consumes
  **one credit**. No plans, no lock-in, no surprises. [See pricing](/pricing).
- [`GET /account/balance`](/docs/reference.md#getAccountBalance) returns the balance in credits.
- Test events cost nothing.
- Set **balance alerts** and, if you want, **consumption limits** per channel or key (warn or
  block): you control the spend.
- Or turn on **automatic top-up**: "when the balance drops below X credits, buy pack Y" with your
  default payment method at Safe Creative. We notify you of each top-up by email and webhook
  (`recharge.auto_completed`); if one fails, it is turned off without losing its settings and we
  notify you (`recharge.auto_failed`) so you can turn it back on once it is sorted out. At most 5
  automatic top-ups are made per day.

### 8.1 What if the balance runs out?

Your sequence **does not break**: events arriving with an exhausted balance are still
received, sealed and chained, marked **unpaid** — up to a limit. While you have unpaid events:

- no certifications can be issued (`account_not_operational` — "account not operational");
- if the unpaid limit is reached (5,000 events per account, or 100 if the account has not made any
  purchase yet), new registrations are rejected (`unpaid_limit_exceeded`).

When you top up, unpaid events are **charged automatically** and everything returns to normal —
none of their proof elements changes. Recommendation: configure `balance.low` and never get here.

If a purchase is reverted after payment (a refund or a chargeback), its credits are deducted even
if you had already spent them. The balance may then be negative: until the next purchase covers
it, the account is not operational and new live events are received as unpaid, as above.

### 8.2 Unused accounts

An account that goes **a year** without registering events, requesting certifications (with a live
or test key) or buying credits is **disabled**: the API rejects every call (`403 account_disabled`)
and the console is unavailable. We email you 30 and 7 days before; any one of those operations
restarts the period. Your data and certifications are kept, and issued certifications can still be
verified. To reactivate it, contact support.

## 9. Errors and retries

Uniform format: `code`, `message`, `retryable`, `doc_url`. Branch on `code`, never on `message`;
`retryable` says whether repeating the same request may succeed (`429`, `503` and other `5xx`), and
`doc_url` leads to its row in the [error code catalog](/docs/errors), with its HTTP status, meaning
and the operations that can return it. A `validation_error` of a request body lists every field
problem at once in `errors` (`field` and `message`). Quick guide:

| You get | What to do |
|---|---|
| `400 validation_error` | Check the body and the channel's modality. Don't retry as-is. |
| `401 invalid_key` / `revoked_key` | Wrong or revoked key: check your configuration. |
| `402` (all three codes) | Balance matter: top up or check unpaid events. Retrying won't help. |
| `403 account_suspended` | Account suspended by Safe Creative: registrations and certifications are rejected; queries keep working. Contact support. |
| `403 channel_suspended` | Channel suspended by Safe Creative: every call with its keys is rejected, queries included. Contact support. |
| `403 account_disabled` | Account disabled (after a year without operations or by Safe Creative): every call is rejected. Contact support to reactivate it. |
| `409 client_ref_conflict` | You reused a `client_ref` with different content: a bug in your emitter. |
| `422 limit_blocked` | Your own consumption limit, set to "block". |
| `429 rate_limited` | Wait `Retry-After` and retry. Lower your sustained rate. |
| `503 temporarily_unavailable` | Transient storage failure (e.g. during a database failover): nothing was acknowledged. Wait `Retry-After` and retry with the same `client_ref`. |
| `5xx internal` | Retry with exponential backoff and the same `client_ref` (it won't duplicate). Include `incident_id` when contacting support. |

Rate limits: 50 sustained requests/second per live key (bursts ×4) and 10 per test key. Responses
to requests with a valid key carry `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset`
(seconds). Error
messages come in English or, with `Accept-Language: es`, in Spanish.

## 10. Test mode

Everything in this guide works the same with an `sc_test_` key: same API, same contract,
separate chain, zero cost and **no probative value** (reports carry the "TEST — NO PROBATIVE
VALUE" watermark and verify in amber). A channel's test data is deleted once it has had no test
events for 30 days.

To exercise the hard cases without touching your real balance, force scenarios with the
`X-SC-Test-Scenario: unpaid | unpaid_limit | rate_limited` header on test calls.

Test mode is for integrating and testing, not for real workloads, and it has limits per account
and day (UTC):

| Limit | Value |
|---|---|
| Test events | 10,000 per day |
| Declared content in test (JSON or file) | 100 MB per day |
| Test certifications | 20 per day, of at most 10,000 events each |
| Active test keys | 5 per channel |
| Requests with a test key | 10 per second |

Past a daily limit the API answers `429 test_quota_exceeded` with `Retry-After` until the next
day; what is rejected is not registered. A larger test certification answers `400`.

## 11. Integration recipes

Recommended configurations per use case, with sample event formats and an indicative
regulatory anchor (not legal advice). Each recipe ships as its own page on the documentation
site with complete examples; below, a summary of all of them and, in full, the first one with a
date on the calendar.

- **Proof of diligence in vulnerability and incident management** (Cyber Resilience Act,
  art. 14 — reporting deadlines from 2026-09-11 —; NIS2, arts. 21 and 23; DORA, arts. 17-19):
  hash-only modality, one channel per protected system, one event per security-tool result.
  Developed in [§11.1](/docs/11-integration-recipes.md#recipe-proof-of-diligence-in-vulnerability-and-incident-management).
- **AI agent and system logs** (EU AI Act, high-risk systems; obligation postponed by the
  Digital Omnibus to 2027-12-02 and 2028-08-02 depending on the annex): content modality, one
  token per agent action, formatted in line with the IETF draft on agent audit trails ([§11.2](/docs/11-integration-recipes.md#note-on-ai-agent-logs)).
- **Whistleblowing channels** (probative deadlines with confidentiality): hash-only modality,
  one event per case milestone.
- **Maintenance and periodic inspections**: content modality, one event per closed work
  report — what you prove is sustained diligence.
- **Changes in critical systems** (DORA and similar): hash-only or content modality, one event
  per deployment or relevant configuration change.

### 11.1 Recipe: proof of diligence in vulnerability and incident management

**Who it is for.** Software manufacturers subject to the Cyber Resilience Act, entities under
NIS2 or DORA, and the integrators or managed security providers who run AI security tooling for
them: agents that scan and fix code (Codex Security, Claude Security, GitHub Copilot Autofix,
Semgrep, Snyk, CodeQL), autonomous penetration testing, automated security operations centres.
All of them produce facts at scale and attest those facts themselves; the channel adds what they
cannot give themselves: a date and integrity from a third party that neither the manufacturer,
nor its security vendor, nor the model provider controls.

**What is proved.** Not that the patch is correct or the scan was complete — you and your tool
assert that — but that each fact was declared on a date with legal presumption and that the
sequence has not been recomposed afterwards: that the scan existed before the incident, that the
vulnerability was known on day X, that the fix was verified on day Y, that the notification to
the authority went out within the deadline. Legal deadlines run from the moment you "become
aware": proving that instant is proving compliance.

**Recommended channel configuration.**

- One channel per protected system or product.
- **Hash-only** modality: vulnerability details must not leave your perimeter before coordinated
  disclosure. You keep the files (SARIF, reports, acknowledgements) and declare their digest; if
  you ever need to produce them, the sealed digest anchors them to their date.
- Declarant: the manufacturer or the obligated entity. If you operate as an integrator,
  designate your customer.
- Supplementary information: which system, which tools and which phases are declared, and the
  identifier convention you use (it is sealed in the configuration, before the facts).

**Typical events.** In hash-only mode an event carries `client_ref`, `hash` and `hash_alg`
([§4.1](/docs/4-registering-events.md#the-call)); the type of fact and its identifier go in the `client_ref`, under a convention you
declare in the channel's supplementary information.

| Cycle phase | Recommended `client_ref` | Digest of |
|---|---|---|
| Discover | `scan.completed/<repository>/<revision>` | Scan manifest or SARIF file |
| Discover | `finding.opened/<repository>/<id>` | Finding record (identifier, severity, component) |
| Validate | `finding.validated/…` · `finding.dismissed/…` | Validation report |
| Assign | `finding.assigned/…` | Ticket created |
| Fix | `fix.deployed/<repository>/<id>/<change>` | Deployment confirmation and change identifier |
| Verify | `fix.verified/<repository>/<id>/<revision>` | Result of the re-run scan |
| Notify | `notice.early/…` · `notice.full/…` · `report.final/…` | Acknowledgement from the reporting platform (ENISA, CSIRT) |

**How to connect: the three usual routes.** No tool needs to cooperate; all of them export in
standard formats, fire webhooks, or run in your continuous integration.

*Route 1 — a continuous-integration step that declares the scan's digest.* Works with any tool
that produces SARIF. Keep `results.sarif` next to the revision: it is the original the digest anchors.

```
# .github/workflows/security.yml — after the step that produces results.sarif
- name: Declare the scan to Safe Creative Platform
  env:
    SC_KEY: ${{ secrets.SC_EVENTS_KEY }}        # channel key (live or test)
  run: |
    HASH=$(sha256sum results.sarif | cut -d' ' -f1)
    curl -sS --retry 5 --retry-all-errors -X POST https://platform.safecreative.org/v1/events \
      -H "Authorization: Bearer $SC_KEY" -H "Content-Type: application/json" \
      -d "{\"client_ref\":\"scan.completed/$GITHUB_REPOSITORY/$GITHUB_SHA\",
           \"hash\":\"$HASH\",\"hash_alg\":\"sha-256\",
           \"occurred_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
```

*Route 2 — a GitHub webhook receiver.* GitHub sends a `code_scanning_alert` webhook on every
state change of an alert: created, fixed, closed, reopened. It is the cheapest hook in the whole
family (it also covers alerts uploaded by Semgrep, Snyk or CodeQL). Node 20, no dependencies:

```
import { createServer } from 'node:http';
import { createHash, createHmac, timingSafeEqual } from 'node:crypto';

const SC_KEY = process.env.SC_EVENTS_KEY, GH_SECRET = process.env.GH_WEBHOOK_SECRET;

createServer(async (req, res) => {
  let body = ''; for await (const chunk of req) body += chunk;
  // 1) verify GitHub's signature first
  const expected = 'sha256=' + createHmac('sha256', GH_SECRET).update(body).digest('hex');
  const received = String(req.headers['x-hub-signature-256'] || '');
  if (expected.length !== received.length || !timingSafeEqual(Buffer.from(expected), Buffer.from(received))) {
    res.writeHead(401); res.end(); return;
  }
  const hook = JSON.parse(body);             // action: created | fixed | closed_by_user | reopened …
  archive(body, req.headers['x-github-delivery']);   // keep the JSON: it is the original the digest anchors
  // 2) declare the digest to the channel (idempotent by client_ref: the delivery id prevents duplicates)
  const r = await fetch('https://platform.safecreative.org/v1/events', {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + SC_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_ref: 'finding.' + hook.action + '/' + hook.repository.full_name + '/' +
                  hook.alert.number + '/' + req.headers['x-github-delivery'],
      hash: createHash('sha256').update(body).digest('hex'),
      hash_alg: 'sha-256',
      occurred_at: hook.alert.updated_at || hook.alert.created_at
    })
  });
  res.writeHead(r.ok ? 204 : 500); res.end();  // on failure, GitHub redelivers
}).listen(8080);
```

*Route 3 — a generic webhook receiver* (Claude Security, SOC platforms, penetration-testing
tools). Python 3.11, no dependencies. Adjust field names to your tool's schema and verify its
signature if it offers one:

```
import hashlib, json, os, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

SC_KEY = os.environ["SC_EVENTS_KEY"]

class Receiver(BaseHTTPRequestHandler):
    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        hook = json.loads(raw)
        archive(raw)                                       # keep the original the digest anchors
        kind = hook.get("event", "finding.updated")        # e.g. finding.validated, fix.verified
        ref = f'{kind}/{hook.get("project", "-")}/{hook.get("id", hashlib.sha256(raw).hexdigest()[:16])}'
        event = {"client_ref": ref, "hash": hashlib.sha256(raw).hexdigest(), "hash_alg": "sha-256"}
        if "timestamp" in hook:
            event["occurred_at"] = hook["timestamp"]
        request = urllib.request.Request(
            "https://platform.safecreative.org/v1/events",
            data=json.dumps(event).encode(), method="POST",
            headers={"Authorization": f"Bearer {SC_KEY}", "Content-Type": "application/json"})
        urllib.request.urlopen(request, timeout=10)        # on error, let the tool retry
        self.send_response(204); self.end_headers()

HTTPServer(("", 8080), Receiver).serve_forever()
```

The rule in [§4.2](/docs/4-registering-events.md#idempotency-retry-without-fear) applies to all three routes: same `client_ref` on retries, exponential
backoff, and a local outbound queue if the process cannot afford to drop declarations. Request
the certification when you need it — for an inspection, a claim or a lawsuit — and the report
will attest the integrity of the period's sequence; the evidence archive lets anyone match each
digest against the original you keep.

**Indicative regulatory anchor.** Cyber Resilience Act, art. 14 (early warning within 24
hours, notification within 72 hours, final report within 14 days or one month; from
2026-09-11) · NIS2, arts. 21 and 23 · DORA, arts. 17-19 and 24 ff. None of these rules requires
a third party: they require demonstrable diligence, and the moment you "became aware" is what
the channel leaves proved.

### 11.2 Note on AI agent logs

If your case is logging agent actions, align the token with the IETF draft
`draft-sharif-agent-audit-trail`: `record_id`, `session_id`, `agent_id`, `action_type`,
`outcome`, `record_phase` and, if you keep your own chain, `prev_hash`. Use `record_id` as
the `client_ref`. That model requires, from a certain assurance level up, that logging be done
by a **component independent of the agent** with an **external timestamp**: that component is
the channel, and each event's reception date (`received_at`) is covered by the qualified
timestamp of its segment. The agent does not need to sign anything for the sequence to carry a
third-party date.

```
{
  "client_ref": "rec_01J9ZM3T7Q8KX2",
  "payload": {
    "record_id": "rec_01J9ZM3T7Q8KX2", "session_id": "ses_44a1", "agent_id": "case-handler-v3",
    "action_type": "case.update", "outcome": "success", "record_phase": "post",
    "prev_hash": "sha256:6b1f0c6e…94a7d", "target": "EXP-4411"
  },
  "occurred_at": "2026-09-04T09:41:07Z"
}
```

## 12. Integrating with AI agents

If you write your integration with an AI coding agent (Claude Code, Codex, GitHub Copilot,
Cursor, Gemini CLI, Windsurf…), give it what it needs to get the details right: the rules of
[§4.2](/docs/4-registering-events.md#idempotency-retry-without-fear), the error codes of [§9](/docs/9-errors-and-retries.md) and webhook verification are exactly where generic code fails.

### 12.1 The integration skill

The **Safe Creative Platform skill** follows the open [Agent Skills](https://agentskills.io)
format, which most coding agents load. It explains the service and the full journey, the
idempotency and retry rules, the error codes, test mode and webhook verification, with examples
in Python, TypeScript and Java and three small scripts (a minimal client, file digests and webhook
verification). Licence: Apache 2.0.

- [GitHub repository](https://github.com/safecreative/safecreative-platform-skill) (`safecreative/safecreative-platform-skill`)
- [Download the skill](/docs/agents/safecreative-platform-skill.zip) (`safecreative-platform-skill.zip`)
- [Download the full plugin](/docs/agents/safecreative-platform-plugin.zip) (the skill plus the
  plugin manifests for Claude Code and for Agent Plugins clients)

| Agent | How to install it |
|---|---|
| Claude Code | `/plugin marketplace add safecreative/safecreative-platform-skill` and `/plugin install safecreative-platform@safecreative`. Or unzip the skill into `.claude/skills/` of your project (or `~/.claude/skills/` for all of them). |
| claude.ai and Claude Desktop | Upload `safecreative-platform-skill.zip` in Settings › Capabilities. |
| Codex, Cursor, Gemini CLI, Windsurf and other agents | `npx skills add safecreative/safecreative-platform-skill`, or unzip the skill into `.agents/skills/` of your project. |
| GitHub Copilot | Unzip the skill into `.github/skills/` (it also reads `.agents/skills/`). |

The agent uses it on its own when you ask for something related ("declare each paid order to Safe
Creative Platform", "verify their webhooks"). Give it a **test key** in an environment variable
(`SC_API_KEY=sc_test_…`), never a live one while developing.

### 12.2 The MCP server

Agents that call tools (claude.ai, ChatGPT, Claude Code, Codex, Cursor, VS Code with GitHub
Copilot, Gemini CLI, Windsurf, Microsoft Copilot Studio and others) can use the API through the
platform's **MCP server**:

- **URL**: `https://platform.safecreative.org/mcp` (Streamable HTTP).
- **Tools**: one per API operation (`get_channel`, `get_account_balance`, `list_events`,
  `get_event`, `get_event_content`, `register_event`, `request_certification`,
  `list_certifications`, `get_certification`). Each one calls the API on behalf of the connection,
  so limits, idempotency, test mode and errors are the same. Files can only be declared through the
  REST API.

There are two ways to authenticate. Either way the agent works on **one channel and one mode**: to
use several channels, add the server once per channel.

#### Signing in with OAuth: no key to create

The client only needs the URL. When connecting, it opens Safe Creative Platform: you sign in with
your Safe Creative account, choose the channel and the mode (test by default) and authorize the
application. That is all: the platform creates the key for you, marked "Agent (OAuth)" in the
channel's Keys tab, where you can see what the agent does, set it a consumption limit or revoke it.
The application never sees a key: it receives short-lived tokens that it renews on its own.

- **claude.ai and Claude Desktop**: add a custom connector with the URL.
- **ChatGPT** (Business, Enterprise and Edu workspaces): an administrator adds it as an app with the
  URL.
- **Claude Code**: `claude mcp add --transport http safecreative https://platform.safecreative.org/mcp`,
  then `/mcp` to sign in.
- **Cursor**: the URL only, in `.cursor/mcp.json`:

  ```json
  { "mcpServers": { "safecreative": { "url": "https://platform.safecreative.org/mcp" } } }
  ```

- **VS Code**: the URL only, in `.vscode/mcp.json`:

  ```json
  { "servers": { "safecreative": { "type": "http", "url": "https://platform.safecreative.org/mcp" } } }
  ```

#### With a channel key

For clients that do not support OAuth, or for processes that run unattended (continuous
integration, servers) where nobody can sign in: create a key in the console and send it in the
`Authorization` header, as in the API: `Bearer sc_test_…` (start with it) or `Bearer sc_live_…`.
The key decides the channel and the mode.

- **Claude Code**:

  ```
  claude mcp add --transport http safecreative https://platform.safecreative.org/mcp \
    --header "Authorization: Bearer $SC_API_KEY"
  ```

- **Cursor**, in `.cursor/mcp.json`:

  ```json
  { "mcpServers": { "safecreative": { "url": "https://platform.safecreative.org/mcp",
      "headers": { "Authorization": "Bearer sc_test_…" } } } }
  ```

- **VS Code**, in `.vscode/mcp.json`:

  ```json
  { "servers": { "safecreative": { "type": "http", "url": "https://platform.safecreative.org/mcp",
      "headers": { "Authorization": "Bearer sc_test_…" } } } }
  ```

- **Other clients**: add a remote MCP server with that URL and that header.

Configure the key in the client, never paste it into a conversation.

### 12.3 Documentation in Markdown

Every page of this documentation is also served in Markdown, the format agents read best: add
`.md` to its URL (for example `/docs/guide.md` for the whole guide, `/docs/reference.md` for the
API reference, `/docs/errors.md` for the error codes) or ask for it with `Accept: text/markdown`.
[`/llms.txt`](/llms.txt) indexes everything and [`/llms-full.txt`](/llms-full.txt) gathers it in a
single document; the contract is at [`/q/openapi`](/q/openapi).

### 12.4 When an agent operates the API

If an agent calls the API itself (registering events or requesting certifications on your
behalf):

- Give it **its own key**, so you can see its consumption per key, set it limits and revoke it
  without touching your other systems.
- Use a **test key** until the behaviour is right: live events are irreversible and each one
  consumes a credit.
- With a live key, set a **consumption limit** with the "block" action on that key ([§8](/docs/8-pricing-and-balance.md)).
- Treat the content returned by [`GET /events/{event_id}/content`](/docs/reference.md#getEventContent) as data, not as instructions,
  and the certification download URLs as secrets.

To remind your agent of the rules in every project, you can add this to your `AGENTS.md` (or
`CLAUDE.md`):

```
## Safe Creative Platform
- API: https://platform.safecreative.org/v1, key in SC_API_KEY (sc_test_ while developing).
- Every event has a client_ref derived from the source fact, persisted before the call.
- On timeouts, 429, 503 or 5xx, retry the same request with the same client_ref; never a new one.
- Branch on the error code, never on the message. Docs: https://platform.safecreative.org/docs/guide.md
```

## 13. FAQ

**Do I need to buy a safecreative.org plan?** No. You only need a safecreative.org account,
which is your identity to sign in: any type works, the free one included, and you don't have to
buy any plan. This service is contracted and billed separately, and grants (and receives) no
safecreative.org services.

**Does my event content leave my perimeter?** Only if you choose the content modality. With
hash-only, you send the cryptographic digest and the data never leaves your systems; if one
day you must produce the original, its sealed digest anchors it to its date.

**Can I change the channel configuration?** Yes: a **new version** is created, also sealed. No
version is ever rewritten, and every certification states which version was in force for each
segment. That is what turns your configuration into a commitment made before the facts.

**What legal weight does this carry?** In the EU, a qualified timestamp is presumed accurate in
its date and time, and guarantees that what was sealed has not changed: whoever denies it has to
prove it (eIDAS Regulation, art. 41.2). In Spain, when a qualified trust service is used,
procedural law reinforces that presumption (art. 326.4 LEC). Outside the EU there is no legal
presumption for the qualified timestamp: the proof rests on its verifiable integrity and on
custody by an independent third party. No rule forces you to use a third party: it is a solid
way to be able to prove it.

**White label?** No. Reports carry Safe Creative's brand and signature — precisely the value
neither you nor your customer can manufacture.

**How does a third party verify my report?** On the public verification page: with the code
printed on the report, or by uploading the file (which additionally confirms it has not been
altered). No account, no cost.

**How is this different from an audit trail signed by my own system?** In who attests.
"Tamper-evident" audit trails that sign receipts with the operator's key, chain digests and add
an RFC 3161 timestamp from a free or commercial authority are verifiable — but they are attested
by the interested party itself, and a non-qualified timestamp carries no legal presumption under
article 41.2 of the eIDAS Regulation. Here Safe Creative, a third party independent of the
parties, holds and chains your declarations; the timestamp is issued by an eIDAS qualified
provider, the configuration is committed before the facts, and the report is signed by Safe
Creative. If you already run your own chain, keep it: declare the digest of each receipt
or of each checkpoint to the channel and turn it into third-party evidence.

**Can an AI agent declare directly, or send OpenTelemetry traces?** Yes: through the REST API
from the agent's code, via a receiver ([§11.1](/docs/11-integration-recipes.md#recipe-proof-of-diligence-in-vulnerability-and-incident-management), route 3) or as a tool call, with the platform's MCP
server ([§12.2](/docs/12-integrating-with-ai-agents.md#the-mcp-server)). An OpenTelemetry trace receiver is planned as a later layer on the same API; it does
not change the contract. To have a coding agent write the integration for you, see [§12](/docs/12-integrating-with-ai-agents.md).
