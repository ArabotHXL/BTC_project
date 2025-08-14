#!/usr/bin/env python3
"""
Gmail SMTP邮件服务测试
Test Gmail SMTP Email Service
"""
import os
import sys
import logging
from gmail_oauth_service import send_verification_email_smtp

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gmail_smtp():
    """测试Gmail SMTP邮件发送"""
    print("=" * 60)
    print("Gmail SMTP邮件服务测试")
    print("=" * 60)
    
    # 检查配置
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_pass = os.environ.get('GMAIL_APP_PASS')
    
    if not gmail_user:
        print("❌ GMAIL_USER环境变量未设置")
        return False
    
    if not gmail_pass:
        print("❌ GMAIL_APP_PASS环境变量未设置")
        return False
    
    print(f"✓ Gmail用户: {gmail_user}")
    print(f"✓ App密码: {'*' * len(gmail_pass[:4])}...")
    
    # 测试邮件地址
    test_email = gmail_user  # 发送给自己进行测试
    test_url = "https://example.com/verify-test-123"
    
    print(f"\n发送测试邮件到: {test_email}")
    print(f"测试验证链接: {test_url}")
    
    try:
        # 发送测试邮件
        result = send_verification_email_smtp(test_email, test_url)
        
        if result:
            print("\n✅ 邮件发送成功！")
            print("请检查您的Gmail收件箱")
            print("主题: BTC Mining Calculator - 邮箱验证")
            return True
        else:
            print("\n❌ 邮件发送失败")
            return False
            
    except Exception as e:
        print(f"\n❌ 邮件发送异常: {e}")
        return False

if __name__ == "__main__":
    success = test_gmail_smtp()
    sys.exit(0 if success else 1)