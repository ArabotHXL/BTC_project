"""
多币种挖矿数据和实用函数
Multi-cryptocurrency mining data and utility functions
"""

import os
import json
import logging
import time
import requests
from datetime import datetime, timedelta

# MINER_DATA 变量从app.py导入，用作MINER_DATA_BY_ALGORITHM的备用

# 全局缓存字典，用于存储API响应
API_CACHE = {}
# 缓存超时时间（分钟）
CACHE_TIMEOUT_MINUTES = 15

# 支持的加密货币列表
CRYPTOCURRENCIES = {
    "BTC": {
        "name": "Bitcoin",
        "chinese_name": "比特币",
        "algorithm": "SHA-256",
        "unit": "TH/s",
        "block_time": 600,  # 10分钟
        "difficulty_adjustment": 2016,  # 区块数
        "api_endpoints": {
            "price": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            "network": "https://blockchair.com/bitcoin/stats",
            "alternative_network": "https://blockchain.info/q/",
        },
        "json_paths": {
            "price": "bitcoin.usd",
        },
        "risk_factors": {
            "market_dominance": 9,  # 1-10，10为最高
            "volatility": 6,
            "mining_competition": 9,
            "regulatory_risk": 5,
            "adoption_rate": 9
        }
    },
    "LTC": {
        "name": "Litecoin",
        "chinese_name": "莱特币",
        "algorithm": "Scrypt",
        "unit": "GH/s",
        "block_time": 150,  # 2.5分钟
        "difficulty_adjustment": 8064,  # 区块数
        "api_endpoints": {
            "price": "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd",
            "network": "https://blockchair.com/litecoin/stats",
            "alternative_network": "",
        },
        "json_paths": {
            "price": "litecoin.usd",
        },
        "risk_factors": {
            "market_dominance": 4,
            "volatility": 7,
            "mining_competition": 6,
            "regulatory_risk": 4,
            "adoption_rate": 5
        }
    },
    "ETC": {
        "name": "Ethereum Classic",
        "chinese_name": "以太经典",
        "algorithm": "EtcHash",
        "unit": "MH/s",
        "block_time": 13,  # 13秒
        "difficulty_adjustment": 1,  # 每区块
        "api_endpoints": {
            "price": "https://api.coingecko.com/api/v3/simple/price?ids=ethereum-classic&vs_currencies=usd",
            "network": "https://blockchair.com/ethereum-classic/stats",
            "alternative_network": "",
        },
        "json_paths": {
            "price": "ethereum-classic.usd",
        },
        "risk_factors": {
            "market_dominance": 2,
            "volatility": 8,
            "mining_competition": 5,
            "regulatory_risk": 4,
            "adoption_rate": 3
        }
    },
    "DOGE": {
        "name": "Dogecoin",
        "chinese_name": "狗狗币",
        "algorithm": "Scrypt",  # 与LTC相同
        "unit": "GH/s",
        "block_time": 60,  # 1分钟
        "difficulty_adjustment": 240,  # 区块数
        "api_endpoints": {
            "price": "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd",
            "network": "https://blockchair.com/dogecoin/stats",
            "alternative_network": "",
        },
        "json_paths": {
            "price": "dogecoin.usd",
        },
        "risk_factors": {
            "market_dominance": 3,
            "volatility": 9,
            "mining_competition": 4,
            "regulatory_risk": 5,
            "adoption_rate": 7
        }
    },
    "RVN": {
        "name": "Ravencoin",
        "chinese_name": "渡鸦币",
        "algorithm": "KawPow",
        "unit": "MH/s",
        "block_time": 60,  # 1分钟
        "difficulty_adjustment": 2016,  # 区块数，类似BTC
        "api_endpoints": {
            "price": "https://api.coingecko.com/api/v3/simple/price?ids=ravencoin&vs_currencies=usd",
            "network": "https://blockchair.com/ravencoin/stats",
            "alternative_network": "",
        },
        "json_paths": {
            "price": "ravencoin.usd",
        },
        "risk_factors": {
            "market_dominance": 2,
            "volatility": 8,
            "mining_competition": 3,
            "regulatory_risk": 3,
            "adoption_rate": 2
        }
    },
    "ZEC": {
        "name": "Zcash",
        "chinese_name": "大零币",
        "algorithm": "Equihash",
        "unit": "Sol/s",
        "block_time": 75,  # 75秒
        "difficulty_adjustment": 134,  # 区块数
        "api_endpoints": {
            "price": "https://api.coingecko.com/api/v3/simple/price?ids=zcash&vs_currencies=usd",
            "network": "https://blockchair.com/zcash/stats",
            "alternative_network": "",
        },
        "json_paths": {
            "price": "zcash.usd",
        },
        "risk_factors": {
            "market_dominance": 3,
            "volatility": 6,
            "mining_competition": 5,
            "regulatory_risk": 7,
            "adoption_rate": 4
        }
    }
}

