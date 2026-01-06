#!/usr/bin/env python3
"""Complete API Workflow Test"""
import requests
import json

BASE_URL = "http://localhost:3000"

def test_workflow():
    print("=" * 60)
    print("HashInsight Demo - API Workflow Test")
    print("=" * 60)
    
    # 1. Get actors
    r = requests.get(f"{BASE_URL}/api/actors?tenant_id=1")
    actors = r.json()
    owner_token = None
    operator_token = None
    for a in actors:
        if a["role"] == "owner":
            owner_token = a["api_token"]
        if a["role"] == "operator":
            operator_token = a["api_token"]
    print(f"✓ Got actors: owner={owner_token[:8]}..., operator={operator_token[:8]}...")
    
    # 2. List sites as operator
    headers = {"Authorization": f"Bearer {operator_token}"}
    r = requests.get(f"{BASE_URL}/api/sites?tenant_id=1", headers=headers)
    sites = r.json()
    print(f"✓ Sites available: {[s['name'] for s in sites]}")
    
    # 3. List miners
    r = requests.get(f"{BASE_URL}/api/miners?site_id={sites[0]['id']}", headers=headers)
    miners = r.json()
    print(f"✓ Miners: {len(miners)} found")
    if miners:
        m = miners[0]
        print(f"  - {m['name']}: mode={m['credential_mode']}, display={m['display_credential']}")
    
    # 4. Whoami
    r = requests.get(f"{BASE_URL}/api/whoami", headers=headers)
    me = r.json()
    print(f"✓ Whoami: {me['actor_name']} (role={me['role']})")
    
    # 5. Create Change Request
    if miners:
        miner_id = miners[0]["id"]
        cr_data = {
            "tenant_id": 1,
            "site_id": sites[0]["id"],
            "request_type": "REVEAL_CREDENTIAL",
            "target_type": "miner",
            "target_id": miner_id,
            "requested_action": {"action": "reveal"},
            "reason": "API test - reveal credential"
        }
        r = requests.post(f"{BASE_URL}/api/changes", json=cr_data, headers=headers)
        if r.status_code == 200:
            cr = r.json()
            print(f"✓ Created CR #{cr['id']}: {cr['status']}")
            
            # 6. Approve CR as owner
            owner_headers = {"Authorization": f"Bearer {owner_token}"}
            r = requests.post(f"{BASE_URL}/api/changes/{cr['id']}/approve", headers=owner_headers)
            if r.status_code == 200:
                result = r.json()
                print(f"✓ Approved CR: {result['status']}")
                
                # 7. Execute CR
                r = requests.post(f"{BASE_URL}/api/changes/{cr['id']}/execute", headers=owner_headers)
                if r.status_code == 200:
                    result = r.json()
                    print(f"✓ Executed CR: revealed={result['result']}")
                else:
                    print(f"✗ Execute failed: {r.text}")
            else:
                print(f"✗ Approve failed: {r.text}")
        else:
            print(f"✗ CR creation failed: {r.text}")
    
    # 8. Audit log
    r = requests.get(f"{BASE_URL}/api/audit?tenant_id=1&limit=5")
    audit = r.json()
    print(f"✓ Recent audit events: {len(audit)} entries")
    for e in audit[:3]:
        print(f"  - {e['event_type']}: {e['actor_name']} @ {e['created_at'][:19]}")
    
    # 9. Discovery simulation
    disc_data = {"site_id": sites[0]["id"], "cidr": "10.0.0.0/24", "ports": [4028], "simulate": True}
    r = requests.post(f"{BASE_URL}/api/discovery/scan", json=disc_data, headers=headers)
    if r.status_code == 200:
        disc = r.json()
        print(f"✓ Discovery: found {disc['count']} candidates")
    
    print("\n" + "=" * 60)
    print("API WORKFLOW TEST COMPLETE ✓")
    print("=" * 60)

if __name__ == "__main__":
    test_workflow()
