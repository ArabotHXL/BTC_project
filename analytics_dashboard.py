#!/usr/bin/env python3
"""
分析数据仪表盘
提供Web界面查看分析报告和实时数据
"""

import os
import json
import psycopg2
from flask import Flask, render_template, render_template_string, jsonify, request, session, redirect, url_for
from datetime import datetime, timedelta
import logging
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "analytics-dashboard-secret")

def get_user_role(email):
    """获取用户角色"""
    db_url = os.environ.get('DATABASE_URL')
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM user_access WHERE email = %s AND is_active = true", [email])
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"获取用户角色失败: {e}")
        return None

def owner_required(f):
    """只允许拥有者访问的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查用户是否已登录
        user_email = session.get('user_email')
        if not user_email:
            if request.path.startswith('/api/'):
                return jsonify({'error': '需要登录访问'}), 401
            return redirect(url_for('login'))
        
        # 检查用户角色是否为拥有者
        user_role = get_user_role(user_email)
        if user_role != 'owner':
            if request.path.startswith('/api/'):
                return jsonify({'error': '只有拥有者可以访问分析系统'}), 403
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>访问被拒绝</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                <style>
                    body { background-color: #0d1421; color: #ffffff; }
                    .card { background-color: #1a2332; border: 1px solid #2d3748; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="row justify-content-center mt-5">
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h4 class="text-danger">访问被拒绝</h4>
                                </div>
                                <div class="card-body">
                                    <p>抱歉，只有<strong>拥有者</strong>角色可以访问Bitcoin数据分析系统。</p>
                                    <p>当前用户：{{ email }}</p>
                                    <p>当前角色：{{ role }}</p>
                                    <a href="/" class="btn btn-primary">返回主页</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            ''', email=user_email, role=user_role or '未知')
        
        return f(*args, **kwargs)
    return decorated_function

class AnalyticsDashboard:
    """分析仪表盘"""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            return psycopg2.connect(self.db_url)
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None
    
    def get_latest_market_data(self):
        """获取最新市场数据"""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    recorded_at, btc_price, btc_market_cap, btc_volume_24h,
                    network_hashrate, network_difficulty, fear_greed_index,
                    price_change_1h, price_change_24h, price_change_7d
                FROM market_analytics 
                ORDER BY recorded_at DESC 
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'timestamp': row[0].isoformat(),
                'btc_price': float(row[1]),
                'market_cap': int(row[2]) if row[2] else None,
                'volume_24h': int(row[3]) if row[3] else None,
                'network_hashrate': float(row[4]) if row[4] else None,
                'network_difficulty': float(row[5]) if row[5] else None,
                'fear_greed_index': int(row[6]) if row[6] else None,
                'price_change_1h': float(row[7]) if row[7] else None,
                'price_change_24h': float(row[8]) if row[8] else None,
                'price_change_7d': float(row[9]) if row[9] else None
            }
            
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_price_history(self, hours=24):
        """获取价格历史"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT recorded_at, btc_price
                FROM market_analytics 
                WHERE recorded_at >= %s
                ORDER BY recorded_at ASC
            """, [datetime.now() - timedelta(hours=hours)])
            
            rows = cursor.fetchall()
            return [
                {
                    'time': row[0].isoformat(),
                    'price': float(row[1])
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"获取价格历史失败: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_latest_report(self):
        """获取最新分析报告"""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    report_type, generated_at, title, summary,
                    key_findings, recommendations, risk_assessment,
                    confidence_score
                FROM analysis_reports 
                ORDER BY generated_at DESC 
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'type': row[0],
                'generated_at': row[1].isoformat(),
                'title': row[2],
                'summary': row[3],
                'key_findings': json.loads(row[4]) if row[4] else {},
                'recommendations': json.loads(row[5]) if row[5] else [],
                'risk_assessment': json.loads(row[6]) if row[6] else {},
                'confidence_score': float(row[7]) if row[7] else 0
            }
            
        except Exception as e:
            logger.error(f"获取分析报告失败: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_technical_indicators(self):
        """获取最新技术指标"""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    recorded_at, sma_20, sma_50, ema_12, ema_26,
                    rsi_14, macd, bollinger_upper, bollinger_lower, volatility_30d
                FROM technical_indicators 
                ORDER BY recorded_at DESC 
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'timestamp': row[0].isoformat(),
                'sma_20': float(row[1]) if row[1] else None,
                'sma_50': float(row[2]) if row[2] else None,
                'ema_12': float(row[3]) if row[3] else None,
                'ema_26': float(row[4]) if row[4] else None,
                'rsi_14': float(row[5]) if row[5] else None,
                'macd': float(row[6]) if row[6] else None,
                'bollinger_upper': float(row[7]) if row[7] else None,
                'bollinger_lower': float(row[8]) if row[8] else None,
                'volatility_30d': float(row[9]) if row[9] else None
            }
            
        except Exception as e:
            logger.error(f"获取技术指标失败: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

# 全局仪表盘实例
dashboard = AnalyticsDashboard()

@app.route('/login', methods=['GET', 'POST'])
def login():
    """简单登录页面"""
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
                                <small class="text-muted">Only Owner Access</small>
                            </div>
                            <div class="card-body">
                                <form method="post">
                                    <div class="mb-3">
                                        <label class="form-label">Email Address</label>
                                        <input type="email" class="form-control" name="email" required 
                                               placeholder="输入拥有者邮箱">
                                    </div>
                                    <button type="submit" class="btn btn-primary">Access Analytics</button>
                                </form>
                                
                                {% if error %}
                                <div class="alert alert-danger mt-3">{{ error }}</div>
                                {% endif %}
                                
                                <div class="mt-3">
                                    <small class="text-muted">
                                        此系统仅限拥有者访问。请使用在主应用中具有'owner'角色的邮箱。
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        ''', error=request.args.get('error'))
    
    # POST处理
    email = request.form.get('email')
    if not email:
        return redirect(url_for('login', error='请输入邮箱'))
    
    # 验证用户角色
    user_role = get_user_role(email)
    if user_role == 'owner':
        session['user_email'] = email
        logger.info(f"拥有者用户登录分析系统: {email}")
        return redirect('/')
    else:
        error_msg = '只有拥有者角色可以访问分析系统' if user_role else '用户不存在或未激活'
        return redirect(url_for('login', error=error_msg))

@app.route('/logout')
def logout():
    """登出"""
    user_email = session.get('user_email')
    session.clear()
    logger.info(f"用户登出分析系统: {user_email}")
    return redirect(url_for('login'))

@app.route('/')
@owner_required
def index():
    """主页"""
    return render_template('analytics_dashboard.html')

@app.route('/api/market-data')
@owner_required
def api_market_data():
    """API: 获取最新市场数据"""
    data = dashboard.get_latest_market_data()
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': '无法获取市场数据'}), 500

@app.route('/api/price-history')
@owner_required
def api_price_history():
    """API: 获取价格历史"""
    hours = request.args.get('hours', 24, type=int)
    data = dashboard.get_price_history(hours)
    return jsonify(data)

@app.route('/api/latest-report')
@owner_required
def api_latest_report():
    """API: 获取最新分析报告"""
    data = dashboard.get_latest_report()
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': '暂无分析报告'}), 404

@app.route('/api/technical-indicators')
@owner_required
def api_technical_indicators():
    """API: 获取技术指标"""
    data = dashboard.get_technical_indicators()
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': '无法获取技术指标'}), 500

@app.route('/health')
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'analytics-dashboard',
        'auth_status': 'owner-only'
    })

@app.route('/auth/status')
@owner_required
def auth_status():
    """获取当前用户状态"""
    user_email = session.get('user_email')
    user_role = get_user_role(user_email)
    return jsonify({
        'authenticated': True,
        'email': user_email,
        'role': user_role,
        'access_level': 'owner'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)