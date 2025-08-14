import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Optional

# 设置日志
logging.basicConfig(level=logging.DEBUG)

class GmailService:
    """Gmail SMTP邮件发送服务"""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email = os.environ.get('GMAIL_EMAIL', 'hxl2022hao@gmail.com')
        self.password = os.environ.get('GMAIL_APP_PASSWORD')  # Gmail应用专用密码
        self.from_name = "BTC Mining Calculator"
    
    def send_verification_email(self, to_email: str, verification_url: str) -> bool:
        """发送邮箱验证邮件"""
        if not self.password:
            logging.error("GMAIL_APP_PASSWORD 环境变量未设置")
            return False
        
        subject = "BTC Mining Calculator - 邮箱验证"
        
        # HTML邮件内容
        html_body = f"""
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #f8d000, #ffd700); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="color: #000; margin: 0; font-size: 28px; font-weight: bold;">
                    🚀 BTC Mining Calculator
                </h1>
                <p style="color: #333; margin: 10px 0 0 0; font-size: 16px;">
                    专业的比特币挖矿盈利计算平台
                </p>
            </div>
            
            <div style="background: #ffffff; padding: 30px; border: 1px solid #ddd; border-top: none;">
                <h2 style="color: #f8d000; margin-bottom: 20px; font-size: 24px;">
                    欢迎注册！
                </h2>
                
                <p style="font-size: 16px; margin-bottom: 20px;">
                    感谢您注册我们的比特币挖矿计算平台！为了确保账户安全，请验证您的邮箱地址。
                </p>
                
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{verification_url}" 
                       style="background: linear-gradient(135deg, #f8d000, #ffd700); 
                              color: #000; 
                              padding: 15px 35px; 
                              text-decoration: none; 
                              border-radius: 50px; 
                              font-weight: bold; 
                              font-size: 18px;
                              display: inline-block;
                              box-shadow: 0 4px 15px rgba(248, 208, 0, 0.3);
                              transition: all 0.3s ease;">
                        🔐 验证邮箱地址
                    </a>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #f8d000; margin: 25px 0;">
                    <p style="margin: 0; font-size: 14px; color: #666;">
                        <strong>链接无法点击？</strong><br>
                        请复制以下URL到浏览器地址栏：<br>
                        <code style="word-break: break-all; background: #e9ecef; padding: 5px; border-radius: 3px; font-size: 12px;">
                            {verification_url}
                        </code>
                    </p>
                </div>
                
                <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 30px;">
                    <p style="color: #666; font-size: 14px; margin: 5px 0;">
                        ⏰ <strong>有效期：</strong>此链接将在24小时后失效
                    </p>
                    <p style="color: #666; font-size: 14px; margin: 5px 0;">
                        🔒 <strong>安全提醒：</strong>如果您没有注册此账户，请忽略这封邮件
                    </p>
                </div>
            </div>
            
            <div style="background: #2c3e50; color: #ecf0f1; padding: 20px; border-radius: 0 0 10px 10px; text-align: center;">
                <p style="margin: 0; font-size: 14px;">
                    © 2025 BTC Mining Calculator | 专业挖矿投资分析平台
                </p>
                <p style="margin: 5px 0 0 0; font-size: 12px; opacity: 0.8;">
                    此邮件由系统自动发送，请勿直接回复
                </p>
            </div>
        </body>
        </html>
        """
        
        # 纯文本版本
        text_body = f"""
BTC Mining Calculator - 邮箱验证

欢迎注册！

感谢您注册我们的比特币挖矿计算平台！

请复制以下链接到浏览器验证您的邮箱地址：
{verification_url}

重要信息：
• 此链接有效期为24小时
• 如果您没有注册此账户，请忽略这封邮件

BTC Mining Calculator 团队
专业挖矿投资分析平台
        """
        
        return self._send_email(to_email, subject, html_body, text_body)
    
    def send_password_reset_email(self, to_email: str, reset_url: str) -> bool:
        """发送密码重置邮件"""
        if not self.password:
            logging.error("GMAIL_APP_PASSWORD 环境变量未设置")
            return False
        
        subject = "BTC Mining Calculator - 密码重置请求"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #f8d000; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="color: #000; margin: 0;">🔐 密码重置请求</h2>
            </div>
            <div style="background: #ffffff; padding: 30px; border: 1px solid #ddd;">
                <p>您请求重置 BTC Mining Calculator 账户的密码。</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background: #f8d000; color: #000; padding: 15px 30px; 
                              text-decoration: none; border-radius: 5px; font-weight: bold;">
                        重置密码
                    </a>
                </div>
                <p>链接: {reset_url}</p>
                <p style="color: #666; font-size: 12px;">
                    此链接有效期为1小时。如果您没有请求重置密码，请忽略这封邮件。
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
BTC Mining Calculator - 密码重置请求

您请求重置账户密码。

请复制以下链接到浏览器重置密码：
{reset_url}

此链接有效期为1小时。如果您没有请求重置密码，请忽略这封邮件。
        """
        
        return self._send_email(to_email, subject, html_body, text_body)
    
    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """发送邮件的核心方法"""
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.email}>"
            msg['To'] = to_email
            msg['Subject'] = Header(subject, 'utf-8')
            
            # 添加文本和HTML部分
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            html_part = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # 连接Gmail SMTP服务器
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # 启用TLS加密
                server.login(self.email, self.password)
                server.send_message(msg)
            
            logging.info(f"Gmail邮件发送成功到 {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logging.error("Gmail认证失败：请检查邮箱和应用专用密码")
            return False
        except smtplib.SMTPRecipientsRefused:
            logging.error(f"收件人被拒绝：{to_email}")
            return False
        except Exception as e:
            logging.error(f"Gmail发送邮件时出错: {str(e)}")
            return False

# 创建全局Gmail服务实例
gmail_service = GmailService()

def send_verification_email_gmail(to_email: str, verification_url: str) -> bool:
    """发送Gmail验证邮件的便捷函数"""
    return gmail_service.send_verification_email(to_email, verification_url)

def send_password_reset_email_gmail(to_email: str, reset_url: str) -> bool:
    """发送Gmail密码重置邮件的便捷函数"""
    return gmail_service.send_password_reset_email(to_email, reset_url)