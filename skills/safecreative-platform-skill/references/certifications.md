# Certifications

A certification covers a range of the channel's chain in the key's mode. It produces two signed PDF reports (Spanish and
English, equally authentic, same verification code), an evidence ZIP that anyone can check without Safe Creative, and, in the
content modality, the declared content in ZIP parts.

## Request

`POST /v1/certifications` with **exactly one** pair:

```json
{ "from": "2026-10-01T00:00:00Z", "to": "2026-11-01T00:00:00Z" }
```
```json
{ "seq_from": 1, "seq_to": 2500 }
```

- `from` inclusive, `to` exclusive (reception time); `seq_from`/`seq_to` inclusive. A future `to` is cut at the moment of the
  request; the range is frozen on acceptance, so events arriving later are not included.
- `202` returns the certification with `status: processing`, `event_count` and `config_versions_in_range`.
- `POST /certifications` is **not idempotent**: retry it only on `429` and `503` (nothing was accepted). After a timeout or
  another `5xx`, first list `GET /certifications` to see whether it was created.
- Rejections: `402 account_not_operational` while the account has unpaid events or a negative balance (in test mode too);
  `402 insufficient_balance` if an issuance fee is set and the balance does not cover it; `400` for an invalid or empty range
  (and, in test mode, a range over 10,000 events).

## Waiting for it

Poll `GET /v1/certifications/{certification_id}` every few seconds (`progress` goes from 0 to 1) until `status` is:

- `completed`: `reports` (one per language: `languages`, `url`, `sha256`), `report_url` (the one in the `Accept-Language`
  language, English by default), `evidence_url`, `content_parts` and `verification_code` (`SC-2026-XXXX-XXXX`, or
  `SC-TEST-…` in test mode). Issuance takes seconds to minutes; it may wait for the channel's segment to be sealed.
- `failed`: any issuance charge is refunded; the same range can be requested again.

Or configure the `certification.completed` / `certification.failed` webhooks in the console (see `webhooks.md`).

List: `GET /v1/certifications?status=&limit=&cursor=` (newest first, `limit` 1–100, default 50).

## Downloads and verification

- Download URLs need no API key: the token in the URL is the credential. Treat them as secrets (do not log or share them);
  they expire after 7 days, and fetching the certification again returns fresh ones.
- Store the PDFs and the evidence ZIP; their SHA-256 is in `reports[].sha256` and in the manifest.
- Anyone can check a report at https://platform.safecreative.org/verify with the verification code or by uploading the PDF or
  the evidence ZIP. Test certifications verify in amber and carry a "TEST" watermark.
- The report attests the declarations' reception, integrity and sequence, never the truth of the declared facts.
