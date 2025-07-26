#!/usr/bin/env python3
"""
认证系统优化修复 - 确保所有测试邮箱都能正常工作
"""

import requests
import time

def test_direct_auth():
    """直接测试认证流程"""
    base_url = "http://localhost:5000"
    
    test_emails = [
        "admin@example.com",
        "hxl2022hao@gmail.com", 
        "user@example.com",
        "site@example.com",
        "testing123@example.com"
    ]
    
    success_count = 0
    
    for email in test_emails:
        session = requests.Session()
        try:
            # 1. 发送登录请求
            login_response = session.post(f"{base_url}/login", 
                                        data={"email": email}, 
                                        timeout=10,
                                        allow_redirects=True)
            
            # 2. 检查是否成功（状态码200且无login关键字）
            if login_response.status_code == 200:
                # 3. 尝试访问主页确认已登录
                main_response = session.get(f"{base_url}/", timeout=5)
                if (main_response.status_code == 200 and 
                    "login" not in main_response.url.lower() and
                    "email" not in main_response.text.lower()[:1000]):  # 检查是否还在登录页面
                    print(f"✅ {email} - 认证成功")
                    success_count += 1
                else:
                    print(f"❌ {email} - 登录后无法访问主页")
            else:
                print(f"❌ {email} - 登录请求失败: {login_response.status_code}")
                
        except Exception as e:
            print(f"❌ {email} - 异常: {str(e)}")
    
    success_rate = success_count / len(test_emails)
    print(f"\n认证成功率: {success_rate*100:.1f}% ({success_count}/{len(test_emails)})")
    
    if success_rate >= 0.95:
        print("🎯 认证系统已达到95%+标准")
        return True
    else:
        print("⚠️ 认证系统需要进一步优化")
        return False

if __name__ == "__main__":
    print("🔧 开始认证系统优化验证")
    success = test_direct_auth()
    exit(0 if success else 1)