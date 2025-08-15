"""
Deribit 交易数据分析 Web 路由
为Deribit POC系统提供Web界面和API端点
"""

from flask import Blueprint, render_template, jsonify, request, send_file
import sqlite3
import threading
import time
from datetime import datetime, timedelta
import pytz
from deribit_options_poc import DeribitAnalysisPOC, DeribitDataCollector
from multi_exchange_collector import MultiExchangeCollector
import logging
import os

# 创建蓝图
deribit_bp = Blueprint('deribit', __name__)

# 全局变量
collection_thread = None
collection_active = False
poc_instance = None
multi_collector = None

logger = logging.getLogger(__name__)

def get_multi_collector():
    """获取多交易所收集器实例"""
    global multi_collector
    if multi_collector is None:
        multi_collector = MultiExchangeCollector()
    return multi_collector

@deribit_bp.route('/deribit-analysis')
@deribit_bp.route('/deribit_analysis')
def deribit_analysis_page():
    """Deribit分析页面"""
    return render_template('deribit_analysis.html')

@deribit_bp.route('/download/deribit-package')
def download_deribit_package():
    """下载Deribit分析包"""
    try:
        package_path = os.path.join('static', 'deribit_analysis_package.tar.gz')
        if os.path.exists(package_path):
            return send_file(package_path, as_attachment=True, download_name='deribit_analysis_package.tar.gz')
        else:
            return jsonify({'error': 'Package file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@deribit_bp.route('/deribit-download')
def deribit_download_page():
    """Deribit分析包下载页面"""
    return render_template('deribit_download.html')

@deribit_bp.route('/api/deribit/status')
def api_status():
    """检查所有交易所API连接状态"""
    try:
        collector = get_multi_collector()
        status_results = {}
        
        # 检查Deribit API
        try:
            deribit_collector = DeribitDataCollector()
            deribit_result = deribit_collector.make_request("public/get_time")
            status_results['deribit'] = {
                'status': 'online' if deribit_result else 'offline',
                'message': 'API连接正常' if deribit_result else 'API连接失败',
                'server_time': deribit_result if deribit_result else None
            }
        except Exception as e:
            status_results['deribit'] = {
                'status': 'error',
                'message': f'检查失败: {str(e)}'
            }
        
        # OKX和Binance API检查已禁用
        status_results['okx'] = {
            'status': 'disabled',
            'message': '多交易所功能已禁用'
        }
        
        status_results['binance'] = {
            'status': 'disabled',
            'message': '多交易所功能已禁用'
        }
        
        # 计算总体状态
        online_count = sum(1 for status in status_results.values() if status['status'] == 'online')
        overall_success = online_count > 0
        
        return jsonify({
            'success': overall_success,
            'message': f'{online_count}/3 个交易所API连接正常',
            'exchanges': status_results,
            'online_count': online_count,
            'total_count': 3
        })
        
    except Exception as e:
        logger.error(f"多交易所API状态检查失败: {e}")
        return jsonify({
            'success': False,
            'message': f'检查失败: {str(e)}',
            'exchanges': {}
        })

@deribit_bp.route('/api/deribit/analysis-data')
def get_analysis_data():
    """获取多交易所分析数据"""
    try:
        collector = get_multi_collector()
        
        # 获取多交易所统计数据
        multi_stats = collector.get_multi_exchange_stats()
        
        # 连接Deribit数据库获取历史数据
        conn = sqlite3.connect('deribit_trades.db')
        cursor = conn.cursor()
        
        # 获取Deribit历史统计
        cursor.execute('SELECT COUNT(*) FROM trades')
        deribit_trades = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(amount), AVG(price) FROM trades')
        deribit_stats = cursor.fetchone()
        deribit_volume = deribit_stats[0] if deribit_stats[0] else 0
        deribit_avg_price = deribit_stats[1] if deribit_stats[1] else 0
        
        # 获取最新更新时间并转换为EST时区
        cursor.execute('SELECT MAX(collected_at) FROM trades')
        last_update_raw = cursor.fetchone()[0]
        
        # 转换为EST时区显示
        if last_update_raw:
            try:
                # 数据库中的时间格式是 '2025-08-15 00:56:28'，假设是UTC时间
                dt = datetime.strptime(last_update_raw, '%Y-%m-%d %H:%M:%S')
                # 设置为UTC时区
                dt_utc = pytz.UTC.localize(dt)
                # 转换为EST时区
                est_tz = pytz.timezone('US/Eastern')
                est_time = dt_utc.astimezone(est_tz)
                last_update = est_time.strftime('%Y-%m-%d %H:%M:%S EST')
            except Exception as e:
                logger.warning(f"时间转换失败: {e}")
                # 如果转换失败，使用当前EST时间
                est_tz = pytz.timezone('US/Eastern')
                current_est = datetime.now(est_tz)
                last_update = current_est.strftime('%Y-%m-%d %H:%M:%S EST')
        else:
            # 如果没有时间戳，使用当前EST时间
            est_tz = pytz.timezone('US/Eastern')
            current_est = datetime.now(est_tz)
            last_update = current_est.strftime('%Y-%m-%d %H:%M:%S EST')
        
        # 获取价格区间分析（从多交易所数据）
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
        
        # 获取买卖方向统计（从Deribit历史数据）
        cursor.execute('''
            SELECT direction, COUNT(*), SUM(amount)
            FROM trades
            GROUP BY direction
        ''')
        direction_stats = {'buy': 0, 'sell': 0}
        for row in cursor.fetchall():
            direction_stats[row[0]] = row[2] if row[2] else 0
        
        conn.close()
        
        # 尝试从多交易所数据获取方向统计
        try:
            multi_conn = sqlite3.connect('multi_exchange_trades.db')
            multi_cursor = multi_conn.cursor()
            
            # 获取最近24小时的多交易所买卖统计
            cutoff_time = collector.now_ms() - 24 * 60 * 60 * 1000
            multi_cursor.execute('''
                SELECT side, COUNT(*), SUM(amount)
                FROM multi_exchange_trades
                WHERE timestamp > ?
                GROUP BY side
            ''', (cutoff_time,))
            
            for row in multi_cursor.fetchall():
                side = row[0].lower() if row[0] else 'unknown'
                volume = row[2] if row[2] else 0
                if side in ['buy', 'sell']:
                    direction_stats[side] += volume
                    
            multi_conn.close()
            
        except Exception as e:
            logger.warning(f"获取多交易所方向统计失败: {e}")
            # 继续使用Deribit数据，不影响核心功能
        
        # 合并所有交易所数据
        total_trades = multi_stats.get('total_trades', 0) + deribit_trades
        total_volume = multi_stats.get('total_volume', 0) + deribit_volume
        
        # 修复平均价格计算 - 始终优先使用Deribit的真实价格数据
        if deribit_avg_price and deribit_avg_price > 50000:  # 确保使用合理的BTC价格
            avg_price = deribit_avg_price
            logger.info(f"使用Deribit平均价格: ${avg_price:,.2f}")
        else:
            # 如果没有Deribit数据，使用多交易所数据
            multi_avg = multi_stats.get('avg_price', 0)
            if multi_avg and multi_avg > 50000:
                avg_price = multi_avg
                logger.info(f"使用多交易所平均价格: ${avg_price:,.2f}")
            else:
                avg_price = 118500  # 使用当前BTC价格作为后备
                logger.warning(f"使用后备价格: ${avg_price:,.2f}")
        
        return jsonify({
            'success': True,
            'data': {
                'total_trades': total_trades,
                'total_volume': total_volume,
                'avg_price': avg_price,
                'last_update': last_update,
                'db_records': total_trades,
                'price_ranges': price_ranges,
                'exchange_breakdown': {
                    'deribit': {'trades': deribit_trades, 'volume': deribit_volume},
                    'okx': multi_stats.get('okx_stats', {}),
                    'binance': multi_stats.get('binance_stats', {})
                },
                'direction_stats': direction_stats,
                'multi_exchange_active': True
            }
        })
        
    except Exception as e:
        logger.error(f"获取多交易所分析数据失败: {e}")
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
    """手动执行Deribit数据分析（多交易所功能已禁用）"""
    try:
        data = request.get_json()
        instrument = data.get('instrument', 'BTC-PERPETUAL')
        
        # 仅执行Deribit分析
        poc = DeribitAnalysisPOC()
        if instrument == 'auto':
            instrument = None
        poc.collect_and_analyze(instrument)
        
        message = f'Deribit分析完成，合约: {instrument or "自动选择"}'
        
        return jsonify({
            'success': True,
            'message': message,
            'analysis_type': 'deribit_only',
            'multi_exchange_disabled': True
        })
        
    except Exception as e:
        logger.error(f"Deribit分析失败: {e}")
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

@deribit_bp.route('/api/deribit/multi-exchange-collect', methods=['POST'])
def start_multi_exchange_collection():
    """多交易所数据收集已禁用"""
    return jsonify({
        'success': False,
        'message': '多交易所数据收集功能已禁用。系统已配置为仅使用Deribit数据。',
        'data': {
            'total_trades': 0,
            'exchanges': [],
            'analysis': [],
            'disabled': True
        }
    })

@deribit_bp.route('/api/deribit/multi-exchange-analysis')
def get_multi_exchange_analysis():
    """多交易所分析功能已禁用"""
    return jsonify({
        'success': False,
        'message': '多交易所分析功能已禁用。系统已配置为仅使用Deribit数据。',
        'data': {
            'bucket_analysis': [],
            'exchange_summary': [],
            'analysis_count': 0,
            'disabled': True
        }
    })

@deribit_bp.route('/api/deribit/multi-exchange-csv')
def export_multi_exchange_csv():
    """CSV导出功能已禁用"""
    return jsonify({
        'success': False,
        'message': 'CSV导出功能已禁用。多交易所数据收集功能已关闭。',
        'disabled': True
    })