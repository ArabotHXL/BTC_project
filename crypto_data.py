"""
多币种挖矿数据和实用函数
Multi-cryptocurrency mining data and utility functions
"""

import requests
import logging
import time
import os

# 缓存目录 
CACHE_DIR = './.cache'
os.makedirs(CACHE_DIR, exist_ok=True)

# 缓存时间 (秒)
CACHE_DURATION = 300  # 5分钟

# 支持的加密货币列表
CRYPTOCURRENCIES = {
    "BTC": {
        "name": "Bitcoin",
        "chinese_name": "比特币",
        "algorithm": "SHA-256",
        "default_price": 80000,  # USD
        "default_block_reward": 3.125,
        "default_difficulty": 119116256505723,  # ~119.12T
        "default_network_hashrate": 900,  # EH/s
        "block_time": 600,  # 10分钟
        "unit": "TH/s",
        "api_id": "bitcoin"
    },
    "LTC": {
        "name": "Litecoin",
        "chinese_name": "莱特币",
        "algorithm": "Scrypt",
        "default_price": 80.0,  # USD
        "default_block_reward": 6.25,
        "default_difficulty": 24.62e6,  # ~24.62M
        "default_network_hashrate": 950,  # TH/s
        "block_time": 150,  # 2.5分钟
        "unit": "MH/s",
        "api_id": "litecoin"
    },
    "ETC": {
        "name": "Ethereum Classic",
        "chinese_name": "以太经典",
        "algorithm": "Ethash",
        "default_price": 30.0,  # USD
        "default_block_reward": 3.2,
        "default_difficulty": 7.12e15,  # ~7.12P
        "default_network_hashrate": 55,  # TH/s
        "block_time": 13,  # 13秒
        "unit": "MH/s",
        "api_id": "ethereum-classic"
    },
    "DOGE": {
        "name": "Dogecoin",
        "chinese_name": "狗狗币",
        "algorithm": "Scrypt",
        "default_price": 0.12,  # USD
        "default_block_reward": 10000,
        "default_difficulty": 15.23e6,  # ~15.23M
        "default_network_hashrate": 650,  # TH/s
        "block_time": 60,  # 1分钟
        "unit": "MH/s",
        "api_id": "dogecoin"
    },
    "RVN": {
        "name": "Ravencoin",
        "chinese_name": "渡鸦币",
        "algorithm": "KawPow",
        "default_price": 0.02,  # USD
        "default_block_reward": 2500,
        "default_difficulty": 86.32e3,  # ~86.32K
        "default_network_hashrate": 4.2,  # TH/s
        "block_time": 60,  # 1分钟
        "unit": "MH/s",
        "api_id": "ravencoin"
    },
    "ZEC": {
        "name": "Zcash",
        "chinese_name": "大零币",
        "algorithm": "Equihash",
        "default_price": 60.0,  # USD
        "default_block_reward": 3.125,
        "default_difficulty": 121.45e6,  # ~121.45M
        "default_network_hashrate": 7.1,  # GH/s
        "block_time": 75,  # 1.25分钟
        "unit": "Sol/s",
        "api_id": "zcash"
    }
}

# 按算法分类的矿机数据，包括算力和功耗
MINER_DATA_BY_ALGORITHM = {
    "SHA-256": {
        "Antminer S21 XP Hyd": {"hashrate": 473, "unit": "TH/s", "power_watt": 5676},
        "Antminer S21 XP": {"hashrate": 270, "unit": "TH/s", "power_watt": 3645},
        "Antminer S21": {"hashrate": 200, "unit": "TH/s", "power_watt": 3500},
        "Antminer S21 Hyd": {"hashrate": 335, "unit": "TH/s", "power_watt": 5360},
        "Antminer S19": {"hashrate": 95, "unit": "TH/s", "power_watt": 3250},
        "Antminer S19 Pro": {"hashrate": 110, "unit": "TH/s", "power_watt": 3250},
        "Antminer S19j Pro": {"hashrate": 100, "unit": "TH/s", "power_watt": 3050},
        "Antminer S19 XP": {"hashrate": 140, "unit": "TH/s", "power_watt": 3010},
        "Antminer S19 Hydro": {"hashrate": 158, "unit": "TH/s", "power_watt": 5451},
        "Antminer S19 Pro+ Hyd": {"hashrate": 198, "unit": "TH/s", "power_watt": 5445}
    },
    "Scrypt": {
        "Antminer L7": {"hashrate": 9500, "unit": "MH/s", "power_watt": 3425},
        "Antminer L7 Pro": {"hashrate": 13000, "unit": "MH/s", "power_watt": 4550},
        "Goldshell LT6": {"hashrate": 3240, "unit": "MH/s", "power_watt": 3200},
        "iBeLink BM-K1+": {"hashrate": 2600, "unit": "MH/s", "power_watt": 2500}
    },
    "Ethash": {
        "Innosilicon A11 Pro ETH": {"hashrate": 2000, "unit": "MH/s", "power_watt": 2450},
        "Jasminer X16-Q": {"hashrate": 2520, "unit": "MH/s", "power_watt": 1200},
        "Antminer E9 Pro": {"hashrate": 3600, "unit": "MH/s", "power_watt": 3200},
        "NVIDIA RTX 4090 (6x)": {"hashrate": 360, "unit": "MH/s", "power_watt": 1500}
    },
    "KawPow": {
        "iBeLink BM-N1": {"hashrate": 80, "unit": "MH/s", "power_watt": 3000},
        "NVIDIA RTX 3080 (6x)": {"hashrate": 180, "unit": "MH/s", "power_watt": 1800},
        "NVIDIA RTX 3090 (6x)": {"hashrate": 240, "unit": "MH/s", "power_watt": 2100}
    },
    "Equihash": {
        "Antminer Z15": {"hashrate": 420, "unit": "kSol/s", "power_watt": 1510},
        "Bitmain Z11": {"hashrate": 135, "unit": "kSol/s", "power_watt": 1418},
        "Innosilicon A9++ ZMaster": {"hashrate": 140, "unit": "kSol/s", "power_watt": 1550}
    }
}

