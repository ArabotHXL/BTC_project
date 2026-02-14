#!/usr/bin/env python3
"""
Test script for Edge v1 Telemetry Ingest endpoints.
Tests POST /api/edge/v1/telemetry/ingest and /api/edge/v1/telemetry/batch (alias).
"""
import argparse
import gzip
import json
import sys
from datetime import datetime, timezone

import requests


def header(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def print_result(name, passed, detail=""):
    status = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
    extra = f"  ({detail})" if detail else ""
    print(f"  [{status}] {name}{extra}")
    return passed


def test_401_no_auth(base_url):
    url = f"{base_url}/api/edge/v1/telemetry/ingest"
    r = requests.post(url, json=[{"miner_id": "test"}])
    return print_result("401 without auth header", r.status_code == 401, f"status={r.status_code}")


def test_plain_list(base_url, token, endpoint="/api/edge/v1/telemetry/ingest"):
    url = f"{base_url}{endpoint}"
    payload = [
        {
            "worker_id": "test-miner-001",
            "hashrate_rt": 85.3,
            "temperature": 62,
        }
    ]
    r = requests.post(url, json=payload, headers=header(token))
    passed = r.status_code in (200, 201, 202)
    return print_result(f"Plain list format -> {endpoint}", passed, f"status={r.status_code}")


def test_envelope_v1(base_url, token):
    url = f"{base_url}/api/edge/v1/telemetry/ingest"
    payload = {
        "format": "telemetry_envelope.v1",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "miners": [
            {
                "worker_id": "test-miner-002",
                "hashrate_rt": 92.1,
                "temperature": 58,
            }
        ],
    }
    r = requests.post(url, json=payload, headers=header(token))
    passed = r.status_code in (200, 201, 202)
    return print_result("Telemetry envelope v1 format", passed, f"status={r.status_code}")


def test_legacy_dict(base_url, token):
    url = f"{base_url}/api/edge/v1/telemetry/ingest"
    payload = {
        "device_id": "test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "miners": [
            {
                "worker_id": "test-miner-003",
                "hashrate_rt": 78.5,
                "temperature": 65,
            }
        ],
    }
    r = requests.post(url, json=payload, headers=header(token))
    passed = r.status_code in (200, 201, 202)
    return print_result("Legacy dict format", passed, f"status={r.status_code}")


def test_gzip_compression(base_url, token):
    url = f"{base_url}/api/edge/v1/telemetry/ingest"
    payload = [
        {
            "worker_id": "test-miner-gzip",
            "hashrate_rt": 100.0,
            "temperature": 60,
        }
    ]
    compressed = gzip.compress(json.dumps(payload).encode("utf-8"))
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Content-Encoding": "gzip",
    }
    r = requests.post(url, data=compressed, headers=headers)
    passed = r.status_code in (200, 201, 202)
    return print_result("Gzip compressed payload", passed, f"status={r.status_code}")


def test_payload_enc_rejected(base_url, token):
    url = f"{base_url}/api/edge/v1/telemetry/ingest"
    payload = {
        "payload_enc": "base64-encrypted-blob-here",
        "iv": "some-iv",
    }
    r = requests.post(url, json=payload, headers=header(token))
    passed = r.status_code == 422
    return print_result("payload_enc rejection (expect 422)", passed, f"status={r.status_code}")


def test_batch_alias(base_url, token):
    return test_plain_list(base_url, token, endpoint="/api/edge/v1/telemetry/batch")


def main():
    parser = argparse.ArgumentParser(description="Test Edge v1 Telemetry Ingest endpoints")
    parser.add_argument("--base-url", default="http://localhost:5000", help="Base URL of the server")
    parser.add_argument("--token", required=True, help="Bearer token for authentication")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Edge v1 Telemetry Test Suite")
    print(f"Base URL: {args.base_url}")
    print(f"{'='*60}\n")

    results = []
    results.append(test_401_no_auth(args.base_url))
    results.append(test_plain_list(args.base_url, args.token))
    results.append(test_envelope_v1(args.base_url, args.token))
    results.append(test_legacy_dict(args.base_url, args.token))
    results.append(test_gzip_compression(args.base_url, args.token))
    results.append(test_payload_enc_rejected(args.base_url, args.token))
    results.append(test_batch_alias(args.base_url, args.token))

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} passed")
    print(f"{'='*60}\n")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
