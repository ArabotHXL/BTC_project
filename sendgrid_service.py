import os
import sys
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

class SendGridService:
    def __init__(self):
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        self.from_email = 'hxl2022hao@gmail.com'  # 发件人邮箱
        self.from_name = 'BTC Mining Calculator'
        
        if not self.api_key:
            logging.error("SENDGRID_API_KEY环境变量未设置")
            
    def send_verification_email(self, to_email, verification_url):
        """发送邮箱验证邮件"""
        if not self.api_key:
            logging.error("SendGrid API密钥未配置")
            return False
            
        try:
            sg = SendGridAPIClient(self.api_key)
            
            # HTML邮件内容
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>邮箱验证 - BTC Mining Calculator</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: #ffd700; color: #1e3c72; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 邮箱验证</h1>
                        <p>BTC Mining Calculator</p>
                    </div>
                    <div class="content">
                        <h2>欢迎注册BTC Mining Calculator！</h2>
                        <p>感谢您注册我们的比特币挖矿计算器平台。请点击下面的按钮验证您的邮箱地址：</p>
                        
                        <div style="text-align: center;">
                            <a href="{verification_url}" class="button">验证邮箱地址</a>
                        </div>
                        
                        <p>如果上面的按钮无法点击，请复制以下链接到浏览器地址栏：</p>
                        <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px;">
                            {verification_url}
                        </p>
                        
                        <p><strong>注意：</strong></p>
                        <ul>
                            <li>此验证链接24小时内有效</li>
                            <li>验证成功后即可使用所有功能</li>
                            <li>如有问题请联系客服</li>
                        </ul>
                    </div>
                    <div class="footer">
                        <p>© 2025 BTC Mining Calculator. All rights reserved.</p>
                        <p>这是一封自动发送的邮件，请勿回复。</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # 纯文本内容
            text_content = f"""
            邮箱验证 - BTC Mining Calculator
            
            欢迎注册BTC Mining Calculator！
            
            请访问以下链接验证您的邮箱地址：
            {verification_url}
            
            注意：
            - 此验证链接24小时内有效
            - 验证成功后即可使用所有功能
            - 如有问题请联系客服
            
            © 2025 BTC Mining Calculator
            这是一封自动发送的邮件，请勿回复。
            """
            
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject="BTC Mining Calculator - 邮箱验证"
            )
            
            # 设置HTML和文本内容
            message.content = [
                Content("text/plain", text_content),
                Content("text/html", html_content)
            ]
            
            response = sg.send(message)
            logging.info(f"SendGrid邮件发送成功: {to_email}, 状态码: {response.status_code}")
            return True
            
        except Exception as e:
            logging.error(f"SendGrid邮件发送失败: {e}")
            return False

def send_verification_email_sendgrid(to_email, verification_url):
    """发送验证邮件的便捷函数"""
    service = SendGridService()
    return service.send_verification_email(to_email, verification_url)