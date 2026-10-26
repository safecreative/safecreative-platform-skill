# Test mode

A `sc_test_` key uses the same endpoints and contract as a live key, on a separate chain of the same channel:

- no credits consumed, simulated timestamps (`timestamp.type: simulated`), `status: test`;
- certifications are issued with a "TEST" watermark, ids `CERT-TEST-…`, verification codes `SC-TEST-…`, and verify in
  amber on the public page: **no probative value**;
- test data is purged after 30 days without activity on the channel's test chain.

Write integrations and their tests against a test key; switching to live is only a change of key.

## Forced scenarios

With a test key, the `X-SC-Test-Scenario` header reproduces responses that are hard to provoke (ignored with live keys):

| Value | Effect |
|---|---|
| `rate_limited` | Any call answers `429 rate_limited` with `Retry-After` |
| `unpaid_limit` | `POST /events` answers `402 unpaid_limit_exceeded` |
| `unpaid` | The account behaves as not operational: `POST /certifications` answers `402 account_not_operational` |

Use them in integration tests of the retry and error paths.

## Daily limits (per account, UTC day)

| Limit | Value |
|---|---|
| Test events | 10,000 |
| Declared content (JSON or files) | 100 MB |
| Test certifications | 20, of at most 10,000 events each (a larger one answers `400`) |
| Active test keys per channel | 5 |
| Requests with a test key | 10 per second |

Past a daily limit the API answers `429 test_quota_exceeded` with `Retry-After` until the next day; rejected events are not
registered. Test mode is for integrating and testing, not for real workloads.
