#!/usr/bin/env python3
"""Minimal Safe Creative Platform API client (Python 3.9+, standard library only).

Reads the key from SC_API_KEY and the base URL from SC_API_BASE (default https://platform.safecreative.org/v1).
Prints the JSON response; the HTTP status goes to standard error. Exits 1 on an API error, printing its code.

    export SC_API_KEY=sc_test_...
    python3 sc_api.py channel
    python3 sc_api.py register-json --client-ref order-1042 --payload '{"action": "order.paid", "order": 1042}'
    python3 sc_api.py register-hash --client-ref scan/repo/abc123 --file results.sarif
    python3 sc_api.py register-file --client-ref contract-77 --file contract.pdf
    python3 sc_api.py events --seq-from 1 --limit 20
    python3 sc_api.py certify --seq-from 1 --seq-to 20
    python3 sc_api.py wait CERT-TEST-2026-0000001

Retry policy, the one the API asks for:
  * GET and POST /events (idempotent by client_ref): retried on network errors, 429, 503 and other 5xx, with the
    same body, honouring Retry-After and otherwise exponential backoff.
  * POST /certifications (not idempotent): retried only on 429 and 503, which guarantee nothing was accepted.
"""
import argparse
import hashlib
import json
import mimetypes
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

DEFAULT_BASE = "https://platform.safecreative.org/v1"
USER_AGENT = "sc_api.py/1.0 (safecreative-platform-skill skill)"
MAX_ATTEMPTS = 6


class ApiError(Exception):
    def __init__(self, status, body):
        self.status = status
        self.body = body
        code = body.get("code") if isinstance(body, dict) else None
        super().__init__(f"HTTP {status} {code or ''}".strip())


class Client:
    def __init__(self, key, base=DEFAULT_BASE, lang=None, scenario=None, timeout=30):
        if not key:
            raise SystemExit("sc_api: set SC_API_KEY (use a sc_test_ key while developing)")
        self.key = key
        self.base = base.rstrip("/")
        self.lang = lang
        self.scenario = scenario
        self.timeout = timeout

    def request(self, method, path, body=None, content_type=None, idempotent=True):
        """Sends the request with the retry policy above; returns (status, parsed JSON)."""
        headers = {"Authorization": "Bearer " + self.key, "Accept": "application/json", "User-Agent": USER_AGENT}
        if content_type:
            headers["Content-Type"] = content_type
        if self.lang:
            headers["Accept-Language"] = self.lang
        if self.scenario:
            headers["X-SC-Test-Scenario"] = self.scenario
        for attempt in range(1, MAX_ATTEMPTS + 1):
            req = urllib.request.Request(self.base + path, data=body, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.status, json.loads(resp.read() or b"null")
            except urllib.error.HTTPError as e:
                status, raw, retry_after = e.code, e.read(), e.headers.get("Retry-After")
                try:
                    parsed = json.loads(raw)
                except ValueError:
                    parsed = {"raw": raw.decode("utf-8", "replace")}
                retryable = status in (429, 503) or (idempotent and status >= 500)
                if not retryable or attempt == MAX_ATTEMPTS:
                    raise ApiError(status, parsed)
                self._sleep(attempt, retry_after)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                # The outcome is unknown: only an idempotent request can be repeated safely.
                if not idempotent or attempt == MAX_ATTEMPTS:
                    raise
                print(f"sc_api: {e}; retrying", file=sys.stderr)
                self._sleep(attempt, None)
        raise AssertionError("unreachable")

    @staticmethod
    def _sleep(attempt, retry_after):
        delay = int(retry_after) if retry_after and retry_after.isdigit() else min(60, 2 ** attempt) + random.random()
        print(f"sc_api: retrying in {delay:.1f}s", file=sys.stderr)
        time.sleep(delay)

    # --- operations -------------------------------------------------------------------------------------------------

    def get(self, path, **query):
        query = {k: v for k, v in query.items() if v is not None}
        return self.request("GET", path + ("?" + urllib.parse.urlencode(query) if query else ""))

    def register(self, event):
        """POST /events with a JSON body (content payload or hash-only). 201 = new, 200 = idempotent replay."""
        return self.request("POST", "/events", json.dumps(event).encode("utf-8"), "application/json")

    def register_file(self, client_ref, path, occurred_at=None):
        """POST /events as multipart/form-data (content modality, file of up to 10 MB)."""
        boundary = "sc-" + uuid.uuid4().hex
        fields = [("client_ref", client_ref)] + ([("occurred_at", occurred_at)] if occurred_at else [])
        parts = []
        for name, value in fields:
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8"))
        filename = os.path.basename(path).replace('"', "")
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                      f"Content-Type: {mime}\r\n\r\n").encode("utf-8") + data + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode("ascii"))
        return self.request("POST", "/events", b"".join(parts), "multipart/form-data; boundary=" + boundary)

    def certify(self, range_):
        """POST /certifications: not idempotent, so never retried on unknown outcomes."""
        return self.request("POST", "/certifications", json.dumps(range_).encode("utf-8"), "application/json",
                            idempotent=False)

    def wait(self, certification_id, interval=5, timeout=1800):
        """Polls GET /certifications/{id} until it is completed or failed."""
        deadline = time.time() + timeout
        while True:
            status, body = self.get("/certifications/" + urllib.parse.quote(certification_id))
            if body.get("status") != "processing" or time.time() > deadline:
                return status, body
            print(f"sc_api: {certification_id} processing ({body.get('progress') or 0:.0%})", file=sys.stderr)
            time.sleep(interval)


