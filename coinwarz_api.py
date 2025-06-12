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
            # 计算CoinWarz基于难度的算力
            coinwarz_hashrate = calculate_hashrate_from_difficulty(coinwarz_btc['difficulty'])
            blockchain_hashrate = get_real_time_btc_hashrate()
            
            # 选择更可靠的算力值：如果两者差异较小，使用CoinWarz计算值
            if coinwarz_hashrate and blockchain_hashrate:
                diff_percent = abs(coinwarz_hashrate - blockchain_hashrate) / blockchain_hashrate * 100
                if diff_percent < 20:  # 差异小于20%时使用CoinWarz计算值
                    final_hashrate = coinwarz_hashrate
                    hashrate_source = "CoinWarz (calculated)"
                    logging.info(f"使用CoinWarz计算算力: {coinwarz_hashrate:.1f} EH/s (差异: {diff_percent:.1f}%)")
                else:
                    final_hashrate = blockchain_hashrate
                    hashrate_source = "blockchain.info (API)"
                    logging.info(f"算力差异过大({diff_percent:.1f}%)，使用blockchain.info: {blockchain_hashrate:.1f} EH/s")
            else:
                final_hashrate = blockchain_hashrate or coinwarz_hashrate
                hashrate_source = "fallback"
            
            # 使用CoinWarz作为主要数据源
            network_data = {
                'btc_price': coinwarz_btc['btc_price'],
                'difficulty': coinwarz_btc['difficulty'],
                'block_reward': coinwarz_btc['block_reward'],
                'block_count': coinwarz_btc['block_count'],
                'hashrate': final_hashrate,
                'hashrate_source': hashrate_source,
                'coinwarz_hashrate': coinwarz_hashrate,
                'blockchain_hashrate': blockchain_hashrate,
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
                'hashrate_source': 'blockchain.info (fallback)',
                'data_source': 'blockchain.info (fallback)',
                'profit_ratio': 100,
                'health_status': 'Unknown'
            }
            logging.warning("CoinWarz数据不可用，使用blockchain.info备份")
            return network_data
            
    except Exception as e:
        logging.error(f"获取增强网络数据失败: {e}")
        return None