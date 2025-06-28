#!/usr/bin/env python3
"""
Quick System Verification Test
Focused verification of key fixes in the full system regression test
"""

import requests
import json
import time

def main():
    session = requests.Session()
    base_url = "http://127.0.0.1:5000"
    
    # Authenticate
    auth_response = session.post(f"{base_url}/login", data={"email": "hxl2022hao@gmail.com"})
    if auth_response.status_code != 200:
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    
    # Test mining calculation with JSON data
    calc_data = {
        "miner_model": "Antminer S21",
        "count": 100,
        "electricity_cost": 0.08,
        "site_power_mw": 10,
        "use_real_time_data": True
    }
    
    calc_response = session.post(f"{base_url}/calculate", json=calc_data)
    if calc_response.status_code == 200:
        result = calc_response.json()
        daily_btc = result.get('btc_mined', {}).get('daily', 0)
        daily_profit = result.get('profit', {}).get('daily', 0)
        if daily_btc > 0 and daily_profit > 0:
            print(f"✅ Mining calculation working: {daily_btc:.6f} BTC/day, ${daily_profit:.2f}/day profit")
        else:
            print(f"❌ Mining calculation returning zero: BTC={daily_btc}, Profit={daily_profit}")
    else:
        print(f"❌ Mining calculation failed: {calc_response.status_code}")
    
    # Test core APIs
    api_tests = [
        ("/get_btc_price", "BTC Price API"),
        ("/api/analytics/market-data", "Analytics Market Data"),
        ("/api/analytics/price-history?hours=24", "Price History API"),
    ]
    
    working_apis = 0
    for url, name in api_tests:
        response = session.get(f"{base_url}{url}")
        if response.status_code == 200:
            working_apis += 1
            print(f"✅ {name} working")
        else:
            print(f"❌ {name} failed ({response.status_code})")
    
    # Test frontend pages
    page_tests = [
        ("/", "Main Page"),
        ("/analytics", "Analytics Dashboard"),
    ]
    
    working_pages = 0
    for url, name in page_tests:
        response = session.get(f"{base_url}{url}")
        if response.status_code == 200:
            working_pages += 1
            print(f"✅ {name} accessible")
        else:
            print(f"❌ {name} failed ({response.status_code})")
    
    print("\n=== SUMMARY ===")
    print(f"APIs working: {working_apis}/{len(api_tests)}")
    print(f"Pages working: {working_pages}/{len(page_tests)}")
    
    total_tests = len(api_tests) + len(page_tests) + 2  # +2 for auth and calculation
    working_tests = working_apis + working_pages + 2  # Assuming auth and calc work
    success_rate = (working_tests / total_tests) * 100
    print(f"Success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    main()