import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class GmailSMTPService:
    def __init__(self):
        self.gmail_user = os.environ.get('GMAIL_USER')
        self.gmail_app_pass = os.environ.get('GMAIL_APP_PASS')
        
        if not all([self.gmail_user, self.gmail_app_pass]):
            logging.warning("Gmail SMTP配置不完整，需要设置GMAIL_USER和GMAIL_APP_PASS")
    
    def send_email(self, to_email, subject, text_content, html_content):
        """发送通用邮件
        
        Args:
            to_email: 接收邮箱
            subject: 邮件主题
            text_content: 纯文本内容
            html_content: HTML内容
        
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        if not self.gmail_user or not self.gmail_app_pass:
            logging.error("Gmail SMTP配置不完整")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f'"BTC Mining Calculator" <{self.gmail_user}>'
            msg["To"] = to_email
            msg["Subject"] = subject
            
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))
            
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                if self.gmail_user and self.gmail_app_pass:
                    server.login(self.gmail_user, self.gmail_app_pass)
                    server.send_message(msg)
            
            logging.info(f"Gmail SMTP邮件发送成功: {to_email}")
            return True
            
        except Exception as e:
            logging.error(f"Gmail SMTP邮件发送失败: {e}")
            return False
    
    def send_verification_email(self, to_email, verification_url, language='zh'):
        """发送邮箱验证邮件
        
        Args:
            to_email: 接收邮箱
            verification_url: 验证链接
            language: 语言 ('zh' 中文, 'en' 英文)
        """
        if not self.gmail_user or not self.gmail_app_pass:
            logging.error("Gmail SMTP配置不完整")
            return False
        
        try:
            # 创建邮件内容
            msg = MIMEMultipart("alternative")
            msg["From"] = f'"BTC Mining Calculator" <{self.gmail_user}>'
            msg["To"] = to_email
            
            # 根据语言设置邮件主题和内容
            if language == 'en':
                msg["Subject"] = "BTC Mining Calculator - Email Verification"
                text_content, html_content = self._get_english_templates(verification_url)
            else:
                msg["Subject"] = "BTC Mining Calculator - 邮箱验证"
                text_content, html_content = self._get_chinese_templates(verification_url)
            
            
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))
            
            # 发送邮件
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                if self.gmail_user and self.gmail_app_pass:
                    server.login(self.gmail_user, self.gmail_app_pass)
                    server.send_message(msg)
            
            logging.info(f"Gmail SMTP邮件发送成功: {to_email}")
            return True
            
        except Exception as e:
            logging.error(f"Gmail SMTP邮件发送失败: {e}")
            return False
    
    def _get_chinese_templates(self, verification_url):
        """获取中文邮件模板"""
        # 纯文本版本
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
        
        # HTML版本
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
        .button {{ display: inline-block; background: #2f6fed; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
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
        
        return text_content, html_content
    
    def _get_english_templates(self, verification_url):
        """获取英文邮件模板"""
        # 纯文本版本
        text_content = f"""
Email Verification - BTC Mining Calculator

Welcome to BTC Mining Calculator!

Please visit the following link to verify your email address:
{verification_url}

Notice:
- This verification link is valid for 24 hours
- After verification, you can use all features
- Contact customer service if you have any questions

© 2025 BTC Mining Calculator
This is an automated email, please do not reply.
"""
        
        # HTML版本
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Email Verification - BTC Mining Calculator</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #2f6fed; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Email Verification</h1>
            <p>BTC Mining Calculator</p>
        </div>
        <div class="content">
            <h2>Welcome to BTC Mining Calculator!</h2>
            <p>Thank you for registering on our Bitcoin mining calculator platform. Please click the button below to verify your email address:</p>
            
            <div style="text-align: center;">
                <a href="{verification_url}" class="button">Verify Email Address</a>
            </div>
            
            <p>If the button above doesn't work, please copy and paste the following link into your browser:</p>
            <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px;">
                {verification_url}
            </p>
            
            <p><strong>Notice:</strong></p>
            <ul>
                <li>This verification link is valid for 24 hours</li>
                <li>After verification, you can use all features</li>
                <li>Contact customer service if you have any questions</li>
            </ul>
        </div>
        <div class="footer">
            <p>© 2025 BTC Mining Calculator. All rights reserved.</p>
            <p>This is an automated email, please do not reply.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return text_content, html_content

def send_verification_email_smtp(to_email, verification_url, language='zh'):
    """发送验证邮件的便捷函数
    
    Args:
        to_email: 接收邮箱
        verification_url: 验证链接  
        language: 语言 ('zh' 中文, 'en' 英文)
    """
    service = GmailSMTPService()
    return service.send_verification_email(to_email, verification_url, language)

def send_curtailment_notification_email(to_email, plan, time_until_start, language='zh'):
    """
    发送限电计划提醒邮件
    
    Args:
        to_email: 接收邮箱
        plan: CurtailmentPlan对象
        time_until_start: 距离开始时间的分钟数
        language: 语言 ('zh' 中文, 'en' 英文)
    
    Returns:
        bool: 发送成功返回True，失败返回False
    """
    service = GmailSMTPService()
    
    strategy_name = plan.strategy.strategy_name if plan.strategy else 'N/A'
    
    if language == 'zh':
        subject = f"⚡ 限电计划提醒：{plan.plan_name} 将在 {int(time_until_start)} 分钟后执行"
        
        text_content = f"""
