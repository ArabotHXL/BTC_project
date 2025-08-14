#!/usr/bin/env python3
"""
测试双语邮件验证功能
Test bilingual email verification functionality
"""

import os
import sys
import logging
from flask import Flask, g

# 设置日志
logging.basicConfig(level=logging.INFO)

# 导入邮件服务
from gmail_oauth_service import send_verification_email_smtp

def test_chinese_email():
    """测试中文邮件模板"""
    print("=" * 60)
    print("🧪 测试中文邮件模板 / Testing Chinese Email Template")
    print("=" * 60)
    
    test_email = "test@example.com"
    verification_url = "https://example.com/verify-email/test-token-chinese"
    
    try:
        result = send_verification_email_smtp(test_email, verification_url, 'zh')
        if result:
            print("✅ 中文邮件发送成功 / Chinese email sent successfully")
        else:
            print("❌ 中文邮件发送失败 / Chinese email failed")
    except Exception as e:
        print(f"❌ 中文邮件发送异常 / Chinese email exception: {e}")

def test_english_email():
    """测试英文邮件模板"""
    print("\n" + "=" * 60)
    print("🧪 测试英文邮件模板 / Testing English Email Template")
    print("=" * 60)
    
    test_email = "test@example.com"
    verification_url = "https://example.com/verify-email/test-token-english"
    
    try:
        result = send_verification_email_smtp(test_email, verification_url, 'en')
        if result:
            print("✅ 英文邮件发送成功 / English email sent successfully")
        else:
            print("❌ 英文邮件发送失败 / English email failed")
    except Exception as e:
        print(f"❌ 英文邮件发送异常 / English email exception: {e}")

def test_app_integration():
    """测试与应用的集成"""
    print("\n" + "=" * 60)
    print("🧪 测试应用集成 / Testing App Integration")
    print("=" * 60)
    
    # 创建测试Flask应用上下文
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-key'
    
    with app.app_context():
        # 模拟中文界面用户
        with app.test_request_context('/?lang=zh'):
            g.language = 'zh'
            print(f"🌐 模拟中文界面用户，语言设置: {g.get('language', 'zh')}")
            
        # 模拟英文界面用户
        with app.test_request_context('/?lang=en'):
            g.language = 'en'
            print(f"🌐 模拟英文界面用户，语言设置: {g.get('language', 'zh')}")

def main():
    """主测试函数"""
    print("🚀 开始双语邮件验证功能测试")
    print("🚀 Starting Bilingual Email Verification Tests")
    print()
    
    # 检查环境变量
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_pass = os.environ.get('GMAIL_APP_PASS')
    
    if not gmail_user or not gmail_pass:
        print("⚠️  Gmail SMTP配置未找到，邮件将显示在控制台")
        print("⚠️  Gmail SMTP config not found, emails will display in console")
    else:
        print(f"✅ Gmail SMTP配置已找到: {gmail_user}")
        print("✅ Gmail SMTP config found")
    
    print()
    
    # 运行测试
    test_chinese_email()
    test_english_email()
    test_app_integration()
    
    print("\n" + "=" * 60)
    print("🎉 双语邮件测试完成！")
    print("🎉 Bilingual Email Tests Completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()