def get_miners_for_crypto(crypto_symbol):
    """获取特定加密货币的矿机列表"""
    if crypto_symbol not in CRYPTOCURRENCIES:
        return []
    
    algorithm = CRYPTOCURRENCIES[crypto_symbol]["algorithm"]
    if algorithm not in MINER_DATA_BY_ALGORITHM:
        return []
    
    return MINER_DATA_BY_ALGORITHM[algorithm]

def get_real_time_crypto_price(crypto_symbol="BTC"):
    """获取实时加密货币价格"""
    if crypto_symbol not in CRYPTOCURRENCIES:
        return CRYPTOCURRENCIES.get("BTC", {}).get("default_price", 80000)
    
    crypto_data = CRYPTOCURRENCIES[crypto_symbol]
    api_id = crypto_data.get("api_id", "bitcoin")
    default_price = crypto_data.get("default_price", 80000)
    
    try:
        # 尝试从CoinGecko API获取价格
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={api_id}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if api_id in data and "usd" in data[api_id]:
                return data[api_id]["usd"]
    except Exception as e:
        logging.error(f"获取{crypto_symbol}价格失败: {str(e)}")
    
    # 如果API获取失败，返回默认值
    return default_price

def get_real_time_network_data(crypto_symbol="BTC"):
    """获取实时网络数据"""
    if crypto_symbol not in CRYPTOCURRENCIES:
        crypto_symbol = "BTC"  # 默认使用BTC
    
    crypto_data = CRYPTOCURRENCIES[crypto_symbol]
    
    # 获取API ID和默认值
    api_id = crypto_data.get("api_id", "bitcoin")
    default_price = crypto_data.get("default_price", 80000)
    default_difficulty = crypto_data.get("default_difficulty", 119116256505723)
    default_network_hashrate = crypto_data.get("default_network_hashrate", 900)
    default_block_reward = crypto_data.get("default_block_reward", 3.125)
    
    try:
        # 获取价格
        price = get_real_time_crypto_price(crypto_symbol)
        
        # 这里简化处理，实际实现应该通过各币种的专用API获取实际数据
        # 以下仅作为示例，实际项目应该连接到相应的区块链API
        
        # 对于BTC，可以实现现有代码中的获取方式
        # 对于其他币种，需要实现类似的逻辑
        
        return {
            "price": price,
            "difficulty": default_difficulty,
            "network_hashrate": default_network_hashrate,
            "block_reward": default_block_reward
        }
        
    except Exception as e:
        logging.error(f"获取{crypto_symbol}网络数据失败: {str(e)}")
        return {
            "price": default_price,
            "difficulty": default_difficulty,
            "network_hashrate": default_network_hashrate,
            "block_reward": default_block_reward
        }

def normalize_hashrate(hashrate, from_unit, to_unit):
    """标准化算力单位"""
    # 单位转换因子
    conversion_factors = {
        "H/s": 1,
        "KH/s": 1e3,
        "MH/s": 1e6,
        "GH/s": 1e9,
        "TH/s": 1e12,
        "PH/s": 1e15,
        "EH/s": 1e18,
        "kSol/s": 1e3,  # Equihash算法特殊单位
        "Sol/s": 1,     # Equihash算法特殊单位
    }
    
    # 检查单位是否支持
    if from_unit not in conversion_factors or to_unit not in conversion_factors:
        return hashrate  # 不支持则返回原值
    
    # 转换为基本单位
    base_hashrate = hashrate * conversion_factors[from_unit]
    
    # 转换到目标单位
    return base_hashrate / conversion_factors[to_unit]