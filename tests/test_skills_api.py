"""
Skills API Integration Tests
Run: python tests/test_skills_api.py

Requires the server to be running on port 5000.
Uses the dev API key for authentication.
"""
import json
import sys
import requests

BASE = "http://localhost:5000"
HEADERS = {"X-API-Key": "hsi_dev_key_2025", "Content-Type": "application/json"}
passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  PASS  {name}")
        passed += 1
    except AssertionError as e:
        print(f"  FAIL  {name}: {e}")
        failed += 1
    except Exception as e:
        print(f"  ERROR {name}: {e}")
        failed += 1

def test_list_skills():
    r = requests.get(f"{BASE}/api/skills", headers=HEADERS)
    assert r.status_code == 200, f"status={r.status_code}"
    data = r.json()
    assert data["ok"] is True
    assert data["count"] == 5
    ids = [s["id"] for s in data["skills"]]
    assert "telemetry_snapshot" in ids
    assert "alert_triage" in ids
    assert "rca_quick_diagnose" in ids
    assert "ticket_draft" in ids
    assert "curtailment_dry_run" in ids

def test_get_skill():
    r = requests.get(f"{BASE}/api/skills/telemetry_snapshot", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["skill"]["id"] == "telemetry_snapshot"
    assert "input_schema" in data["skill"]

def test_get_skill_not_found():
    r = requests.get(f"{BASE}/api/skills/nonexistent", headers=HEADERS)
    assert r.status_code == 404

def test_run_telemetry_snapshot():
    r = requests.post(f"{BASE}/api/skills/telemetry_snapshot/run", headers=HEADERS,
                      json={"miner_id": "test-miner-001", "window_min": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["skill_id"] == "telemetry_snapshot"
    assert data["audit_id"] is not None
    assert "data" in data

def test_run_ticket_draft():
    r = requests.post(f"{BASE}/api/skills/ticket_draft/run", headers=HEADERS,
                      json={"miner_id": "test-miner-001", "issue": "overheat"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "title" in data["data"]

def test_run_missing_required():
    r = requests.post(f"{BASE}/api/skills/telemetry_snapshot/run", headers=HEADERS, json={})
    assert r.status_code == 400
    data = r.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "INVALID_INPUT"

def test_auth_required():
    r = requests.get(f"{BASE}/api/skills")
    assert r.status_code == 401

def test_run_nonexistent_skill():
    r = requests.post(f"{BASE}/api/skills/fake_skill/run", headers=HEADERS, json={})
    assert r.status_code == 404

if __name__ == "__main__":
    print("Skills API Integration Tests")
    print("=" * 40)
    test("List all skills", test_list_skills)
    test("Get skill spec", test_get_skill)
    test("Get skill 404", test_get_skill_not_found)
    test("Run telemetry_snapshot", test_run_telemetry_snapshot)
    test("Run ticket_draft", test_run_ticket_draft)
    test("Run with missing required field", test_run_missing_required)
    test("Auth required without key", test_auth_required)
    test("Run nonexistent skill", test_run_nonexistent_skill)
    print("=" * 40)
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(1 if failed > 0 else 0)
