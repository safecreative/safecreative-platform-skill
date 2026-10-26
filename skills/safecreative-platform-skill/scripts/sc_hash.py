#!/usr/bin/env python3
"""Digest of a file for the hash-only modality of Safe Creative Platform.

Prints the lowercase hexadecimal digest of the exact bytes of FILE (or of standard input with "-"),
ready for the "hash" field of POST /events, with "hash_alg" set to the same algorithm.

    python3 sc_hash.py report.sarif                  # sha-256
    python3 sc_hash.py --alg sha-512 report.sarif
    python3 sc_hash.py --json report.sarif           # {"hash": "...", "hash_alg": "sha-256"}
"""
import argparse
import hashlib
import json
import sys

ALGORITHMS = {"sha-256": "sha256", "sha-512": "sha512"}


def digest(stream, alg="sha-256"):
    h = hashlib.new(ALGORITHMS[alg])
    for chunk in iter(lambda: stream.read(1 << 20), b""):
        h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Digest of a file for the hash-only modality.")
    parser.add_argument("file", help='file to hash, or "-" for standard input')
    parser.add_argument("--alg", choices=sorted(ALGORITHMS), default="sha-256")
    parser.add_argument("--json", action="store_true", help="print the hash and hash_alg fields as JSON")
    args = parser.parse_args()
    try:
        if args.file == "-":
            value = digest(sys.stdin.buffer, args.alg)
        else:
            with open(args.file, "rb") as f:
                value = digest(f, args.alg)
    except OSError as e:
        sys.exit(f"sc_hash: {e}")
    print(json.dumps({"hash": value, "hash_alg": args.alg}) if args.json else value)


if __name__ == "__main__":
    main()