# 每种算法的矿机数据
MINER_DATA_BY_ALGORITHM = {
    "SHA-256": {  # BTC
        "Antminer S21 XP": {
            "hashrate": 255,  # TH/s
            "power_watt": 3550,
            "unit": "TH/s",
            "release_date": "2023-08",
            "price_usd": 6200
        },
        "Whatsminer M60S++": {
            "hashrate": 340,  # TH/s
            "power_watt": 5650,
            "unit": "TH/s",
            "release_date": "2023-09",
            "price_usd": 8700
        },
        "Antminer S21": {
            "hashrate": 200,  # TH/s
            "power_watt": 3400,
            "unit": "TH/s",
            "release_date": "2023-04",
            "price_usd": 4500
        },
        "Antminer S19 XP": {
            "hashrate": 140,  # TH/s
            "power_watt": 3010,
            "unit": "TH/s",
            "release_date": "2022-07",
            "price_usd": 2800
        },
        "Whatsminer M50S++": {
            "hashrate": 150,  # TH/s
            "power_watt": 3300,
            "unit": "TH/s",
            "release_date": "2022-08",
            "price_usd": 3100
        },
        "Avalon A1366": {
            "hashrate": 95,  # TH/s
            "power_watt": 3400,
            "unit": "TH/s",
            "release_date": "2022-06",
            "price_usd": 1900
        }
    },
    "Scrypt": {  # LTC, DOGE
        "Bitmain Antminer L7": {
            "hashrate": 9500,  # GH/s (9.5 TH/s)
            "power_watt": 3425,
            "unit": "GH/s",
            "release_date": "2021-11",
            "price_usd": 18500
        },
        "FusionSilicon X7+": {
            "hashrate": 262,  # GH/s
            "power_watt": 1900,
            "unit": "GH/s",
            "release_date": "2022-02",
            "price_usd": 2400
        },
        "Goldshell LT6": {
            "hashrate": 3060,  # GH/s
            "power_watt": 3100,
            "unit": "GH/s",
            "release_date": "2022-09",
            "price_usd": 9500
        },
        "iBeLink BM-K1+": {
            "hashrate": 2650,  # GH/s
            "power_watt": 3200,
            "unit": "GH/s",
            "release_date": "2022-04",
            "price_usd": 7800
        }
    },
    "EtcHash": {  # ETC
        "Antminer E9 Pro": {
            "hashrate": 3600,  # MH/s (3.6 GH/s)
            "power_watt": 2560,
            "unit": "MH/s",
            "release_date": "2022-07",
            "price_usd": 7000
        },
        "Jasminer X16-Q": {
            "hashrate": 2650,  # MH/s
            "power_watt": 1900,
            "unit": "MH/s",
            "release_date": "2022-03",
            "price_usd": 5500
        },
        "Innosilicon A11 Pro ETH": {
            "hashrate": 2000,  # MH/s
            "power_watt": 2500,
            "unit": "MH/s",
            "release_date": "2021-09",
            "price_usd": 4500
        }
    },
    "KawPow": {  # RVN
        "iPollo RV1": {
            "hashrate": 20,  # MH/s
            "power_watt": 950,
            "unit": "MH/s",
            "release_date": "2022-05",
            "price_usd": 3200
        },
        "Goldshell KD6": {
            "hashrate": 28.8,  # MH/s
            "power_watt": 2880,
            "unit": "MH/s",
            "release_date": "2022-09",
            "price_usd": 6500
        }
    },
    "Equihash": {  # ZEC
        "Bitmain Antminer Z15": {
            "hashrate": 420,  # kSol/s
            "power_watt": 1510,
            "unit": "kSol/s",
            "release_date": "2020-05",
            "price_usd": 3500
        },
        "iBeLink BM-N1+": {
            "hashrate": 90,  # kSol/s
            "power_watt": 650,
            "unit": "kSol/s",
            "release_date": "2020-01",
            "price_usd": 1200
        }
    }
}

# 算力单位转换表（标准化到最小单位的倍数）
HASHRATE_UNITS = {
    "H/s": 1,                # 哈希/秒
    "KH/s": 1e3,             # 千哈希/秒
    "MH/s": 1e6,             # 百万哈希/秒
    "GH/s": 1e9,             # 十亿哈希/秒
    "TH/s": 1e12,            # 万亿哈希/秒
    "PH/s": 1e15,            # 千万亿哈希/秒
    "EH/s": 1e18,            # 百万万亿哈希/秒
    "ZH/s": 1e21,            # 十亿万亿哈希/秒
    "Sol/s": 1,              # 解决方案/秒 (Equihash)
    "kSol/s": 1e3,           # 千解决方案/秒
    "MSol/s": 1e6            # 百万解决方案/秒
}