def file_digest(path, alg):
    h = hashlib.new({"sha-256": "sha256", "sha-512": "sha512"}[alg])
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description="Minimal Safe Creative Platform API client (key in SC_API_KEY).")
    p.add_argument("--base", default=os.environ.get("SC_API_BASE", DEFAULT_BASE), help="API base URL (SC_API_BASE)")
    p.add_argument("--lang", choices=["en", "es"], help="language of error messages and of report_url")
    p.add_argument("--scenario", choices=["unpaid", "unpaid_limit", "rate_limited"], help="forced test scenario (test keys)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("channel", help="GET /channel: the channel and its sealed configuration versions")
    sub.add_parser("balance", help="GET /account/balance")
    s = sub.add_parser("register-json", help="POST /events, content modality with a JSON payload")
    s.add_argument("--client-ref", required=True)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--payload", help="JSON text")
    g.add_argument("--payload-file", help="file with the JSON payload")
    s.add_argument("--occurred-at")
    s = sub.add_parser("register-hash", help="POST /events, hash-only modality")
    s.add_argument("--client-ref", required=True)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="file whose digest is declared (computed locally)")
    g.add_argument("--hash", help="digest already computed, lowercase hex")
    s.add_argument("--alg", choices=["sha-256", "sha-512"], default="sha-256")
    s.add_argument("--occurred-at")
    s = sub.add_parser("register-file", help="POST /events, content modality with a file (multipart)")
    s.add_argument("--client-ref", required=True)
    s.add_argument("--file", required=True)
    s.add_argument("--occurred-at")
    s = sub.add_parser("events", help="GET /events")
    for name in ("from", "to", "seq-from", "seq-to", "status", "limit", "cursor"):
        s.add_argument("--" + name)
    s = sub.add_parser("event", help="GET /events/{event_id}")
    s.add_argument("event_id")
    s = sub.add_parser("certify", help="POST /certifications for a date or sequence range")
    for name in ("from", "to"):
        s.add_argument("--" + name)
    for name in ("seq-from", "seq-to"):
        s.add_argument("--" + name, type=int)
    s = sub.add_parser("certification", help="GET /certifications/{id}")
    s.add_argument("certification_id")
    s = sub.add_parser("wait", help="poll a certification until completed or failed")
    s.add_argument("certification_id")
    s.add_argument("--interval", type=int, default=5)
    s.add_argument("--timeout", type=int, default=1800)
    a = p.parse_args()

    c = Client(os.environ.get("SC_API_KEY"), a.base, a.lang, a.scenario)
    try:
        if a.cmd == "channel":
            status, body = c.get("/channel")
        elif a.cmd == "balance":
            status, body = c.get("/account/balance")
        elif a.cmd == "register-json":
            payload = json.loads(a.payload) if a.payload else json.load(open(a.payload_file, encoding="utf-8"))
            event = {"client_ref": a.client_ref, "payload": payload}
            if a.occurred_at:
                event["occurred_at"] = a.occurred_at
            status, body = c.register(event)
        elif a.cmd == "register-hash":
            event = {"client_ref": a.client_ref, "hash": a.hash.lower() if a.hash else file_digest(a.file, a.alg),
                     "hash_alg": a.alg}
            if a.occurred_at:
                event["occurred_at"] = a.occurred_at
            status, body = c.register(event)
        elif a.cmd == "register-file":
            status, body = c.register_file(a.client_ref, a.file, a.occurred_at)
        elif a.cmd == "events":
            status, body = c.get("/events", **{"from": getattr(a, "from"), "to": a.to, "seq_from": a.seq_from,
                                                "seq_to": a.seq_to, "status": a.status, "limit": a.limit,
                                                "cursor": a.cursor})
        elif a.cmd == "event":
            status, body = c.get("/events/" + urllib.parse.quote(a.event_id))
        elif a.cmd == "certify":
            range_ = {k: v for k, v in {"from": getattr(a, "from"), "to": a.to, "seq_from": a.seq_from,
                                        "seq_to": a.seq_to}.items() if v is not None}
            status, body = c.certify(range_)
        elif a.cmd == "certification":
            status, body = c.get("/certifications/" + urllib.parse.quote(a.certification_id))
        else:
            status, body = c.wait(a.certification_id, a.interval, a.timeout)
    except ApiError as e:
        print(f"HTTP {e.status}", file=sys.stderr)
        print(json.dumps(e.body, indent=2, ensure_ascii=False))
        sys.exit(1)
    print(f"HTTP {status}", file=sys.stderr)
    print(json.dumps(body, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
