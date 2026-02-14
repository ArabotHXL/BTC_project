#!/usr/bin/env python3
"""
Test script for Edge v1 Commands Poll and Ack endpoints.
Tests GET /api/edge/v1/commands/poll and POST /api/edge/v1/commands/{id}/ack.
"""
import argparse
import json
import sys

import requests


def header(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def print_result(name, passed, detail=""):
    status = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
    extra = f"  ({detail})" if detail else ""
    print(f"  [{status}] {name}{extra}")
    return passed


def test_poll_401(base_url):
    url = f"{base_url}/api/edge/v1/commands/poll"
    r = requests.get(url)
    return print_result("Poll 401 without auth", r.status_code == 401, f"status={r.status_code}")


def test_ack_401(base_url):
    url = f"{base_url}/api/edge/v1/commands/0/ack"
    r = requests.post(url, json={"status": "SUCCESS"})
    return print_result("Ack 401 without auth", r.status_code == 401, f"status={r.status_code}")


def test_poll_with_auth(base_url, token):
    url = f"{base_url}/api/edge/v1/commands/poll"
    r = requests.get(url, headers=header(token))
    passed = r.status_code == 200
    detail = f"status={r.status_code}"
    if passed:
        body = r.json()
        cmd_count = len(body.get("commands", []))
        detail += f", commands={cmd_count}"
    return print_result("Poll with auth", passed, detail)


def test_ack_nonexistent(base_url, token):
    url = f"{base_url}/api/edge/v1/commands/999999/ack"
    payload = {
        "status": "SUCCESS",
        "result": {"message": "test ack"},
        "execution_time_ms": 150,
    }
    r = requests.post(url, json=payload, headers=header(token))
    passed = r.status_code in (404, 403, 200)
    return print_result("Ack non-existent command", passed, f"status={r.status_code}")


def test_ack_with_duration_ms_alias(base_url, token):
    url = f"{base_url}/api/edge/v1/commands/999999/ack"
    payload = {
        "status": "SUCCESS",
        "result": {"message": "test duration_ms alias"},
        "duration_ms": 200,
    }
    r = requests.post(url, json=payload, headers=header(token))
    passed = r.status_code in (404, 403, 200)
    return print_result("Ack with duration_ms alias", passed, f"status={r.status_code}")


def test_poll_returns_expected_fields(base_url, token):
    url = f"{base_url}/api/edge/v1/commands/poll"
    r = requests.get(url, headers=header(token))
    if r.status_code != 200:
        return print_result("Poll response has expected fields", False, f"status={r.status_code}")
    body = r.json()
    expected_keys = {"commands", "server_time"}
    found_keys = set(body.keys())
    has_required = expected_keys.issubset(found_keys)
    return print_result("Poll response has expected fields", has_required, f"keys={sorted(found_keys)}")


def main():
    parser = argparse.ArgumentParser(description="Test Edge v1 Commands Poll & Ack endpoints")
    parser.add_argument("--base-url", default="http://localhost:5000", help="Base URL of the server")
    parser.add_argument("--token", required=True, help="Bearer token for authentication")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Edge v1 Commands Test Suite")
    print(f"Base URL: {args.base_url}")
    print(f"{'='*60}\n")

    results = []
    results.append(test_poll_401(args.base_url))
    results.append(test_ack_401(args.base_url))
    results.append(test_poll_with_auth(args.base_url, args.token))
    results.append(test_poll_returns_expected_fields(args.base_url, args.token))
    results.append(test_ack_nonexistent(args.base_url, args.token))
    results.append(test_ack_with_duration_ms_alias(args.base_url, args.token))

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} passed")
    print(f"{'='*60}\n")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