def get_miners_for_crypto(crypto_symbol):
    """获取特定加密货币的矿机列表"""
    if crypto_symbol not in CRYPTOCURRENCIES:
        return []
    
    algorithm = CRYPTOCURRENCIES[crypto_symbol]['algorithm']
    if algorithm in MINER_DATA_BY_ALGORITHM:
        return MINER_DATA_BY_ALGORITHM[algorithm]
    return {}


def get_real_time_crypto_price(crypto_symbol="BTC"):
    """获取实时加密货币价格"""
    if crypto_symbol not in CRYPTOCURRENCIES:
        logging.error(f"不支持的加密货币: {crypto_symbol}")
        return None
    
    # 获取API信息
    crypto_data = CRYPTOCURRENCIES[crypto_symbol]
    price_endpoint = crypto_data['api_endpoints']['price']
    json_path = crypto_data['json_paths']['price'] if 'json_paths' in crypto_data else None
    
    # 检查缓存
    cache_key = f"price_{crypto_symbol}"
    if cache_key in API_CACHE:
        timestamp, data = API_CACHE[cache_key]
        # 如果缓存有效，返回缓存的价格
        if datetime.now() - timestamp < timedelta(minutes=CACHE_TIMEOUT_MINUTES):
            logging.info(f"使用缓存的{crypto_symbol}价格: ${data}")
            return data
    
    try:
        # 请求API获取价格
        response = requests.get(price_endpoint, timeout=10)
        if response.status_code == 200:
            price_data = response.json()
            
            # 根据json路径提取价格
            if json_path:
                path_parts = json_path.split('.')
                value = price_data
                for part in path_parts:
                    if part in value:
                        value = value[part]
                    else:
                        logging.error(f"JSON路径错误: {json_path}，部分{part}不存在")
                        return None
                
                # 获取价格
                price = float(value)
                
                # 更新缓存
                API_CACHE[cache_key] = (datetime.now(), price)
                
                logging.info(f"获取实时{crypto_symbol}价格: ${price}")
                return price
        
        logging.error(f"获取{crypto_symbol}价格失败: {response.status_code}")
        return None
    except Exception as e:
        logging.error(f"获取{crypto_symbol}价格时发生错误: {str(e)}")
        return None


def get_real_time_network_data(crypto_symbol="BTC"):
    """获取实时网络数据"""
    if crypto_symbol not in CRYPTOCURRENCIES:
        logging.error(f"不支持的加密货币: {crypto_symbol}")
        return None
    
    # 获取API信息
    crypto_data = CRYPTOCURRENCIES[crypto_symbol]
    network_endpoint = crypto_data['api_endpoints']['network']
    
    # 检查缓存
    cache_key = f"network_{crypto_symbol}"
    if cache_key in API_CACHE:
        timestamp, data = API_CACHE[cache_key]
        # 如果缓存有效，返回缓存的数据
        if datetime.now() - timestamp < timedelta(minutes=CACHE_TIMEOUT_MINUTES):
            logging.info(f"使用缓存的{crypto_symbol}网络数据")
            return data
    
    try:
        # TODO: 根据不同加密货币实现对应的网络数据获取逻辑
        # 返回值应包含:
        # - difficulty: 网络难度
        # - hashrate: 网络算力
        # - block_reward: 区块奖励
        
        # 这里是示例结构，需要为每种加密货币实现具体的获取逻辑
        network_data = {
            'difficulty': 0,
            'hashrate': 0,
            'block_reward': 0
        }
        
        # 比特币特殊处理
        if crypto_symbol == "BTC":
            # 获取BTC挖矿网络数据的具体实现
            from mining_calculator import get_real_time_difficulty, get_real_time_block_reward, get_real_time_btc_hashrate
            
            network_data = {
                'difficulty': get_real_time_difficulty(),
                'hashrate': get_real_time_btc_hashrate(),
                'block_reward': get_real_time_block_reward()
            }
        
        # 更新缓存
        API_CACHE[cache_key] = (datetime.now(), network_data)
        return network_data
        
    except Exception as e:
        logging.error(f"获取{crypto_symbol}网络数据时发生错误: {str(e)}")
        return None


def normalize_hashrate(hashrate, from_unit, to_unit):
    """标准化算力单位"""
    if from_unit not in HASHRATE_UNITS or to_unit not in HASHRATE_UNITS:
        logging.error(f"不支持的算力单位: {from_unit} 或 {to_unit}")
        return hashrate
    
    # 转换到标准单位
    base_value = hashrate * HASHRATE_UNITS[from_unit]
    
    # 从标准单位转换到目标单位
    return base_value / HASHRATE_UNITS[to_unit]