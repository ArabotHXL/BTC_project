import os
import requests
import logging
from typing import Optional

# 设置日志
logging.basicConfig(level=logging.DEBUG)

class ElasticEmailService:
    """Elastic Email邮件发送服务"""
    
    def __init__(self):
        self.api_key = os.environ.get('ELASTIC_EMAIL_API_KEY')
        self.base_url = "https://api.elasticemail.com/v2"
        self.from_email = os.environ.get('EMAIL_FROM', 'noreply@btc-mining-calculator.com')
        self.from_name = os.environ.get('EMAIL_FROM_NAME', 'BTC Mining Calculator')
    
    def send_verification_email(self, to_email: str, verification_url: str) -> bool:
        """发送邮箱验证邮件"""
        if not self.api_key:
            logging.error("ELASTIC_EMAIL_API_KEY 环境变量未设置")
            return False
        
        subject = "BTC Mining Calculator - 邮箱验证"
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #f8d000;">欢迎注册 BTC Mining Calculator</h2>
                <p>感谢您注册我们的比特币挖矿计算平台！</p>
                <p>请点击下面的链接验证您的邮箱地址：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background-color: #f8d000; color: #000; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; font-weight: bold;">
                        验证邮箱
                    </a>
                </div>
                <p>如果按钮无法点击，请复制以下链接到浏览器：</p>
                <p style="word-break: break-all; color: #666;">{verification_url}</p>
                <p style="color: #666; font-size: 12px; margin-top: 40px;">
                    此链接有效期为24小时。如果您没有注册此账户，请忽略这封邮件。
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        欢迎注册 BTC Mining Calculator
        
        感谢您注册我们的比特币挖矿计算平台！
        
        请复制以下链接到浏览器验证您的邮箱地址：
        {verification_url}
        
        此链接有效期为24小时。如果您没有注册此账户，请忽略这封邮件。
        """
        
        return self._send_email(to_email, subject, html_body, text_body)
    
    def send_password_reset_email(self, to_email: str, reset_url: str) -> bool:
        """发送密码重置邮件"""
        if not self.api_key:
            logging.error("ELASTIC_EMAIL_API_KEY 环境变量未设置")
            return False
        
        subject = "BTC Mining Calculator - 密码重置"
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #f8d000;">密码重置请求</h2>
                <p>您请求重置 BTC Mining Calculator 账户的密码。</p>
                <p>请点击下面的链接重置您的密码：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #f8d000; color: #000; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; font-weight: bold;">
                        重置密码
                    </a>
                </div>
                <p>如果按钮无法点击，请复制以下链接到浏览器：</p>
                <p style="word-break: break-all; color: #666;">{reset_url}</p>
                <p style="color: #666; font-size: 12px; margin-top: 40px;">
                    此链接有效期为1小时。如果您没有请求重置密码，请忽略这封邮件。
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        密码重置请求
        
        您请求重置 BTC Mining Calculator 账户的密码。
        
        请复制以下链接到浏览器重置您的密码：
        {reset_url}
        
        此链接有效期为1小时。如果您没有请求重置密码，请忽略这封邮件。
        """
        
        return self._send_email(to_email, subject, html_body, text_body)
    
    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """发送邮件的核心方法"""
        try:
            data = {
                'apikey': self.api_key,
                'from': self.from_email,
                'fromName': self.from_name,
                'to': to_email,
                'subject': subject,
                'bodyHtml': html_body,
                'bodyText': text_body,
                'isTransactional': 'true'
            }
            
            response = requests.post(f"{self.base_url}/email/send", data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', False):
                    logging.info(f"邮件发送成功到 {to_email}")
                    return True
                else:
                    logging.error(f"Elastic Email API错误: {result.get('error', '未知错误')}")
                    return False
            else:
                logging.error(f"HTTP错误 {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"发送邮件时出错: {str(e)}")
            return False

# 创建全局邮件服务实例
email_service = ElasticEmailService()

def send_verification_email(to_email: str, verification_url: str) -> bool:
    """发送验证邮件的便捷函数"""
    return email_service.send_verification_email(to_email, verification_url)

def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """发送密码重置邮件的便捷函数"""
    return email_service.send_password_reset_email(to_email, reset_url)