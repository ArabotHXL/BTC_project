#!/usr/bin/env python3
"""
分析系统授权模块
提供多种访问控制选项
"""

import os
import hashlib
import hmac
from functools import wraps
from flask import request, jsonify, session, redirect, url_for, render_template_string
import psycopg2
from datetime import datetime

class AnalyticsAuth:
    """分析系统授权管理"""
    
    def __init__(self, db_url):
        self.db_url = db_url
        self.auth_mode = os.environ.get('ANALYTICS_AUTH_MODE', 'open')  # open, token, email, integrated
        self.auth_token = os.environ.get('ANALYTICS_AUTH_TOKEN')
        self.allowed_emails = os.environ.get('ANALYTICS_ALLOWED_EMAILS', '').split(',')
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            return psycopg2.connect(self.db_url)
        except Exception as e:
            return None
    
    def verify_token_auth(self, token):
        """验证Token访问"""
        if not self.auth_token:
            return False
        return hmac.compare_digest(token, self.auth_token)
    
    def verify_email_auth(self, email):
        """验证邮箱访问"""
        if not self.allowed_emails or self.allowed_emails == ['']:
            return False
        return email.lower().strip() in [e.lower().strip() for e in self.allowed_emails]
    
    def verify_integrated_auth(self, email):
        """验证集成主应用授权"""
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM user_access 
                WHERE email = %s AND is_active = true
            """, [email])
            count = cursor.fetchone()[0]
            return count > 0
            
        except Exception:
            return False
        finally:
            cursor.close()
            conn.close()
    
    def require_auth(self, f):
        """授权装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 开放模式 - 无限制访问
            if self.auth_mode == 'open':
                return f(*args, **kwargs)
            
            # Token模式 - 需要在请求头或参数中提供token
            elif self.auth_mode == 'token':
                token = request.headers.get('Authorization') or request.args.get('token')
                if token and token.startswith('Bearer '):
                    token = token[7:]
                
                if not token or not self.verify_token_auth(token):
                    return jsonify({'error': '需要有效的访问令牌'}), 401
            
            # 邮箱模式 - 简单邮箱验证
            elif self.auth_mode == 'email':
                email = session.get('analytics_email')
                if not email:
                    if request.path.startswith('/api/'):
                        return jsonify({'error': '需要邮箱验证'}), 401
                    return redirect(url_for('auth_login'))
                
                if not self.verify_email_auth(email):
                    return jsonify({'error': '邮箱未授权访问'}), 403
            
            # 集成模式 - 使用主应用的用户权限
            elif self.auth_mode == 'integrated':
                email = session.get('analytics_email')
                if not email:
                    if request.path.startswith('/api/'):
                        return jsonify({'error': '需要登录验证'}), 401
                    return redirect(url_for('auth_login'))
                
                if not self.verify_integrated_auth(email):
                    return jsonify({'error': '用户未授权访问分析系统'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def create_auth_routes(self, app):
        """创建授权相关路由"""
        
        @app.route('/auth/login', methods=['GET', 'POST'])
        def auth_login():
            if request.method == 'GET':
                return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Analytics Login</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                    <style>
                        body { background-color: #0d1421; color: #ffffff; }
                        .card { background-color: #1a2332; border: 1px solid #2d3748; }
                        .form-control { background-color: #2d3748; border: 1px solid #4a5568; color: #ffffff; }
                        .form-control:focus { background-color: #2d3748; border-color: #667eea; color: #ffffff; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="row justify-content-center mt-5">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h4>Bitcoin Analytics Access</h4>
                                        <small class="text-muted">Mode: {{ auth_mode }}</small>
                                    </div>
                                    <div class="card-body">
                                        {% if auth_mode == 'token' %}
                                        <form method="post">
                                            <div class="mb-3">
                                                <label class="form-label">Access Token</label>
                                                <input type="password" class="form-control" name="token" required>
                                            </div>
                                            <button type="submit" class="btn btn-primary">Access Dashboard</button>
                                        </form>
                                        {% else %}
                                        <form method="post">
                                            <div class="mb-3">
                                                <label class="form-label">Email Address</label>
                                                <input type="email" class="form-control" name="email" required>
                                            </div>
                                            <button type="submit" class="btn btn-primary">Verify Access</button>
                                        </form>
                                        {% endif %}
                                        
                                        {% if error %}
                                        <div class="alert alert-danger mt-3">{{ error }}</div>
                                        {% endif %}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                ''', auth_mode=self.auth_mode, error=request.args.get('error'))
            
            # POST处理
            if self.auth_mode == 'token':
                token = request.form.get('token')
                if self.verify_token_auth(token):
                    session['analytics_token'] = True
                    return redirect('/')
                else:
                    return redirect(url_for('auth_login', error='Invalid token'))
            
            else:  # email or integrated
                email = request.form.get('email')
                if self.auth_mode == 'email' and self.verify_email_auth(email):
                    session['analytics_email'] = email
                    return redirect('/')
                elif self.auth_mode == 'integrated' and self.verify_integrated_auth(email):
                    session['analytics_email'] = email
                    return redirect('/')
                else:
                    error_msg = 'Email not authorized' if self.auth_mode == 'email' else 'User not found in main application'
                    return redirect(url_for('auth_login', error=error_msg))
        
        @app.route('/auth/logout')
        def auth_logout():
            session.clear()
            return redirect(url_for('auth_login'))
        
        @app.route('/auth/status')
        def auth_status():
            if self.auth_mode == 'open':
                return jsonify({'authenticated': True, 'mode': 'open'})
            
            authenticated = False
            user_info = {}
            
            if self.auth_mode == 'token':
                authenticated = session.get('analytics_token', False)
            else:
                email = session.get('analytics_email')
                authenticated = bool(email)
                if email:
                    user_info['email'] = email
            
            return jsonify({
                'authenticated': authenticated,
                'mode': self.auth_mode,
                'user': user_info
            })

def get_auth_config_example():
    """获取授权配置示例"""
    return """
# 分析系统授权配置示例

## 1. 开放访问模式（当前默认）
export ANALYTICS_AUTH_MODE="open"
# 无任何限制，所有人可访问

## 2. Token访问模式
export ANALYTICS_AUTH_MODE="token"
export ANALYTICS_AUTH_TOKEN="your-secret-token-here"
# 需要提供访问令牌
# 使用方式：curl -H "Authorization: Bearer your-secret-token-here" http://localhost:5001/api/market-data

## 3. 邮箱白名单模式  
export ANALYTICS_AUTH_MODE="email"
export ANALYTICS_ALLOWED_EMAILS="admin@company.com,analyst@company.com"
# 只允许指定邮箱访问

## 4. 集成主应用授权模式
export ANALYTICS_AUTH_MODE="integrated"
# 使用主应用的用户权限系统，只有在user_access表中的用户可以访问

启动方式：
1. 设置环境变量
2. 重启分析系统：python analytics_dashboard.py
"""

if __name__ == "__main__":
    print(get_auth_config_example())