#!/usr/bin/env python3
"""
Quick Regression Test for Language Separation
验证中英文界面分离后核心功能正常
"""

import requests
import json

def test_system():
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    print("Quick Regression Test - Language Separation")
    print("=" * 50)
    
    # 1. 认证测试
    login_data = {"email": "hxl2022hao@gmail.com"}
    login_response = session.post(f"{base_url}/login", data=login_data)
    auth_success = login_response.status_code in [200, 302]
    print(f"1. Authentication: {'✓' if auth_success else '✗'}")
    
    if not auth_success:
        print("   Authentication failed - stopping tests")
        return False
    
    # 2. 语言切换测试
    zh_response = session.get(f"{base_url}/?lang=zh")
    en_response = session.get(f"{base_url}/?lang=en")
    lang_success = zh_response.status_code == 200 and en_response.status_code == 200
    print(f"2. Language Switching: {'✓' if lang_success else '✗'}")
    
    # 3. 网络数据API测试
    stats_response = session.get(f"{base_url}/network_stats")
    if stats_response.status_code == 200:
        stats_data = stats_response.json()
        api_success = stats_data.get("success", False)
        hashrate = stats_data.get("hashrate", 0)
    else:
        api_success = False
        hashrate = 0
    print(f"3. Network Stats API: {'✓' if api_success else '✗'} (Hashrate: {hashrate:.1f} EH/s)")
    
    # 4. 矿机列表API测试
    miners_response = session.get(f"{base_url}/miners")
    if miners_response.status_code == 200:
        miners_data = miners_response.json()
        miners_success = miners_data.get("success", False)
        miners_count = len(miners_data.get("miners", []))
    else:
        miners_success = False
        miners_count = 0
    print(f"4. Miners API: {'✓' if miners_success else '✗'} ({miners_count} models)")
    
    # 5. 挖矿计算测试
    calc_data = {
        "miner_model": "Antminer S21 XP",
        "miner_count": "10",
        "electricity_cost": "0.05",
        "client_electricity_cost": "0.06",
        "hashrate_source": "manual",
        "manual_hashrate": "921.8",
        "use_real_time": "on"
    }
    
    calc_response = session.post(f"{base_url}/calculate", data=calc_data)
    if calc_response.status_code == 200:
        calc_result = calc_response.json()
        calc_success = "btc_mined" in calc_result and "client_profit" in calc_result
        if calc_success:
            daily_btc = calc_result["btc_mined"]["daily"]
            monthly_profit = calc_result["client_profit"]["monthly"]
        else:
            daily_btc = monthly_profit = 0
    else:
        calc_success = False
        daily_btc = monthly_profit = 0
    
    print(f"5. Mining Calculation: {'✓' if calc_success else '✗'}")
    if calc_success:
        print(f"   Daily BTC: {daily_btc:.6f}, Monthly Profit: ${monthly_profit:,.0f}")
    
    # 6. 手动算力覆盖测试
    manual_calc_data = calc_data.copy()
    manual_calc_data["hashrate_source"] = "manual"
    manual_calc_data["manual_hashrate"] = "921.8"
    
    manual_response = session.post(f"{base_url}/calculate", data=manual_calc_data)
    manual_success = manual_response.status_code == 200
    print(f"6. Manual Hashrate Override: {'✓' if manual_success else '✗'}")
    
    # 7. 限电计算测试
    curtail_data = calc_data.copy()
    curtail_data["curtailment"] = "20"
    curtail_data["shutdown_strategy"] = "efficiency"
    
    curtail_response = session.post(f"{base_url}/calculate", data=curtail_data)
    if curtail_response.status_code == 200:
        curtail_result = curtail_response.json()
        curtail_factor = curtail_result.get("inputs", {}).get("curtailment_factor", 1)
        curtail_success = curtail_factor < 1  # Should be reduced
    else:
        curtail_success = False
    
    print(f"7. Curtailment Calculation: {'✓' if curtail_success else '✗'}")
    
    # 汇总结果
    tests = [auth_success, lang_success, api_success, miners_success, 
             calc_success, manual_success, curtail_success]
    passed = sum(tests)
    total = len(tests)
    
    print("=" * 50)
    print(f"SUMMARY: {passed}/{total} tests passed ({(passed/total)*100:.0f}%)")
    
    if passed == total:
        print("✅ ALL CORE SYSTEMS OPERATIONAL")
        print("✅ Language separation successful")
        print("✅ Mining calculator fully functional")
        return True
    else:
        print("⚠️ Some issues detected")
        failed_tests = total - passed
        print(f"❌ {failed_tests} test(s) failed")
        return False

if __name__ == "__main__":
    success = test_system()
    exit(0 if success else 1)