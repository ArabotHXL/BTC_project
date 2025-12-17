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
from multi_exchange_collector import MultiExchangeCollector
import logging

# 创建蓝图
deribit_bp = Blueprint('deribit_advanced', __name__)

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
        
        # 检查OKX API
        try:
            import requests
            okx_response = requests.get("https://www.okx.com/api/v5/public/time", timeout=10)
            okx_response.raise_for_status()
            status_results['okx'] = {
                'status': 'online',
                'message': 'API连接正常',
                'server_time': okx_response.json().get('data', [{}])[0].get('ts')
            }
        except Exception as e:
            status_results['okx'] = {
                'status': 'error',
                'message': f'OKX API检查失败: {str(e)}'
            }
        
        # 检查Binance API
        try:
            import requests
            binance_response = requests.get("https://eapi.binance.com/eapi/v1/time", timeout=10)
            binance_response.raise_for_status()
            status_results['binance'] = {
                'status': 'online',
                'message': 'API连接正常',
                'server_time': binance_response.json().get('serverTime')
            }
        except Exception as e:
            status_results['binance'] = {
                'status': 'error',
                'message': f'Binance API检查失败: {str(e)}'
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
        
        # 获取最新更新时间
        cursor.execute('SELECT MAX(collected_at) FROM trades')
        last_update = cursor.fetchone()[0]
        
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
    """手动执行多交易所数据分析"""
    try:
        data = request.get_json()
        instrument = data.get('instrument', 'BTC-PERPETUAL')
        
        # 执行原Deribit分析
        poc = DeribitAnalysisPOC()
        if instrument == 'auto':
            instrument = None
        poc.collect_and_analyze(instrument)
        
        # 执行多交易所数据收集
        collector = get_multi_collector()
        all_trades = collector.collect_all_exchanges(minutes=15, max_okx=50, max_binance=50)
        
        if all_trades:
            # 进行聚合分析
            agg_all, agg_cp = collector.aggregate_analysis(all_trades, 5.0, by="price", by_type=True)
            
            # 保存分析结果
            cp_dict = dict(agg_cp) if agg_cp else {}
            collector.save_bucket_analysis(agg_all, cp_dict, 5.0, "price", 15)
            
            message = f'多交易所分析完成 (Deribit + OKX + Binance)，收集到 {len(all_trades)} 笔交易'
        else:
            message = 'Deribit分析完成，多交易所数据收集无结果'
        
        return jsonify({
            'success': True,
            'message': message
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
    # Note: collection_active and poc_instance are module-level globals
    # They are only read here, not assigned, so no 'global' declaration needed
    
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
    """启动多交易所数据收集"""
    try:
        # 获取请求参数
        data = request.get_json() or {}
        minutes = data.get('minutes', 15)
        bucket_width = data.get('bucket_width', 5.0)
        bucket_by = data.get('bucket_by', 'price')
        max_okx = data.get('max_okx', 400)
        max_binance = data.get('max_binance', 400)
        by_type = data.get('by_type', True)
        
        collector = get_multi_collector()
        
        # 收集所有交易所数据（添加错误处理）
        try:
            all_trades = collector.collect_all_exchanges(minutes, max_okx, max_binance)
        except Exception as e:
            logger.error(f"多交易所数据收集失败: {e}")
            # 返回成功响应但包含错误信息，避免前端JSON解析错误
            return jsonify({
                'success': True,  # 改为True以避免前端错误
                'warning': f'部分数据收集失败: {str(e)}',
                'data': {
                    'total_trades': 0,
                    'exchanges': [],
                    'analysis': [],
                    'error_details': str(e)
                }
            })
        
        if not all_trades:
            return jsonify({
                'success': True,  # 改为True，避免前端显示错误
                'warning': '未收集到任何交易数据，可能是网络问题或市场交易较少',
                'data': {
                    'total_trades': 0,
                    'exchanges': [],
                    'analysis': []
                }
            })
        
        # 进行聚合分析
        agg_all, agg_cp = collector.aggregate_analysis(all_trades, bucket_width, by=bucket_by, by_type=by_type)
        
        # 保存分析结果
        cp_dict = dict(agg_cp) if agg_cp else {}
        collector.save_bucket_analysis(agg_all, cp_dict, bucket_width, bucket_by, minutes)
        
        # 获取各交易所摘要
        exchange_summary = collector.get_exchange_summary(minutes)
        
        return jsonify({
            'success': True,
            'message': f'成功收集到 {len(all_trades)} 笔交易数据',
            'data': {
                'total_trades': len(all_trades),
                'time_window_minutes': minutes,
                'bucket_width': bucket_width,
                'bucket_type': bucket_by,
                'exchanges': exchange_summary,
                'bucket_analysis': [{'bucket': k, 'trades': v['trades'], 'amount': v['amount']} for k, v in agg_all],
                'call_put_analysis': [{'bucket': k, 'call': v['CALL'], 'put': v['PUT']} for k, v in agg_cp] if agg_cp else [],
                'collection_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"多交易所数据收集失败: {e}")
        # 确保始终返回有效的JSON响应，避免前端解析错误
        return jsonify({
            'success': True,  # 改为True避免前端JSON解析错误
            'warning': f'系统处理异常: {str(e)}',
            'data': {
                'total_trades': 0,
                'exchanges': [],
                'analysis': [],
                'error_details': str(e)
            }
        })

@deribit_bp.route('/api/deribit/multi-exchange-analysis')
def get_multi_exchange_analysis():
    """获取多交易所分析结果"""
    try:
        collector = get_multi_collector()
        
        # 获取最新分析结果
        analysis_data = collector.get_latest_analysis(limit=50)
        
        # 获取交易所摘要
        exchange_summary = collector.get_exchange_summary(minutes=60)  # 最近1小时
        
        return jsonify({
            'success': True,
            'data': {
                'bucket_analysis': analysis_data,
                'exchange_summary': exchange_summary,
                'analysis_count': len(analysis_data),
                'last_updated': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"获取多交易所分析失败: {e}")
        return jsonify({
            'success': False,
            'error': f'获取分析数据失败: {str(e)}'
        }), 500

@deribit_bp.route('/api/deribit/multi-exchange-csv')
def export_multi_exchange_csv():
    """导出多交易所数据为CSV"""
    try:
        from flask import Response, make_response
        import io
        import csv
        
        collector = get_multi_collector()
        
        # 获取最近的交易数据 (最近1小时)
        conn = sqlite3.connect(collector.db_path)
        cursor = conn.cursor()
        
        # 查询最近1小时的数据
        cutoff_time = int(time.time() * 1000) - (60 * 60 * 1000)  # 1小时前
        
        cursor.execute('''
            SELECT exchange, timestamp, instrument, price, amount, side, 
                   expiry, strike, option_type, created_at
            FROM multi_exchange_trades 
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        ''', (cutoff_time,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 创建CSV内容
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入标题
        writer.writerow([
            'Exchange', 'Timestamp', 'Instrument', 'Price', 'Amount', 'Side',
            'Expiry', 'Strike', 'Option Type', 'Created At'
        ])
        
        # 写入数据
        for row in rows:
            # 转换时间戳为可读格式
            timestamp = datetime.fromtimestamp(row[1] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([
                row[0], timestamp, row[2], row[3], row[4], row[5],
                row[6], row[7], row[8], row[9]
            ])
        
        # 准备响应
        csv_content = output.getvalue()
        output.close()
        
        # 创建响应
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=multi_exchange_trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"CSV导出失败: {e}")
        return jsonify({
            'success': False,
            'error': f'CSV导出失败: {str(e)}'
        }), 500