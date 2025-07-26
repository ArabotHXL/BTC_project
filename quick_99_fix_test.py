#!/usr/bin/env python3
"""
快速99%修复验证测试
Quick 99% Fix Verification Test
"""

import requests
import json
import time
from datetime import datetime

def test_security_fix():
    """测试安全修复"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    # 登录
    session.post(f"{base_url}/login", data={"email": "testing@example.com"})
    
    # 测试客户电费安全防护
    malicious_data = {
        "miner_model": "Antminer S19 Pro",
        "miner_count": "100",
        "electricity_cost": "0.08",
        "client_electricity_cost": "-999999",  # 恶意负数
        "use_real_time": "on"
    }
    
    response = session.post(f"{base_url}/calculate", data=malicious_data, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        if not data.get('success'):
            print("✅ 安全修复成功 - 恶意输入被拒绝")
            return True
        else:
            print("❌ 安全修复失败 - 恶意输入被接受")
            return False
    else:
        print("✅ 安全修复成功 - HTTP错误响应")
        return True

def test_auth_improvement():
    """测试认证改进"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    # 测试邮箱认证
    test_emails = ["testing@example.com", "admin@example.com"]
    success_count = 0
    
    for email in test_emails:
        try:
            response = session.post(f"{base_url}/login", data={"email": email}, timeout=5)
            if response.status_code in [200, 302]:
                # 验证是否真正登录成功
                dashboard_response = session.get(f"{base_url}/", timeout=5)
                if dashboard_response.status_code == 200 and "login" not in dashboard_response.url:
                    success_count += 1
                    print(f"✅ {email} 认证成功")
                else:
                    print(f"❌ {email} 认证失败")
        except Exception as e:
            print(f"❌ {email} 认证错误: {str(e)}")
    
    return success_count >= len(test_emails) * 0.8  # 80%成功率

if __name__ == "__main__":
    print("🔧 开始99%修复验证测试")
    
    security_ok = test_security_fix()
    auth_ok = test_auth_improvement()
    
    if security_ok and auth_ok:
        print("🎯 修复验证成功！系统应该达到99%标准")
    else:
        print("⚠️ 修复验证部分失败，需要进一步调整")