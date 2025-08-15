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
        
        # 正确计算期权平均价格 - 期权价格以BTC为单位，通常是小数
        if deribit_avg_price and deribit_avg_price > 0:  # 期权价格应该大于0
            avg_price = deribit_avg_price
            logger.info(f"使用Deribit期权平均价格: {avg_price:.6f} BTC")
        else:
            # 如果没有Deribit数据，使用多交易所数据
            multi_avg = multi_stats.get('avg_price', 0)
            if multi_avg and multi_avg > 0:
                avg_price = multi_avg
                logger.info(f"使用多交易所期权平均价格: {avg_price:.6f} BTC")
            else:
                avg_price = 0.001  # 使用典型期权价格作为后备
                logger.warning(f"使用后备期权价格: {avg_price:.6f} BTC")
        
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

@deribit_bp.route('/api/deribit/exchange-data/<exchange>')
def get_exchange_data(exchange):
    """获取指定交易所的实时数据"""
    try:
        import requests
        
        if exchange.lower() == 'deribit':
            # 获取Deribit数据
            response = requests.get("https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=option&expired=false", timeout=10)
            if response.status_code == 200:
                data = response.json()
                instruments = data.get('result', [])[:20]  # 获取前20个期权合约
                
                result_data = {
                    'exchange': 'Deribit',
                    'status': 'online',
                    'instruments_count': len(instruments),
                    'top_instruments': [
                        {
                            'name': inst.get('instrument_name'),
                            'strike': inst.get('strike'),
                            'expiry': inst.get('expiration_timestamp'),
                            'type': inst.get('option_type')
                        } for inst in instruments[:5]
                    ],
                    'last_update': datetime.now().isoformat()
                }
                return jsonify({'success': True, 'data': result_data})
        
        elif exchange.lower() == 'okx':
            # 获取OKX数据
            response = requests.get("https://www.okx.com/api/v5/public/instruments?instType=OPTION&uly=BTC-USD", timeout=10)
            if response.status_code == 200:
                data = response.json()
                instruments = data.get('data', [])[:20]
                
                result_data = {
                    'exchange': 'OKX',
                    'status': 'online',
                    'instruments_count': len(instruments),
                    'top_instruments': [
                        {
                            'name': inst.get('instId'),
                            'strike': inst.get('stk'),
                            'expiry': inst.get('expTime'),
                            'type': inst.get('optType')
                        } for inst in instruments[:5]
                    ],
                    'last_update': datetime.now().isoformat()
                }
                return jsonify({'success': True, 'data': result_data})
        
        elif exchange.lower() == 'binance':
            # 获取Binance数据 - 使用现货API作为备用
            try:
                response = requests.get("https://eapi.binance.com/eapi/v1/exchangeInfo", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    symbols = [s for s in data.get('symbols', []) if s.get('underlying') == 'BTCUSDT'][:20]
                    
                    result_data = {
                        'exchange': 'Binance',
                        'status': 'online',
                        'instruments_count': len(symbols),
                        'top_instruments': [
                            {
                                'name': symbol.get('symbol'),
                                'strike': symbol.get('strikePrice'),
                                'expiry': symbol.get('expiryDate'),
                                'type': symbol.get('side')
                            } for symbol in symbols[:5]
                        ],
                        'last_update': datetime.now().isoformat()
                    }
                    return jsonify({'success': True, 'data': result_data})
                else:
                    # 如果期权API失败，使用现货API作为备用
                    response = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        result_data = {
                            'exchange': 'Binance',
                            'status': 'online (spot)',
                            'instruments_count': 1,
                            'top_instruments': [
                                {
                                    'name': 'BTCUSDT',
                                    'strike': 'N/A',
                                    'expiry': 'Perpetual',
                                    'type': 'Spot'
                                }
                            ],
                            'last_update': datetime.now().isoformat()
                        }
                        return jsonify({'success': True, 'data': result_data})
            except Exception as binance_error:
                logger.warning(f"Binance API错误: {binance_error}")
                return jsonify({
                    'success': False, 
                    'error': f'Binance API暂时不可用: {str(binance_error)}',
                    'data': {
                        'exchange': 'Binance',
                        'status': 'error',
                        'last_update': datetime.now().isoformat()
                    }
                })
        
        else:
            return jsonify({'success': False, 'error': 'Unsupported exchange'})
            
    except Exception as e:
        logger.error(f"获取{exchange}数据失败: {e}")
        return jsonify({
            'success': False, 
            'error': f'获取{exchange}数据失败: {str(e)}',
            'data': {
                'exchange': exchange.title(),
                'status': 'error',
                'last_update': datetime.now().isoformat()
            }
        })

@deribit_bp.route('/api/deribit/multi-exchange-trades')
def get_multi_exchange_trades():
    """获取三大交易所的交易数据统计"""
    try:
        import requests
        
        # 存储所有交易所的数据
        all_trades = []
        total_volume = 0
        total_count = 0
        price_sum = 0
        price_count = 0
        
        # 获取Deribit交易数据
        try:
            deribit_response = requests.get("https://www.deribit.com/api/v2/public/get_last_trades_by_currency?currency=BTC&kind=option&count=100", timeout=10)
            if deribit_response.status_code == 200:
                deribit_data = deribit_response.json()
                deribit_trades = deribit_data.get('result', {}).get('trades', [])
                
                for trade in deribit_trades:
                    price = trade.get('price', 0)
                    amount = trade.get('amount', 0)
                    
                    all_trades.append({
                        'exchange': 'Deribit',
                        'price': price,
                        'amount': amount,
                        'timestamp': trade.get('timestamp', 0),
                        'instrument': trade.get('instrument_name', '')
                    })
                    
                    total_volume += amount
                    total_count += 1
                    if price > 0:
                        price_sum += price
                        price_count += 1
        except Exception as e:
            logger.warning(f"Deribit数据获取失败: {e}")
        
        # 获取OKX交易数据
        try:
            okx_response = requests.get("https://www.okx.com/api/v5/market/trades?instId=BTC-USD-241227-70000-C", timeout=10)
            if okx_response.status_code == 200:
                okx_data = okx_response.json()
                okx_trades = okx_data.get('data', [])
                
                for trade in okx_trades:
                    price = float(trade.get('px', 0))
                    size = float(trade.get('sz', 0))
                    
                    all_trades.append({
                        'exchange': 'OKX',
                        'price': price,
                        'amount': size,
                        'timestamp': int(trade.get('ts', 0)),
                        'instrument': trade.get('instId', '')
                    })
                    
                    total_volume += size
                    total_count += 1
                    if price > 0:
                        price_sum += price
                        price_count += 1
        except Exception as e:
            logger.warning(f"OKX数据获取失败: {e}")
        
        # 获取Binance交易数据（优先使用期权API，失败时使用现货API）
        try:
            # 尝试期权API
            binance_response = requests.get("https://eapi.binance.com/eapi/v1/ticker/24hr", timeout=10)
            if binance_response.status_code == 200:
                binance_data = binance_response.json()
                
                # 筛选BTC期权合约
                btc_options = [item for item in binance_data if 'BTC' in item.get('symbol', '')][:50]
                
                for option in btc_options:
                    try:
                        price = float(option.get('lastPrice', 0))
                        volume = float(option.get('volume', 0))
                        
                        if price > 0 and volume > 0:
                            all_trades.append({
                                'exchange': 'Binance',
                                'price': price,
                                'amount': volume,
                                'timestamp': int(option.get('closeTime', 0)),
                                'instrument': option.get('symbol', '')
                            })
                            
                            total_volume += volume
                            total_count += 1
                            price_sum += price
                            price_count += 1
                    except (ValueError, TypeError) as parse_error:
                        continue  # 跳过解析失败的数据
            else:
                # 如果期权API失败，使用现货数据作为备用
                spot_response = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=10)
                if spot_response.status_code == 200:
                    spot_data = spot_response.json()
                    price = float(spot_data.get('lastPrice', 0))
                    volume = float(spot_data.get('volume', 0))
                    
                    if price > 0 and volume > 0:
                        all_trades.append({
                            'exchange': 'Binance',
                            'price': price,
                            'amount': volume,
                            'timestamp': int(spot_data.get('closeTime', 0)),
                            'instrument': 'BTCUSDT-SPOT'
                        })
                        
                        total_volume += volume
                        total_count += 1
                        price_sum += price
                        price_count += 1
        except Exception as e:
            logger.warning(f"Binance数据获取失败: {e}")
        
        # 计算平均价格
        avg_price = price_sum / price_count if price_count > 0 else 0
        
        # 按交易所分组统计
        exchange_stats = {}
        for trade in all_trades:
            exchange = trade['exchange']
            if exchange not in exchange_stats:
                exchange_stats[exchange] = {
                    'count': 0,
                    'volume': 0,
                    'price_sum': 0,
                    'price_count': 0
                }
            
            exchange_stats[exchange]['count'] += 1
            exchange_stats[exchange]['volume'] += trade['amount']
            if trade['price'] > 0:
                exchange_stats[exchange]['price_sum'] += trade['price']
                exchange_stats[exchange]['price_count'] += 1
        
        # 计算各交易所平均价格
        for exchange in exchange_stats:
            stats = exchange_stats[exchange]
            stats['avg_price'] = stats['price_sum'] / stats['price_count'] if stats['price_count'] > 0 else 0
        
        # 转换为EST时区
        from pytz import timezone
        est = timezone('US/Eastern')
        utc_now = datetime.utcnow().replace(tzinfo=timezone('UTC'))
        est_now = utc_now.astimezone(est)
        
        return jsonify({
            'success': True,
            'data': {
                'total_trades': total_count,
                'total_volume': round(total_volume, 2),
                'avg_price': round(avg_price, 2),
                'last_update': est_now.strftime('%Y-%m-%d %H:%M:%S EST'),
                'exchange_breakdown': exchange_stats,
                'sample_trades': all_trades[:20]  # 返回前20笔交易作为样本
            }
        })
        
    except Exception as e:
        logger.error(f"多交易所交易数据获取失败: {e}")
        return jsonify({
            'success': False,
            'error': f'数据获取失败: {str(e)}'
        })

@deribit_bp.route('/api/deribit/compare-exchanges')
def compare_exchanges():
    """对比三大交易所数据"""
    try:
        exchanges = ['deribit', 'okx', 'binance']
        comparison_data = {
            'timestamp': datetime.now().isoformat(),
            'exchanges': {}
        }
        
        for exchange in exchanges:
            try:
                # 这里可以调用上面的get_exchange_data逻辑
                # 简化版本，直接返回基础比较数据
                comparison_data['exchanges'][exchange] = {
                    'name': exchange.title(),
                    'status': 'checking',
                    'last_check': datetime.now().isoformat()
                }
            except Exception as e:
                comparison_data['exchanges'][exchange] = {
                    'name': exchange.title(),
                    'status': 'error',
                    'error': str(e)
                }
        
        return jsonify({
            'success': True,
            'data': comparison_data
        })
        
    except Exception as e:
        logger.error(f"交易所对比失败: {e}")
        return jsonify({
            'success': False,
            'error': f'对比失败: {str(e)}'
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
        import sqlite3
        
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