"""
CoinWarz API集成模块
提供专业的挖矿收益数据和多币种分析
"""

import requests
import logging
from config import Config

# CoinWarz API配置
COINWARZ_API_KEY = "8dd87e048ec84b6c8ad3322fb07f747a"
COINWARZ_BASE_URL = "https://www.coinwarz.com/v1/api"

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

def get_enhanced_network_data():
    """
    获取增强的网络数据，结合CoinWarz和blockchain.info
    
    Returns:
    - 综合网络数据字典
    """
    try:
        # 获取CoinWarz数据
        coinwarz_btc = get_bitcoin_data_from_coinwarz()
        
        # 获取blockchain.info数据作为备份
        from mining_calculator import get_real_time_btc_price, get_real_time_difficulty, get_real_time_btc_hashrate
        
        if coinwarz_btc:
            # 使用CoinWarz作为主要数据源
            network_data = {
                'btc_price': coinwarz_btc['btc_price'],
                'difficulty': coinwarz_btc['difficulty'],
                'block_reward': coinwarz_btc['block_reward'],
                'block_count': coinwarz_btc['block_count'],
                'hashrate': get_real_time_btc_hashrate(),  # 仍使用blockchain.info的算力
                'data_source': 'CoinWarz + blockchain.info',
                'profit_ratio': coinwarz_btc['profit_ratio'],
                'health_status': coinwarz_btc['health_status']
            }
            logging.info("使用CoinWarz增强网络数据")
            return network_data
        else:
            # 回退到blockchain.info
            network_data = {
                'btc_price': get_real_time_btc_price(),
                'difficulty': get_real_time_difficulty(),
                'block_reward': 3.125,
                'hashrate': get_real_time_btc_hashrate(),
                'data_source': 'blockchain.info (fallback)',
                'profit_ratio': 100,
                'health_status': 'Unknown'
            }
            logging.warning("CoinWarz数据不可用，使用blockchain.info备份")
            return network_data
            
    except Exception as e:
        logging.error(f"获取增强网络数据失败: {e}")
        return None