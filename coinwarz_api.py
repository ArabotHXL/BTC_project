"""
CoinWarz API集成模块
提供专业的挖矿收益数据和多币种分析
"""

import requests
import logging
import os
import psycopg2
# from config import Config  # 已移除config模块

# CoinWarz API配置 - 从环境变量加载
COINWARZ_API_KEY = os.environ.get('COINWARZ_API_KEY', '')
COINWARZ_BASE_URL = "https://www.coinwarz.com/v1/api"

# 安全检查
if not COINWARZ_API_KEY:
    logging.warning("CoinWarz API key not configured. Please set COINWARZ_API_KEY environment variable.")

def get_coinwarz_profitability(algorithm="sha-256"):
    """
    获取CoinWarz挖矿收益数据
    
    Parameters:
    - algorithm: 挖矿算法 (sha-256, scrypt, ethash等)
    
    Returns:
    - 包含币种收益数据的字典
    """
    try:
        url = f"{COINWARZ_BASE_URL}/profitability"
        params = {
            'apikey': COINWARZ_API_KEY,
            'algo': algorithm
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('Success'):
            logging.info(f"成功获取CoinWarz {algorithm}算法收益数据")
            return data['Data']
        else:
            logging.error(f"CoinWarz API错误: {data.get('Message', '未知错误')}")
            return None
            
    except Exception as e:
        logging.error(f"获取CoinWarz数据失败: {e}")
        return None

def get_bitcoin_data_from_coinwarz():
    """
    从CoinWarz获取Bitcoin专用数据
    
    Returns:
    - Bitcoin挖矿数据字典
    """
    try:
        profitability_data = get_coinwarz_profitability("sha-256")
        if profitability_data:
            # 查找Bitcoin数据
            btc_data = next((coin for coin in profitability_data if coin['CoinTag'] == 'BTC'), None)
            if btc_data:
                return {
                    'btc_price': btc_data['ExchangeRate'],
                    'difficulty': btc_data['Difficulty'],
                    'block_reward': btc_data['BlockReward'],
                    'block_count': btc_data['BlockCount'],
                    'profit_ratio': btc_data['ProfitRatio'],
                    'health_status': btc_data['HealthStatus'],
                    'exchange': btc_data['Exchange'],
                    'block_time': btc_data['BlockTimeInSeconds']
                }
        return None
    except Exception as e:
        logging.error(f"获取CoinWarz Bitcoin数据失败: {e}")
        return None

def get_sha256_coins_comparison():
    """
    获取SHA-256算法所有币种的挖矿对比数据
    
    Returns:
    - SHA-256币种收益对比列表
    """
    try:
        profitability_data = get_coinwarz_profitability("sha-256")
        if profitability_data:
            # 按收益比率排序
            sorted_coins = sorted(profitability_data, key=lambda x: x['ProfitRatio'], reverse=True)
            
            comparison_data = []
            for coin in sorted_coins:
                comparison_data.append({
                    'coin_name': coin['CoinName'],
                    'coin_tag': coin['CoinTag'],
                    'difficulty': coin['Difficulty'],
                    'block_reward': coin['BlockReward'],
                    'profit_ratio': coin['ProfitRatio'],
                    'exchange_rate': coin['ExchangeRate'],
                    'health_status': coin['HealthStatus']
                })
            
            logging.info(f"获取到{len(comparison_data)}个SHA-256币种数据")
            return comparison_data
        return None
    except Exception as e:
        logging.error(f"获取SHA-256币种对比数据失败: {e}")
        return None

def check_coinwarz_api_status():
    """
    检查CoinWarz API状态和剩余调用次数
    
    Returns:
    - API状态信息字典
    """
    try:
        url = f"{COINWARZ_BASE_URL}/apikeyinfo"
        params = {'apikey': COINWARZ_API_KEY}
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        if data.get('Success'):
            api_info = data['Data']
            logging.info(f"CoinWarz API状态: 剩余{api_info['ApiUsageAvailable']}/{api_info['ApiUsageLimit']}次调用")
            return api_info
        else:
            logging.error(f"CoinWarz API状态检查失败: {data.get('Message', '未知错误')}")
            return None
            
    except Exception as e:
        logging.error(f"检查CoinWarz API状态失败: {e}")
        return None

def calculate_hashrate_from_difficulty(difficulty, block_time=600):
    """
    从难度计算网络算力
    
    Parameters:
    - difficulty: 网络难度
    - block_time: 区块时间（秒），比特币为600秒
    
    Returns:
    - 网络算力（EH/s）
    """
    try:
        # 使用比特币算力计算公式: hashrate = (difficulty * 2^32) / block_time
        hashrate_hash_per_sec = (difficulty * (2**32)) / block_time
        # 转换为EH/s
        hashrate_eh = hashrate_hash_per_sec / 1e18
        return hashrate_eh
    except Exception as e:
        logging.error(f"从难度计算算力失败: {e}")
        return None

def get_analytics_hashrate():
    """
    从分析系统获取网络算力数据 - 仅作为备用数据源
    """
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT network_hashrate, btc_price, network_difficulty
            FROM market_analytics 
            ORDER BY recorded_at DESC LIMIT 1
        """)
        data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if data and data[0]:
            logging.info(f"获取分析系统备用算力数据: {data[0]} EH/s")
            return {
                'hashrate': float(data[0]),
                'btc_price': float(data[1]) if data[1] else None,
                'difficulty': float(data[2]) if data[2] else None,
                'source': 'analytics_dashboard_fallback'
            }
    except Exception as e:
        logging.warning(f"无法获取分析系统算力数据: {e}")
    
    return None

def get_enhanced_network_data():
    """
    获取增强的网络数据，智能切换CoinWarz和blockchain.info
    优先使用CoinWarz，API用完时自动切换到blockchain.info
    
    Returns:
    - 综合网络数据字典
    """
    try:
        # 优先尝试从分析系统获取算力数据
        analytics_data = get_analytics_hashrate()
        
        # 首先检查CoinWarz API状态
        api_status = check_coinwarz_api_status()
        coinwarz_available = api_status and api_status.get('Approved') and api_status.get('ApiUsageAvailable', 0) > 0
        
        # 获取blockchain.info数据作为备份
        from mining_calculator import get_real_time_btc_price, get_real_time_difficulty, get_real_time_btc_hashrate
        
        if coinwarz_available:
            # CoinWarz API可用时优先使用
            coinwarz_btc = get_bitcoin_data_from_coinwarz()
            
            if coinwarz_btc:
                # 优先使用实时blockchain.info算力数据，其次使用分析系统缓存
                blockchain_hashrate = get_real_time_btc_hashrate()
                if blockchain_hashrate and blockchain_hashrate > 0:
                    final_hashrate = blockchain_hashrate
                    hashrate_source = "blockchain.info (real-time)"
                    logging.info(f"使用blockchain.info实时算力数据: {blockchain_hashrate:.1f} EH/s")
                elif analytics_data and analytics_data.get('hashrate'):
                    final_hashrate = analytics_data['hashrate']
                    hashrate_source = "analytics_dashboard (fallback)"
                    logging.info(f"使用分析仪表盘备用算力数据: {final_hashrate:.1f} EH/s")
                else:
                    final_hashrate = 900  # 默认值
                    hashrate_source = "default"
                    logging.warning(f"使用默认算力数据: {final_hashrate:.1f} EH/s")
                
                # 使用CoinWarz作为主要数据源
                network_data = {
                    'btc_price': coinwarz_btc['btc_price'],
                    'difficulty': coinwarz_btc['difficulty'],
                    'block_reward': coinwarz_btc['block_reward'],
                    'block_count': coinwarz_btc['block_count'],
                    'hashrate': final_hashrate,
                    'hashrate_source': hashrate_source,
                    'data_source': 'CoinWarz (primary)',
                    'profit_ratio': coinwarz_btc['profit_ratio'],
                    'health_status': coinwarz_btc['health_status'],
                    'api_calls_remaining': api_status.get('ApiUsageAvailable', 0)
                }
                logging.info(f"使用CoinWarz主要数据源 (剩余{api_status.get('ApiUsageAvailable', 0)}次调用)")
                return network_data
        
        # CoinWarz不可用或调用次数用完时，使用blockchain.info
        logging.warning(f"CoinWarz API不可用 (剩余调用: {api_status.get('ApiUsageAvailable', 0) if api_status else 0})，切换到blockchain.info")
        
        # 优先使用实时blockchain.info算力数据
        blockchain_hashrate = get_real_time_btc_hashrate()
        if blockchain_hashrate and blockchain_hashrate > 0:
            final_hashrate = blockchain_hashrate
            hashrate_source = 'blockchain.info (real-time API)'
            logging.info(f"使用blockchain.info实时算力数据: {blockchain_hashrate:.1f} EH/s")
        elif analytics_data and analytics_data.get('hashrate'):
            final_hashrate = analytics_data['hashrate']
            hashrate_source = "analytics_dashboard (fallback)"
            logging.info(f"使用分析仪表盘备用算力数据: {final_hashrate:.1f} EH/s")
        else:
            final_hashrate = 900  # 默认值
            hashrate_source = 'default'
            logging.warning(f"使用默认算力数据: {final_hashrate:.1f} EH/s")
        
        blockchain_difficulty = get_real_time_difficulty()
        blockchain_price = get_real_time_btc_price()
        
        network_data = {
            'btc_price': blockchain_price,
            'difficulty': blockchain_difficulty,
            'block_reward': 3.125,
            'hashrate': final_hashrate,
            'hashrate_source': hashrate_source,
            'data_source': 'blockchain.info (fallback)',
            'profit_ratio': 100,
            'health_status': 'Healthy' if blockchain_price and blockchain_difficulty and final_hashrate else 'Warning',
            'api_calls_remaining': api_status.get('ApiUsageAvailable', 0) if api_status else 0,
            'fallback_reason': 'CoinWarz API exhausted' if api_status else 'CoinWarz API unavailable'
        }
        
        # 将难度转换为T单位（万亿）
        difficulty_t = blockchain_difficulty / 1000000000000  # 转换为T单位
        logging.info(f"已切换到blockchain.info备用数据源: 价格=${blockchain_price}, 难度={difficulty_t:.1f}T, 算力={final_hashrate}EH/s")
        return network_data
            
    except Exception as e:
        logging.error(f"获取增强网络数据失败: {e}")
        # 最后的fallback - 使用默认值
        return {
            'btc_price': 80000,
            'difficulty': 100,
            'block_reward': 3.125,
            'hashrate': 700,
            'hashrate_source': 'default',
            'data_source': 'emergency fallback',
            'profit_ratio': 100,
            'health_status': 'Error',
            'api_calls_remaining': 0,
            'error': str(e)
        }