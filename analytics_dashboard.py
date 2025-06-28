#!/usr/bin/env python3
"""
分析数据仪表盘
提供Web界面查看分析报告和实时数据
"""

import os
import json
import psycopg2
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "analytics-dashboard-secret")

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

@app.route('/')
def index():
    """主页"""
    return render_template('analytics_dashboard.html')

@app.route('/api/market-data')
def api_market_data():
    """API: 获取最新市场数据"""
    data = dashboard.get_latest_market_data()
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': '无法获取市场数据'}), 500

@app.route('/api/price-history')
def api_price_history():
    """API: 获取价格历史"""
    hours = request.args.get('hours', 24, type=int)
    data = dashboard.get_price_history(hours)
    return jsonify(data)

@app.route('/api/latest-report')
def api_latest_report():
    """API: 获取最新分析报告"""
    data = dashboard.get_latest_report()
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': '暂无分析报告'}), 404

@app.route('/api/technical-indicators')
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
        'service': 'analytics-dashboard'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)