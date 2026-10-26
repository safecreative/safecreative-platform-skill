#!/usr/bin/env python3
"""Verification of a Safe Creative Platform webhook delivery.

The signature is X-SC-Signature: v1=<hex>, where <hex> is HMAC-SHA256 with the endpoint secret (whsec_...)
over "<X-SC-Timestamp>.<raw body>". Exits 0 if the delivery is authentic and recent, 1 otherwise.

    python3 sc_verify_webhook.py --secret "$SC_WEBHOOK_SECRET" --timestamp 1761206400 \
        --signature "v1=4f1c..." --body-file delivery.json

As a module: verify(secret, timestamp_header, signature_header, raw_body_bytes) -> bool.
"""
import argparse
import hashlib
import hmac
import sys
import time

TOLERANCE_SECONDS = 300


def verify(secret, timestamp, signature, body, now=None, tolerance=TOLERANCE_SECONDS):
    """True if the signature matches the raw body and the timestamp is within the tolerance."""
    if not secret or not timestamp or not signature or not signature.startswith("v1="):
        return False
    try:
        sent = int(timestamp)
    except ValueError:
        return False
    if abs((time.time() if now is None else now) - sent) > tolerance:
        return False
    expected = hmac.new(secret.encode("utf-8"), timestamp.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[3:])


def main():
    parser = argparse.ArgumentParser(description="Verify a Safe Creative Platform webhook delivery.")
    parser.add_argument("--secret", required=True, help="endpoint secret (whsec_...)")
    parser.add_argument("--timestamp", required=True, help="value of the X-SC-Timestamp header")
    parser.add_argument("--signature", required=True, help="value of the X-SC-Signature header (v1=<hex>)")
    parser.add_argument("--body-file", required=True, help='file with the raw request body, or "-" for standard input')
    parser.add_argument("--tolerance", type=int, default=TOLERANCE_SECONDS, help="maximum age in seconds (default 300)")
    args = parser.parse_args()
    body = sys.stdin.buffer.read() if args.body_file == "-" else open(args.body_file, "rb").read()
    ok = verify(args.secret, args.timestamp, args.signature, body, tolerance=args.tolerance)
    print("valid" if ok else "invalid")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
