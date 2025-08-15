"""
Deribit 交易数据分析 Web 路由
为Deribit POC系统提供Web界面和API端点
"""

from flask import Blueprint, render_template, jsonify, request
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from deribit_options_poc import DeribitAnalysisPOC, DeribitDataCollector
import logging

# 创建蓝图
deribit_bp = Blueprint('deribit', __name__)

# 全局变量
collection_thread = None
collection_active = False
poc_instance = None

logger = logging.getLogger(__name__)

@deribit_bp.route('/deribit-analysis')
@deribit_bp.route('/deribit_analysis')
def deribit_analysis_page():
    """Deribit分析页面"""
    return render_template('deribit_analysis.html')

@deribit_bp.route('/api/deribit/status')
def api_status():
    """检查Deribit API连接状态"""
    try:
        collector = DeribitDataCollector()
        result = collector.make_request("public/get_time")
        
        if result:
            return jsonify({
                'success': True,
                'message': 'API连接正常',
                'server_time': result
            })
        else:
            return jsonify({
                'success': False,
                'message': 'API连接失败'
            })
    except Exception as e:
        logger.error(f"API状态检查失败: {e}")
        return jsonify({
            'success': False,
            'message': f'检查失败: {str(e)}'
        })

@deribit_bp.route('/api/deribit/analysis-data')
def get_analysis_data():
    """获取分析数据"""
    try:
        # 连接数据库
        conn = sqlite3.connect('deribit_trades.db')
        cursor = conn.cursor()
        
        # 获取基础统计
        cursor.execute('SELECT COUNT(*) FROM trades')
        total_trades = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(amount), AVG(price) FROM trades')
        stats = cursor.fetchone()
        total_volume = stats[0] if stats[0] else 0
        avg_price = stats[1] if stats[1] else 0
        
        # 获取最新更新时间
        cursor.execute('SELECT MAX(collected_at) FROM trades')
        last_update = cursor.fetchone()[0]
        
        # 获取价格区间分析
        cursor.execute('''
            SELECT price_range, trade_count, total_volume, avg_price, percentage
            FROM price_range_analysis
            ORDER BY analysis_time DESC
            LIMIT 10
        ''')
        price_ranges = []
        for row in cursor.fetchall():
            price_ranges.append({
                'price_range': row[0],
                'trade_count': row[1],
                'total_volume': row[2],
                'avg_price': row[3],
                'percentage': row[4]
            })
        
        # 获取买卖方向统计
        cursor.execute('''
            SELECT direction, COUNT(*), SUM(amount)
            FROM trades
            GROUP BY direction
        ''')
        direction_stats = {'buy': 0, 'sell': 0}
        for row in cursor.fetchall():
            direction_stats[row[0]] = row[2] if row[2] else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total_trades': total_trades,
                'total_volume': total_volume,
                'avg_price': avg_price,
                'last_update': last_update,
                'db_records': total_trades,
                'price_ranges': price_ranges,
                'direction_stats': direction_stats
            }
        })
        
    except Exception as e:
        logger.error(f"获取分析数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取数据失败: {str(e)}'
        })

@deribit_bp.route('/api/deribit/start-collection', methods=['POST'])
def start_collection():
    """启动数据采集"""
    global collection_thread, collection_active, poc_instance
    
    try:
        data = request.get_json()
        instrument = data.get('instrument', 'BTC-PERPETUAL')
        interval = int(data.get('interval', 15))
        
        if collection_active:
            return jsonify({
                'success': False,
                'message': '数据采集已在运行中'
            })
        
        # 初始化POC实例
        poc_instance = DeribitAnalysisPOC()
        
        # 启动采集线程
        collection_active = True
        collection_thread = threading.Thread(
            target=collection_worker,
            args=(instrument, interval)
        )
        collection_thread.daemon = True
        collection_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'数据采集已启动，间隔{interval}分钟'
        })
        
    except Exception as e:
        logger.error(f"启动数据采集失败: {e}")
        return jsonify({
            'success': False,
            'message': f'启动失败: {str(e)}'
        })

@deribit_bp.route('/api/deribit/stop-collection', methods=['POST'])
def stop_collection():
    """停止数据采集"""
    global collection_active
    
    try:
        collection_active = False
        
        return jsonify({
            'success': True,
            'message': '数据采集已停止'
        })
        
    except Exception as e:
        logger.error(f"停止数据采集失败: {e}")
        return jsonify({
            'success': False,
            'message': f'停止失败: {str(e)}'
        })

@deribit_bp.route('/api/deribit/manual-analysis', methods=['POST'])
def manual_analysis():
    """手动执行数据分析"""
    try:
        data = request.get_json()
        instrument = data.get('instrument', 'BTC-PERPETUAL')
        
        # 执行分析
        poc = DeribitAnalysisPOC()
        
        if instrument == 'auto':
            instrument = None
            
        poc.collect_and_analyze(instrument)
        
        return jsonify({
            'success': True,
            'message': '分析完成'
        })
        
    except Exception as e:
        logger.error(f"手动分析失败: {e}")
        return jsonify({
            'success': False,
            'message': f'分析失败: {str(e)}'
        })

@deribit_bp.route('/api/deribit/instruments')
def get_instruments():
    """获取可用合约列表"""
    try:
        collector = DeribitDataCollector()
        instruments = collector.get_instruments("BTC", "option")
        
        # 添加永续合约
        instrument_list = [
            {
                'instrument_name': 'BTC-PERPETUAL',
                'type': 'perpetual',
                'description': 'BTC永续合约'
            }
        ]
        
        # 添加期权合约（前20个）
        for inst in instruments[:20]:
            instrument_list.append({
                'instrument_name': inst['instrument_name'],
                'type': 'option',
                'description': f"{inst['option_type']} 期权, 行权价: ${inst['strike']}"
            })
        
        return jsonify({
            'success': True,
            'instruments': instrument_list
        })
        
    except Exception as e:
        logger.error(f"获取合约列表失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        })

def collection_worker(instrument, interval):
    """数据采集工作线程"""
    global collection_active, poc_instance
    
    logger.info(f"开始定时数据采集: {instrument}, 间隔{interval}分钟")
    
    while collection_active:
        try:
            if poc_instance:
                poc_instance.collect_and_analyze(instrument if instrument != 'auto' else None)
                logger.info(f"完成一次数据采集: {datetime.now()}")
        except Exception as e:
            logger.error(f"数据采集错误: {e}")
        
        # 等待指定间隔
        for i in range(interval * 60):  # 转换为秒
            if not collection_active:
                break
            time.sleep(1)
    
    logger.info("数据采集线程已停止")