限电计划提醒

计划名称：{plan.plan_name}
开始时间：{plan.scheduled_start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
目标削减：{plan.target_power_reduction_kw} kW
策略：{strategy_name}

距离执行还有：{int(time_until_start)} 分钟

请做好准备，系统将自动执行限电计划。

此邮件为自动发送，请勿回复。
"""
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
        <div style="background: #f7931a; color: white; padding: 15px; border-radius: 5px 5px 0 0; text-align: center;">
            <h2 style="margin: 0;">⚡ 限电计划提醒</h2>
        </div>
        <div style="padding: 20px; background: #f9f9f9;">
            <p><strong>计划名称：</strong>{plan.plan_name}</p>
            <p><strong>开始时间：</strong>{plan.scheduled_start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            <p><strong>目标削减：</strong>{plan.target_power_reduction_kw} kW</p>
            <p><strong>策略：</strong>{strategy_name}</p>
            
            <div style="background: #fff3cd; border-left: 4px solid #f7931a; padding: 10px; margin: 15px 0;">
                <p style="margin: 0;"><strong>距离执行还有：{int(time_until_start)} 分钟</strong></p>
            </div>
            
            <p>请做好准备，系统将自动执行限电计划。</p>
        </div>
        <div style="padding: 10px; text-align: center; color: #666; font-size: 12px;">
            <p>此邮件为自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
"""
    else:
        subject = f"⚡ Curtailment Alert: {plan.plan_name} will execute in {int(time_until_start)} minutes"
        
        text_content = f"""
Curtailment Plan Alert

Plan Name: {plan.plan_name}
Start Time: {plan.scheduled_start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
Target Reduction: {plan.target_power_reduction_kw} kW
Strategy: {strategy_name}

Time until execution: {int(time_until_start)} minutes

Please prepare, the system will automatically execute the curtailment plan.

This is an automated email, please do not reply.
"""
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
        <div style="background: #f7931a; color: white; padding: 15px; border-radius: 5px 5px 0 0; text-align: center;">
            <h2 style="margin: 0;">⚡ Curtailment Plan Alert</h2>
        </div>
        <div style="padding: 20px; background: #f9f9f9;">
            <p><strong>Plan Name:</strong> {plan.plan_name}</p>
            <p><strong>Start Time:</strong> {plan.scheduled_start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            <p><strong>Target Reduction:</strong> {plan.target_power_reduction_kw} kW</p>
            <p><strong>Strategy:</strong> {strategy_name}</p>
            
            <div style="background: #fff3cd; border-left: 4px solid #f7931a; padding: 10px; margin: 15px 0;">
                <p style="margin: 0;"><strong>Time until execution: {int(time_until_start)} minutes</strong></p>
            </div>
            
            <p>Please prepare, the system will automatically execute the curtailment plan.</p>
        </div>
        <div style="padding: 10px; text-align: center; color: #666; font-size: 12px;">
            <p>This is an automated email, please do not reply.</p>
        </div>
    </div>
</body>
</html>
"""
    
    try:
        result = service.send_email(to_email, subject, text_content, html_content)
        if result:
            logging.info(f"✅ 已发送限电计划提醒邮件给 {to_email}")
        return result
    except Exception as e:
        logging.error(f"❌ 发送限电计划提醒邮件失败: {e}")
        return False