#!/usr/bin/env python3
"""
最终99%认证测试 - 诊断和修复认证问题
"""

import requests
import json
import time

def debug_auth_flow(email):
    """调试单个邮箱的认证流程"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    print(f"\n🔍 调试 {email} 认证流程:")
    
    try:
        # 1. 获取登录页面
        login_page = session.get(f"{base_url}/login", timeout=5)
        print(f"  1. 登录页面: {login_page.status_code}")
        
        # 2. 发送登录请求
        login_response = session.post(f"{base_url}/login", 
                                    data={"email": email}, 
                                    timeout=10,
                                    allow_redirects=False)  # 不自动重定向，查看原始响应
        print(f"  2. 登录请求: {login_response.status_code}")
        print(f"  3. 重定向位置: {login_response.headers.get('Location', 'None')}")
        
        # 3. 检查会话状态
        if login_response.status_code in [302, 303]:
            # 手动跟随重定向
            redirect_url = login_response.headers.get('Location')
            if redirect_url:
                if redirect_url.startswith('/'):
                    redirect_url = base_url + redirect_url
                
                final_response = session.get(redirect_url, timeout=5)
                print(f"  4. 重定向后页面: {final_response.status_code}")
                print(f"  5. 最终URL: {final_response.url}")
                
                # 检查页面内容
                if "login" in final_response.url.lower():
                    print(f"  ❌ 仍在登录页面")
                    return False
                elif final_response.status_code == 200:
                    print(f"  ✅ 成功访问主页")
                    return True
        
        # 4. 直接访问主页测试
        main_response = session.get(f"{base_url}/", timeout=5)
        print(f"  6. 直接访问主页: {main_response.status_code}")
        print(f"  7. 主页URL: {main_response.url}")
        
        if main_response.status_code == 200 and "login" not in main_response.url.lower():
            print(f"  ✅ 认证成功")
            return True
        else:
            print(f"  ❌ 认证失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        return False

def run_comprehensive_auth_test():
    """运行全面认证测试"""
    test_emails = [
        "admin@example.com",
        "hxl2022hao@gmail.com", 
        "user@example.com",
        "site@example.com",
        "testing123@example.com"
    ]
    
    success_count = 0
    
    for email in test_emails:
        if debug_auth_flow(email):
            success_count += 1
        time.sleep(1)  # 避免太快请求
    
    success_rate = success_count / len(test_emails)
    print(f"\n📊 最终结果:")
    print(f"认证成功率: {success_rate*100:.1f}% ({success_count}/{len(test_emails)})")
    
    if success_rate >= 0.95:
        print("🎯 达到99%认证标准！")
        return True
    else:
        print("⚠️ 未达到99%标准，需要进一步优化")
        return False

if __name__ == "__main__":
    print("🎯 开始最终99%认证诊断测试")
    success = run_comprehensive_auth_test()
    exit(0 if success else 1)