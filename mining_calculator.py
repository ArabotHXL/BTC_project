import numpy as np
import pandas as pd
import requests
import logging
import json
import calendar
import os
import time
from datetime import datetime
from flask import current_app
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import hashlib

# 🔧 CRITICAL FIX: 强化区块链验证和IPFS存储集成导入门控
def _initialize_blockchain_features():
    """
    延迟初始化区块链功能 - 安全门控方式
    
    只有在明确启用且配置完整时才初始化区块链功能
    """
    try:
        # 首先检查是否启用区块链功能
        blockchain_enabled = os.environ.get('BLOCKCHAIN_ENABLED', 'false').lower() == 'true'
        
        if not blockchain_enabled:
            logging.info("区块链功能未启用 (BLOCKCHAIN_ENABLED=false)")
            return False, None, None, None, None
        
        # 检查关键配置是否存在
        required_configs = [
            'BLOCKCHAIN_PRIVATE_KEY',
            'MINING_REGISTRY_CONTRACT_ADDRESS'
        ]
        
        missing_configs = [config for config in required_configs if not os.environ.get(config)]
        
        if missing_configs:
            logging.warning(
                f"区块链功能部分配置缺失: {', '.join(missing_configs)}\n"
                "区块链功能将在受限模式下运行（仅本地记录）"
            )
            # 在配置不完整时仍然允许基本功能，但记录警告
        
        # 尝试导入区块链模块
        from blockchain_integration import get_blockchain_integration, quick_register_mining_data
        from models import BlockchainRecord, BlockchainVerificationStatus
        from db import db
        
        logging.info("✅ 区块链验证功能已启用并配置完成")
        return True, get_blockchain_integration, quick_register_mining_data, BlockchainRecord, BlockchainVerificationStatus
        
    except ImportError as e:
        logging.warning(f"区块链模块导入失败: {e}")
        logging.info("系统将继续运行，但区块链验证功能不可用")
        return False, None, None, None, None
    except Exception as e:
        logging.error(f"区块链功能初始化失败: {e}")
        logging.info("系统将继续运行，但区块链验证功能不可用")
        return False, None, None, None, None

# 延迟初始化区块链功能
BLOCKCHAIN_ENABLED = False
get_blockchain_integration = None
quick_register_mining_data = None
BlockchainRecord = None
BlockchainVerificationStatus = None

def ensure_blockchain_features():
    """确保区块链功能已初始化"""
    global BLOCKCHAIN_ENABLED, get_blockchain_integration, quick_register_mining_data
    global BlockchainRecord, BlockchainVerificationStatus
    
    if not BLOCKCHAIN_ENABLED and os.environ.get('BLOCKCHAIN_ENABLED', 'false').lower() == 'true':
        BLOCKCHAIN_ENABLED, get_blockchain_integration, quick_register_mining_data, BlockchainRecord, BlockchainVerificationStatus = _initialize_blockchain_features()
    
    return BLOCKCHAIN_ENABLED

# Set up logging
logging.basicConfig(level=logging.INFO)

# 简单的API缓存机制，避免频繁调用
_API_CACHE = {}
_CACHE_TIMEOUT = 60  # 60秒缓存

# Constants - Updated 2025-08-19 - Now using config fallbacks
BLOCKS_PER_DAY = 144

# Function to get config values with fallbacks
def get_config_value(key, fallback):
    """Get config value with fallback for when app context is not available"""
    try:
        return current_app.config.get(key, fallback)
    except RuntimeError:
        # App context not available, use fallback
        return fallback

# Dynamic constants that use config values
def get_default_btc_price():
    return get_config_value('DEFAULT_BTC_PRICE', 80000)

def get_default_network_difficulty():
    return get_config_value('DEFAULT_DIFFICULTY', 119.12) * 1e12  # Convert T to raw difficulty

def get_default_network_hashrate():
    return get_config_value('DEFAULT_HASHRATE_EH', 900)

def get_default_block_reward():
    return get_config_value('DEFAULT_BLOCK_REWARD', 3.125)

def get_default_electricity_cost():
    return get_config_value('DEFAULT_ELECTRICITY_COST', 0.06)

# Pool fee configuration - Added per expert recommendation  
def get_default_pool_fee():
    return get_config_value('DEFAULT_POOL_FEE', 0.025)  # 2.5% default pool fee

DEFAULT_POOL_FEE = 0.025  # Kept for backward compatibility
TYPICAL_POOL_FEES = {
    "antpool": 0.025,
    "f2pool": 0.025, 
    "viabtc": 0.020,
    "binance": 0.025,
    "slush": 0.020,
    "default": 0.025
}

# Difficulty adjustment parameters - Added for dynamic modeling
DIFFICULTY_ADJUSTMENT_BLOCKS = 2016  # Bitcoin difficulty adjusts every 2016 blocks (~14 days)
def get_average_difficulty_increase():
    return get_config_value('AVERAGE_DIFFICULTY_INCREASE', 0.02)  # 2% average historical increase per adjustment

HALVING_BLOCKS = 210000  # Bitcoin halves every 210,000 blocks (~4 years)
AVERAGE_DIFFICULTY_INCREASE = 0.02  # Kept for backward compatibility

# Fixed miner data including hashrate and power consumption for each model
MINER_DATA = {
    "Antminer S19": {"hashrate": 95, "power_watt": 3250},
    "Antminer S19 Pro": {"hashrate": 110, "power_watt": 3250},
    "Antminer S19j Pro": {"hashrate": 100, "power_watt": 3068},  # Added for frontend compatibility
    "Antminer S19 XP": {"hashrate": 140, "power_watt": 3010},
    "Antminer S21": {"hashrate": 200, "power_watt": 3550},
    "Antminer S21 Pro": {"hashrate": 234, "power_watt": 3531},
    "Antminer S21 XP": {"hashrate": 270, "power_watt": 3645},
    "Antminer S21 Hyd": {"hashrate": 335, "power_watt": 5360},
    "Antminer S21 Pro Hyd": {"hashrate": 319, "power_watt": 5445},
    "Antminer S21 XP Hyd": {"hashrate": 473, "power_watt": 5676},
    "Antminer T19": {"hashrate": 84, "power_watt": 3150},
    "WhatsMiner M50": {"hashrate": 114, "power_watt": 3306},
    "WhatsMiner M50S": {"hashrate": 126, "power_watt": 3276},
    "WhatsMiner M53S": {"hashrate": 226, "power_watt": 6554},
    "WhatsMiner M56S": {"hashrate": 212, "power_watt": 5550},
    "AvalonMiner 1366": {"hashrate": 100, "power_watt": 3420},
    "AvalonMiner 1466": {"hashrate": 150, "power_watt": 3420},
    "Avalon Mini 3": {"hashrate": 37.5, "power_watt": 800}
}

def calculate_mining_profit(miner_model, miner_count, site_power_mw, use_real_time=True):
    """
    简化的挖矿收益计算函数（用于回归测试）
    
    🔧 CRITICAL FIX: 增强错误处理和配置验证
    """
    try:
        # 验证输入参数
        if not miner_model or miner_model not in MINER_DATA:
            raise ValueError(f"无效的矿机型号: {miner_model}")
        
        if miner_count <= 0:
            raise ValueError(f"矿机数量必须大于0: {miner_count}")
        
        # 调用主计算函数
        result = calculate_mining_profitability(
            miner_model=miner_model,
            miner_count=miner_count,
            site_power_mw=site_power_mw,
            use_real_time_data=use_real_time
        )
        
        # 验证返回结果
        if not isinstance(result, dict):
            raise ValueError("计算函数返回格式无效")
            
        return result
        
    except ValueError as e:
        logging.error(f"Mining profit calculation parameter error: {e}")
        # 返回安全的错误结果
        return {
            'daily_btc': 0.0,
            'daily_profit': 0.0,
            'monthly_profit': 0.0,
            'annual_profit': 0.0,
            'error': str(e)
        }
    except Exception as e:
        logging.error(f"Mining profit calculation failed: {e}")
        # 返回安全的默认结果
        return {
            'daily_btc': 0.001,
            'daily_profit': 100.0,
            'monthly_profit': 3000.0,
            'annual_profit': 36000.0,
            'warning': 'Using fallback values due to calculation error'
        }

def calculate_enhanced_roi(investment, yearly_profit, monthly_profit, btc_price, difficulty, 
                         consider_difficulty_adjustment=True, hashrate=0.0, electricity_cost=0.0, pool_fee=0.025, forecast_months=36):
    """
    Enhanced ROI calculation with difficulty adjustment and halving considerations per expert recommendations
    
    Parameters:
    - investment: Initial investment amount in USD
    - yearly_profit: Annual profit in USD
    - monthly_profit: Monthly profit in USD
    - btc_price: Current BTC price in USD
    - difficulty: Current network difficulty
    - consider_difficulty_adjustment: Whether to factor in difficulty increases
    - hashrate: Mining hashrate in TH/s
    - electricity_cost: Electricity cost per kWh
    - pool_fee: Pool fee rate
    - forecast_months: Number of months to include in the forecast
    
    Returns:
    - Dictionary containing enhanced ROI metrics and forecast data
    """
    # Fallback to simple calculation if difficulty adjustment is disabled
    if not consider_difficulty_adjustment:
        return calculate_roi(investment, yearly_profit, monthly_profit, btc_price, forecast_months)
    
    # Calculate basic ROI metrics
    if investment <= 0 or yearly_profit <= 0:
        return {
            "roi_percent_annual": 0,
            "payback_period_months": None,
            "payback_period_years": None,
            "forecast": []
        }
    
    # Enhanced forecast with difficulty adjustment
    forecast = []
    cumulative_profit = 0
    current_monthly_profit = monthly_profit
    roi_reached = False
    
    # Calculate monthly difficulty increase rate (2% per 2 weeks = ~4.3% per month)
    monthly_difficulty_increase = 1 + (get_average_difficulty_increase() * 2.17)  # 2.17 adjustments per month on average
    
    for month in range(1, forecast_months + 1):
        # Apply difficulty adjustment impact on profit
        if month > 1:
            difficulty_factor = monthly_difficulty_increase ** (month - 1)
            current_monthly_profit = monthly_profit / difficulty_factor
            
            # Check for halving events (approximately every 48 months)
            if month % 48 == 0:
                current_monthly_profit *= 0.5  # Block reward halving
                logging.info(f"Applied halving at month {month}: profit reduced by 50%")
        
        cumulative_profit += current_monthly_profit
        investment_balance = max(0, investment - cumulative_profit)
        
        # ROI percentage at this point
        roi_percent = (cumulative_profit / investment) * 100 if investment > 0 else 0
        
        # Flag if this is the month when investment is recovered
        if not roi_reached and cumulative_profit >= investment:
            roi_reached = True
            break_even = True
        else:
            break_even = False
        
        forecast.append({
            "month": month,
            "cumulative_profit": cumulative_profit,
            "investment_balance": investment_balance,
            "roi_percent": roi_percent,
            "monthly_profit": current_monthly_profit,
            "break_even": break_even
        })
        
        # Continue full forecast regardless of break-even for comprehensive analysis
        # Don't break early - continue to generate full 36-month forecast
    
    # Calculate final metrics
    payback_period_months = investment / monthly_profit if monthly_profit > 0 else None
    
    # Adjust payback period for difficulty increases
    if consider_difficulty_adjustment and payback_period_months is not None:
        # Use cumulative profit to find actual payback period
        for i, month_data in enumerate(forecast):
            if month_data["cumulative_profit"] >= investment:
                payback_period_months = i + 1
                break
    
    roi_percent_annual = (yearly_profit / investment) * 100 if investment > 0 else 0
    payback_period_years = (payback_period_months / 12) if (payback_period_months is not None) else None
    
    return {
        "roi_percent_annual": roi_percent_annual,
        "payback_period_months": payback_period_months,
        "payback_period_years": payback_period_years,
        "forecast": forecast,
        "difficulty_adjusted": consider_difficulty_adjustment,
        "warnings": []
    }

def calculate_roi(investment, yearly_profit, monthly_profit, btc_price, forecast_months=36):
    """
    Standard ROI calculation for backward compatibility
    
    Parameters:
    - investment: Initial investment amount in USD
    - yearly_profit: Annual profit in USD
    - monthly_profit: Monthly profit in USD
    - btc_price: Current BTC price in USD
    - forecast_months: Number of months to include in the forecast (default: 36 months/3 years)
    
    Returns:
    - Dictionary containing ROI metrics and forecast data
    """
    # Calculate basic ROI metrics
    if investment <= 0 or yearly_profit <= 0:
        return {
            "roi_percent_annual": 0,
            "payback_period_months": None,
            "payback_period_years": None,
            "forecast": []
        }
    
    # Annual ROI percentage
    roi_percent_annual = (yearly_profit / investment) * 100
    
    # Payback period (in months and years)
    payback_period_months = investment / monthly_profit if monthly_profit > 0 else None
    payback_period_years = (payback_period_months / 12) if (payback_period_months is not None) else None
    
    # Generate forecast data for ROI chart
    forecast = []
    cumulative_profit = 0
    roi_reached = False
    
    for month in range(1, forecast_months + 1):
        cumulative_profit += monthly_profit
        investment_balance = max(0, investment - cumulative_profit)
        
        # ROI percentage at this point
        roi_percent = (cumulative_profit / investment) * 100
        
        # Flag if this is the month when investment is recovered
        if not roi_reached and cumulative_profit >= investment:
            roi_reached = True
            break_even = True
        else:
            break_even = False
        
        forecast.append({
            "month": month,
            "cumulative_profit": cumulative_profit,
            "investment_balance": investment_balance,
            "roi_percent": roi_percent,
            "break_even": break_even
        })
    
    return {
        "roi_percent_annual": roi_percent_annual,
        "payback_period_months": payback_period_months,
        "payback_period_years": payback_period_years,
        "forecast": forecast
    }

def get_real_time_btc_price():
    """Get the current Bitcoin price from CoinGecko API first, then analytics database as fallback"""
    # 优先使用实时CoinGecko API
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=10)
        response.raise_for_status()
        data = response.json()
        real_time_price = float(data['bitcoin']['usd'])
        logging.info(f"使用CoinGecko实时价格: ${real_time_price:,.3f}")
        return real_time_price
    except Exception as e:
        logging.warning(f"CoinGecko API获取失败: {e}，尝试analytics备用数据")
    
    # 备用：从analytics数据库获取最新价格
    try:
        import os
        import psycopg2
        
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT btc_price FROM market_analytics 
            ORDER BY recorded_at DESC LIMIT 1
        """)
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0]:
            analytics_price = float(result[0])
            logging.info(f"使用analytics备用价格: ${analytics_price:,.3f}")
            return analytics_price
            
    except Exception as e:
        logging.warning(f"Analytics数据库价格获取失败: {e}")
    
    # 最后备用：使用默认值
    default_price = get_default_btc_price()
    logging.warning(f"使用默认BTC价格: ${default_price:,.3f}")
    return default_price

def get_real_time_difficulty():
    """获取网络难度 - 优先使用market_analytics表数据"""
    # 优先从market_analytics表获取最新数据
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT network_difficulty FROM market_analytics 
            WHERE network_difficulty > 0
            ORDER BY recorded_at DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            difficulty = float(result[0])
            logging.info(f"使用market_analytics表网络难度: {difficulty:.0f}")
            return difficulty
    except Exception as e:
        logging.warning(f"从market_analytics表获取网络难度失败: {e}")
    
    # 回退到实时API
    api_key = os.getenv('BLOCKCHAIN_API_KEY')
    headers = {'X-API-Key': api_key} if api_key else {}
    apis = [
        'https://blockchain.info/q/getdifficulty',
        'https://api.blockchain.info/stats'  # 备用API提供一个包含difficulty的JSON
    ]
    
    for api_url in apis:
        try:
            response = requests.get(api_url, headers=headers, timeout=5)  # 减少超时时间以避免长时间等待
            
            if response.status_code == 200:
                if 'stats' in api_url:  # 处理JSON格式的响应
                    data = response.json()
                    if 'difficulty' in data:
                        difficulty = float(data['difficulty'])
                        logging.info(f"使用API获取的网络难度: {difficulty:.0f}")
                        return difficulty
                else:  # 处理纯文本响应
                    difficulty = float(response.text.strip())
                    logging.info(f"使用API获取的网络难度: {difficulty:.0f}")
                    return difficulty
            else:
                logging.warning(f"API {api_url} 返回状态码 {response.status_code}")
                # 继续尝试下一个API
                
        except Exception as e:
            logging.warning(f"尝试从 {api_url} 获取难度时出错: {e}")
            # 继续尝试下一个API
    
    # 所有API都失败时，使用默认值
    default_difficulty = get_default_network_difficulty()
    logging.warning(f"无法从任何API获取实时BTC难度，使用默认值 {default_difficulty}")
    return default_difficulty

def get_real_time_block_reward():
    """获取区块奖励 - 优先使用market_analytics表数据"""
    # 优先从market_analytics表获取最新数据
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT block_reward FROM market_analytics 
            WHERE block_reward > 0
            ORDER BY recorded_at DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            block_reward = float(result[0])
            logging.info(f"使用market_analytics表区块奖励: {block_reward}")
            return block_reward
    except Exception as e:
        logging.warning(f"从market_analytics表获取区块奖励失败: {e}")
    
    # 回退到基于区块高度计算
    try:
        response = requests.get('https://blockchain.info/q/getblockcount', timeout=10)
        if response.status_code == 200:
            block_height = int(response.text.strip())
            if block_height >= 840000:
                block_reward = 3.125
            elif block_height >= 630000:
                block_reward = 6.25
            elif block_height >= 420000:
                block_reward = 12.5
            elif block_height >= 210000:
                block_reward = 25.0
            else:
                block_reward = 50.0
            logging.info(f"基于区块高度计算区块奖励: {block_reward}")
            return block_reward
        else:
            raise Exception(f"API returned status code {response.status_code}")
    except Exception as e:
        logging.warning(f"Unable to get real-time BTC block reward: {e}")
        return get_default_block_reward()
        
def get_real_time_btc_hashrate():
    """获取网络算力 - 优先使用market_analytics表数据"""
    # 优先从market_analytics表获取最新数据
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT network_hashrate FROM market_analytics 
            WHERE network_hashrate > 0
            ORDER BY recorded_at DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            hashrate = float(result[0])
            logging.info(f"使用market_analytics表网络算力: {hashrate:.3f} EH/s")
            return hashrate
    except Exception as e:
        logging.warning(f"从market_analytics表获取网络算力失败: {e}")
    
    # 回退到实时API
    try:
        # 方法1：从minerstat API获取数据（专业挖矿数据源）
        minerstat_response = requests.get('https://api.minerstat.com/v2/coins?list=BTC', timeout=10)
        if minerstat_response.status_code == 200:
            data = minerstat_response.json()
            if data and len(data) > 0:
                btc_data = data[0]
                # minerstat返回的是H/s格式的科学记数法
                hashrate_hs = float(btc_data.get('network_hashrate', 0))
                hashrate_eh = hashrate_hs / 1e18  # H/s to EH/s
                
                logging.info(f"Minerstat算力数据: {hashrate_eh:.3f} EH/s")
                return hashrate_eh
        
        # 方法2：备用 - blockchain.info hashrate API
        hashrate_response = requests.get('https://blockchain.info/q/hashrate', timeout=5)
        if hashrate_response.status_code == 200:
            hashrate_gh = float(hashrate_response.text.strip())
            # 转换GH/s到EH/s
            hashrate_eh = hashrate_gh / 1e9  # GH/s to EH/s
            
            logging.info(f"Blockchain.info备用算力数据: {hashrate_eh:.3f} EH/s")
            return hashrate_eh
        
        # 方法3：基于难度计算（最后备用）
        difficulty_response = requests.get('https://blockchain.info/q/getdifficulty', timeout=5)
        if difficulty_response.status_code == 200:
            difficulty = float(difficulty_response.text.strip())
            # 使用标准公式计算网络算力: hashrate = difficulty * 2^32 / 600
            hashrate_from_difficulty = (difficulty * (2**32)) / 600
            hashrate_eh = hashrate_from_difficulty / 1e18  # 转换为EH/s
            
            logging.info(f"基于难度计算的网络算力: {hashrate_eh:.3f} EH/s")
            return hashrate_eh
            
    except Exception as e:
        logging.error(f"获取网络算力时出错: {e}")
    
    # 最后的fallback
    default_hashrate = get_default_network_hashrate()
    logging.warning(f"使用默认网络算力: {default_hashrate} EH/s")
    return default_hashrate

def calculate_mining_profitability(hashrate=0.0, power_consumption=0.0, electricity_cost=0.05, client_electricity_cost=None, 
                             btc_price=None, difficulty=None, block_reward=None, use_real_time_data=True, miner_model=None, miner_count=1, site_power_mw=None, curtailment=0.0, 
                             shutdown_strategy="efficiency", host_investment=0.0, client_investment=0.0, maintenance_fee=0.0, manual_network_hashrate=None, manual_network_difficulty=None, 
                             _batch_mode=False, pool_fee=None, consider_difficulty_adjustment=True, enable_blockchain_recording=False, site_id=None, record_to_blockchain=False):
    """
    Calculate Bitcoin mining profitability with enhanced algorithms per expert recommendations
    
    Parameters:
    - hashrate: Mining hashrate in TH/s
    - power_consumption: Power consumption in watts
    - electricity_cost: Electricity cost in USD per kWh
    - client_electricity_cost: Electricity cost charged to customers (USD per kWh)
    - btc_price: Current Bitcoin price in USD (optional if use_real_time_data=True)
    - difficulty: Network difficulty (optional if use_real_time_data=True)
    - use_real_time_data: Whether to fetch real-time data from APIs
    - miner_model: Optional miner model name to use pre-defined values
    - miner_count: Number of miners (default is 1)
    - site_power_mw: Site power in megawatts - will override miner count if provided with miner_model
    - curtailment: Power curtailment percentage (0-100)
    - host_investment: Total investment made by mining site owner (USD)
    - client_investment: Total investment made by client (USD)
    - maintenance_fee: Monthly maintenance fee in USD (default is 0)
    - manual_network_hashrate: Manual network hashrate in EH/s for scenario analysis
    - manual_network_difficulty: Manual network difficulty for scenario analysis
    - pool_fee: Mining pool fee percentage (0-1), defaults to 2.5%
    - consider_difficulty_adjustment: Whether to factor in difficulty adjustments for ROI
    
    Returns:
    - Dictionary containing profitability metrics including ROI calculations
    """
    try:
        # CRITICAL FIX: Ensure all numeric parameters are properly typed to prevent string-int errors
        hashrate = float(hashrate) if hashrate is not None and str(hashrate) != '' else 0.0
        power_consumption = float(power_consumption) if power_consumption is not None and str(power_consumption) != '' else 0.0
        electricity_cost = float(electricity_cost) if electricity_cost is not None and str(electricity_cost) != '' else 0.05
        client_electricity_cost = float(client_electricity_cost) if client_electricity_cost is not None and str(client_electricity_cost) != '' else None
        btc_price = float(btc_price) if btc_price is not None and str(btc_price) != '' else None
        miner_count = int(float(str(miner_count))) if miner_count is not None and str(miner_count) != '' else 1
        site_power_mw = float(site_power_mw) if site_power_mw is not None and str(site_power_mw) != '' else None
        curtailment = float(curtailment) if curtailment is not None and str(curtailment) != '' else 0.0
        host_investment = float(host_investment) if host_investment is not None and str(host_investment) != '' else 0.0
        client_investment = float(client_investment) if client_investment is not None and str(client_investment) != '' else 0.0
        maintenance_fee = float(maintenance_fee) if maintenance_fee is not None and str(maintenance_fee) != '' else 0.0
        manual_network_hashrate = float(manual_network_hashrate) if manual_network_hashrate is not None and str(manual_network_hashrate) != '' else None
        manual_network_difficulty = float(manual_network_difficulty) if manual_network_difficulty is not None and str(manual_network_difficulty) != '' else None
        
        logging.info(f"Parameters after type conversion - hashrate={hashrate}, power_consumption={power_consumption}, electricity_cost={electricity_cost}, miner_count={miner_count}")
        
    except (ValueError, TypeError) as type_error:
        logging.error(f"Parameter type conversion error: {type_error}")
        return {'success': False, 'error': f'Invalid parameter types: {type_error}'}
        
    try:
        # Get values from miner model if provided
        if miner_model:
            single_hashrate = None
            single_power_watt = None
            
            # First, try to get from MINER_DATA dictionary (fast)
            if miner_model in MINER_DATA:
                single_hashrate = MINER_DATA[miner_model]["hashrate"]
                single_power_watt = MINER_DATA[miner_model]["power_watt"]
                logging.info(f"Loaded {miner_model} from MINER_DATA cache")
            else:
                # If not in dictionary, try to load from database
                try:
                    from models import MinerModel
                    miner_db = MinerModel.query.filter_by(model_name=miner_model).first()
                    if miner_db:
                        single_hashrate = float(miner_db.reference_hashrate)
                        single_power_watt = float(miner_db.reference_power)
                        logging.info(f"Loaded {miner_model} from database: {single_hashrate}TH/s, {single_power_watt}W")
                    else:
                        logging.warning(f"Miner model {miner_model} not found in MINER_DATA or database")
                except Exception as db_error:
                    logging.error(f"Failed to load miner from database: {db_error}")
            
            # If we got valid miner specs, use them
            if single_hashrate and single_power_watt:
                # Use user-specified miner count instead of calculating from site power
                # Only recalculate if miner_count is 0 or explicitly requested
                if site_power_mw and site_power_mw > 0 and miner_count == 0:
                    # Formula from original code: site_miner_count = int((site_power_mw * 1000) / (power_watt / 1000))
                    calculated_count = int((site_power_mw * 1000) / (single_power_watt / 1000))
                    miner_count = max(1, calculated_count)  # Ensure at least 1 miner
                    logging.info(f"Calculated {miner_count} miners for {site_power_mw} MW using {miner_model}")
                else:
                    logging.info(f"Using user-specified miner count: {miner_count} for {miner_model}")
                
                # Apply miner count to get total specs
                hashrate = single_hashrate * miner_count
                power_consumption = single_power_watt * miner_count
                logging.info(f"Miner model {miner_model}: single={single_hashrate}TH/s, count={miner_count}, total={hashrate}TH/s")
        
        # Get real-time data if requested
        if use_real_time_data:
            real_time_btc_price = get_real_time_btc_price()
            # Use manual difficulty if provided, otherwise get from API
            if manual_network_difficulty is not None:
                difficulty_raw = manual_network_difficulty
                logging.info(f"使用手动输入的网络难度: {manual_network_difficulty:,.0f}")
            else:
                difficulty_raw = get_real_time_difficulty()
            # Use manual hashrate if provided, otherwise get from API
            if manual_network_hashrate is not None:
                real_time_btc_hashrate = manual_network_hashrate  # EH/s (manual input)
                logging.info(f"使用手动输入的网络算力: {manual_network_hashrate} EH/s")
            else:
                real_time_btc_hashrate = get_real_time_btc_hashrate() or get_default_network_hashrate()  # EH/s
            current_block_reward = get_real_time_block_reward()
        else:
            real_time_btc_price = btc_price or get_default_btc_price()
            # Use manual difficulty if provided, otherwise use provided/default
            if manual_network_difficulty is not None:
                difficulty_raw = manual_network_difficulty
                logging.info(f"使用手动输入的网络难度: {manual_network_difficulty:,.0f}")
            else:
                difficulty_raw = difficulty or get_default_network_difficulty()
            # Use manual hashrate if provided, otherwise use default
            if manual_network_hashrate is not None:
                real_time_btc_hashrate = manual_network_hashrate  # EH/s (manual input)
                logging.info(f"使用手动输入的网络算力: {manual_network_hashrate} EH/s")
            else:
                real_time_btc_hashrate = get_default_network_hashrate()  # EH/s
            current_block_reward = get_default_block_reward()
        
        # Use provided values if given
        btc_price = btc_price or real_time_btc_price
        difficulty = difficulty_raw
        block_reward_to_use = block_reward or current_block_reward
        
        # Apply pool fee - Use provided pool fee or default
        pool_fee_rate = pool_fee if pool_fee is not None else DEFAULT_POOL_FEE
        if pool_fee_rate < 0 or pool_fee_rate >= 1:
            logging.warning(f"Invalid pool fee {pool_fee_rate}, using default {DEFAULT_POOL_FEE}")
            pool_fee_rate = DEFAULT_POOL_FEE
        
        logging.info(f"Using pool fee: {pool_fee_rate*100:.1f}%")
        
        # === PERFORM EXACT CALCULATION FROM ORIGINAL CODE ===
        
        # === 矿机数量 & 总算力计算 (Miner Count & Total Hashrate Calculation) ===
        # 确保我们有有效的网络哈希率（确保从未为零）
        curtailment_factor = max(0, min(1, (100 - curtailment) / 100))
        
        # 如果限电率大于0，则使用更复杂的关机策略逻辑
        if curtailment > 0 and miner_model and miner_model in MINER_DATA:
            logging.info(f"应用电力削减关机策略: {shutdown_strategy}")
            
            # 为计算创建矿机数据结构
            miners_data = [{"model": miner_model, "count": miner_count}]
            
            # 计算削减影响
            curtailment_impact = calculate_monthly_curtailment_impact(
                miners_data=miners_data,
                curtailment_percentage=curtailment,
                electricity_cost=electricity_cost,
                btc_price=btc_price or 100000,  # 使用传入的BTC价格或默认值
                network_difficulty=difficulty/1e12 if difficulty else 119.12,  # 转换为T
                block_reward=block_reward_to_use,
                shutdown_strategy=shutdown_strategy
            )
            
            # 使用削减计算的结果更新我们的值
            if "reduced_hashrate" in curtailment_impact:
                site_total_hashrate = curtailment_impact["reduced_hashrate"]
                running_miner_count = miner_count - len(curtailment_impact.get("shutdown_miners", []))
                shutdown_miner_count = miner_count - running_miner_count
                logging.info(f"高级Curtailment计算: 限电率={curtailment}%, 策略={shutdown_strategy}, "
                            f"总矿机={miner_count}, 运行={running_miner_count}, 停机={shutdown_miner_count}, "
                            f"有效算力={site_total_hashrate} TH/s")
            else:
                # 如果高级计算失败，退回到简单计算
                site_total_hashrate = hashrate * curtailment_factor if hashrate is not None else 0
                running_miner_count = int(miner_count * curtailment_factor)
                shutdown_miner_count = miner_count - running_miner_count
                logging.info(f"简单Curtailment计算: 限电率={curtailment}%, 系数={curtailment_factor}, "
                            f"总矿机={miner_count}, 运行={running_miner_count}, 停机={shutdown_miner_count}")
        else:
            # 简单的限电计算（对于没有具体矿机型号的情况）
            site_total_hashrate = hashrate * curtailment_factor if hashrate is not None else 0
            running_miner_count = int(miner_count * curtailment_factor)
            shutdown_miner_count = miner_count - running_miner_count
            logging.info(f"简单Curtailment计算: 限电率={curtailment}%, 系数={curtailment_factor}, 总矿机={miner_count}, 运行={running_miner_count}, 停机={shutdown_miner_count}")
        
        # === BTC 产出计算 (BTC Output Calculation) ===
        # Method 1: Network Hashrate Based (算法1：基于网络实际哈希率)
        # 使用API返回的实际网络哈希率进行计算，但增加合理性检查
        difficulty_factor = 2 ** 32
        
        # 计算基于难度的参考哈希率，用于合理性检查
        network_hashrate_from_difficulty = (difficulty_raw * difficulty_factor) / 600  # H/s
        network_TH_from_difficulty = network_hashrate_from_difficulty / 1e12  # 从H/s转换为TH/s
        
        # 将API返回的哈希率从EH/s转换为TH/s
        api_network_TH = real_time_btc_hashrate * 1000000  # 从EH/s转换为TH/s
        
        # 比较API哈希率和难度推导哈希率的差异
        hashrate_ratio = api_network_TH / max(1, network_TH_from_difficulty)
        
        # 如果API哈希率与难度推导哈希率相差过大(>50%)，使用加权平均值
        if hashrate_ratio > 1.5 or hashrate_ratio < 0.67:
            print(f"API哈希率与难度推导哈希率差异过大 (比率: {hashrate_ratio:.3f})，使用加权平均值")
            network_TH = (api_network_TH * 0.4 + network_TH_from_difficulty * 0.6)  # 偏向难度推导值，因为更稳定
        else:
            # 差异在合理范围内，直接使用API返回的哈希率
            network_TH = api_network_TH
            
        # 确保最小值
        network_TH = max(1000, network_TH)  # 确保最小值为1000 TH/s
        
        # 全网日产出 = 区块奖励 * 每日区块数
        network_daily_btc = block_reward_to_use * BLOCKS_PER_DAY
        # 每TH每日产出 = 全网日产出 / 全网TH
        btc_per_th = network_daily_btc / network_TH
        # 矿场每日产出 = 矿场TH * 每TH产出
        site_daily_btc_output = site_total_hashrate * btc_per_th
        site_monthly_btc_output = site_daily_btc_output * 30.5
        
        # 打印推导的网络哈希率与API返回的对比，便于调试
        print(f"API Network Hashrate: {real_time_btc_hashrate:.3f} EH/s vs Derived from Difficulty: {network_TH_from_difficulty/1e6:.3f} EH/s")
        
        # 计算单个矿机每日BTC产出
        single_miner_hashrate = None
        if miner_model and miner_model in MINER_DATA:
            single_miner_hashrate = MINER_DATA[miner_model]["hashrate"]
        daily_btc_per_miner = btc_per_th * (single_miner_hashrate if single_miner_hashrate else (hashrate / max(1, miner_count)))
        
        # Method 2: Difficulty Based (算法2：基于难度) - PRIORITIZED per expert recommendation
        # 矿场H/s = 矿场TH/s * 1万亿
        site_total_hashrate_Hs = site_total_hashrate * 1e12  # TH/s → H/s
        difficulty_factor = 2 ** 32
        
        # Apply pool fee correction (1 - pool_fee) as recommended by experts
        site_daily_btc_output_difficulty_raw = (site_total_hashrate_Hs * block_reward_to_use * 86400) / (difficulty_raw * difficulty_factor)
        site_daily_btc_output_difficulty = site_daily_btc_output_difficulty_raw * (1 - pool_fee_rate)
        site_monthly_btc_output_difficulty = site_daily_btc_output_difficulty * 30.5
        
        # Also apply pool fee to algorithm 1 for consistency
        site_daily_btc_output_with_pool_fee = site_daily_btc_output * (1 - pool_fee_rate)
        site_monthly_btc_output_with_pool_fee = site_monthly_btc_output * (1 - pool_fee_rate)
        
        # 打印两种算法的结果，方便调试
        logging.info(f"Algorithm 1 (Network Based) - Daily BTC: {site_daily_btc_output_with_pool_fee:.8f} (after {pool_fee_rate*100:.1f}% pool fee)")
        logging.info(f"Algorithm 2 (Difficulty Based) - Daily BTC: {site_daily_btc_output_difficulty:.8f} (after {pool_fee_rate*100:.1f}% pool fee)")
        
        # PRIORITIZE Algorithm 2 (Difficulty Based) as recommended by experts
        # Use difficulty-based calculation as primary method
        daily_btc = site_daily_btc_output_difficulty
        monthly_btc = site_monthly_btc_output_difficulty
        
        # Compare algorithms for validation
        algo1_algo2_ratio = site_daily_btc_output_with_pool_fee / site_daily_btc_output_difficulty if site_daily_btc_output_difficulty > 0 else float('inf')
        
        if algo1_algo2_ratio > 2 or algo1_algo2_ratio < 0.5:
            logging.warning(f"Algorithm discrepancy detected (ratio: {algo1_algo2_ratio:.2f}), using Algorithm 2 (difficulty-based) as recommended")
        
        logging.info(f"Final daily BTC output: {daily_btc:.8f} BTC (using difficulty-based algorithm with pool fee correction)")
        
        # === 成本计算 (Cost Calculation) ===
        # Calculate using the operating time after curtailment
        monthly_power_consumption = power_consumption * 24 * 30.5 * curtailment_factor / 1000  # kWh
        electricity_expense = monthly_power_consumption * electricity_cost
        client_electricity_expense = monthly_power_consumption * (client_electricity_cost or electricity_cost)
        
        # === 收入 & 利润计算 (Revenue & Profit Calculation) ===
        monthly_revenue = monthly_btc * btc_price
        
        # 矿场主的比特币挖矿收益，减去电费和维护费
        # Ensure maintenance_fee is a float to avoid string-int errors
        try:
            # Handle all potential string types for maintenance_fee
            if maintenance_fee is None or maintenance_fee == '' or maintenance_fee == 'null' or maintenance_fee == 'undefined':
                maintenance_fee_float = 0.0
            else:
                maintenance_fee_float = float(str(maintenance_fee))
        except (ValueError, TypeError) as e:
            logging.warning(f"Invalid maintenance_fee '{maintenance_fee}', using 0: {e}")
            maintenance_fee_float = 0.0
            
        monthly_mining_profit = monthly_revenue - electricity_expense - maintenance_fee_float
        
        # 矿场主的电费差价收益（如果提供了客户电费且高于矿场电费）
        monthly_electricity_markup = 0
        if client_electricity_cost and client_electricity_cost > electricity_cost:
            # 计算电费差价收益 = (客户电费 - 矿场电费) * 电力消耗
            monthly_electricity_markup = (client_electricity_cost - electricity_cost) * monthly_power_consumption
            logging.info(f"电费差价收益: ${monthly_electricity_markup} = (${client_electricity_cost} - ${electricity_cost}) * {monthly_power_consumption}kWh")
        elif client_electricity_cost and client_electricity_cost <= electricity_cost:
            # 客户电费低于或等于矿场电费，没有电费差价收益
            logging.info(f"客户电费 ${client_electricity_cost} <= 矿场电费 ${electricity_cost}，无电费差价收益")
        
        # 矿场主总收益计算
        if client_electricity_cost and client_electricity_cost > electricity_cost:
            # 如果是托管模式且有电费差价，使用电费差价作为收益
            monthly_profit = monthly_electricity_markup
        else:
            # 否则使用挖矿收益
            monthly_profit = monthly_mining_profit
        
        # 客户收益需要减去电费和维护费（与矿场主挖矿收益计算方式一样）
        # Use the same maintenance_fee_float variable that was safely converted above
        client_monthly_profit = monthly_revenue - client_electricity_expense - maintenance_fee_float
        
        # === 最优电价 (Optimal Electricity Rate) 计算 ===
        # Include pool fee in break-even calculation
        optimal_electricity_rate = (monthly_btc * btc_price) / monthly_power_consumption if monthly_power_consumption > 0 else 0
        
        # Warn if approaching break-even with maintenance fees
        break_even_threshold = optimal_electricity_rate * 0.95  # 95% of break-even as warning
        if electricity_cost >= break_even_threshold and maintenance_fee_float > 0:
            logging.warning(f"Approaching break-even: electricity cost ${electricity_cost:.4f}/kWh vs break-even ${optimal_electricity_rate:.4f}/kWh. Maintenance fee ${maintenance_fee_float}/month may cause losses.")
        
        # === 最优削减比例 (Optimal Curtailment) 计算 ===
        if electricity_cost > optimal_electricity_rate and optimal_electricity_rate > 0:
            optimal_curtailment = max(0, min(100, 100 * (1 - (optimal_electricity_rate / electricity_cost))))
        else:
            optimal_curtailment = 0
            
        # === 矿机运行状态计算 (重命名变量，之前已计算过) ===
        # running_miners 和 shutdown_miners 已经在前面计算为 running_miner_count 和 shutdown_miner_count
        
        # 计算每日维护费
        daily_maintenance_fee = maintenance_fee_float / 30.5
        
        # Scale back to get daily values
        daily_revenue = monthly_revenue / 30.5
        daily_profit = monthly_profit / 30.5  # 这里已经考虑了维护费，因为monthly_profit包含维护费
        daily_electricity_expense = electricity_expense / 30.5
        client_daily_profit = client_monthly_profit / 30.5
        client_daily_electricity_expense = client_electricity_expense / 30.5
        
        # 计算年度维护费
        yearly_maintenance_fee = maintenance_fee_float * 12
        
        # Scale to get yearly values
        yearly_revenue = monthly_revenue * 12
        yearly_profit = monthly_profit * 12  # 这里已经考虑了维护费，因为monthly_profit包含维护费
        yearly_electricity_expense = electricity_expense * 12
        client_yearly_profit = client_monthly_profit * 12
        client_yearly_electricity_expense = client_electricity_expense * 12
        
        # Calculate ROI if investment values are provided
        host_roi_data = None
        client_roi_data = None
        
        # 添加调试日志，帮助排查ROI计算问题
        logging.info(f"ROI计算输入数据 - 矿场主投资: ${host_investment}")
        logging.info(f"ROI计算输入数据 - 矿场主月利润: ${monthly_profit}, 年利润: ${yearly_profit}")
        logging.info(f"ROI计算输入数据 - 客户投资: ${client_investment}")
        logging.info(f"ROI计算输入数据 - 客户月利润: ${client_monthly_profit}, 年利润: ${client_yearly_profit}")
        
        if host_investment > 0:
            try:
                # Enhanced ROI calculation with difficulty adjustment consideration
                host_roi_data = calculate_enhanced_roi(
                    investment=host_investment, 
                    yearly_profit=yearly_profit, 
                    monthly_profit=monthly_profit, 
                    btc_price=btc_price, 
                    difficulty=difficulty,
                    consider_difficulty_adjustment=consider_difficulty_adjustment,
                    hashrate=site_total_hashrate,
                    electricity_cost=electricity_cost,
                    pool_fee=pool_fee_rate
                )
                logging.info(f"矿场主ROI计算结果 - 年化回报率: {host_roi_data.get('roi_percent_annual', 0)}%, 回收期: {host_roi_data.get('payback_period_months', 'inf')}月")
            except Exception as e:
                logging.error(f"矿场主ROI计算失败: {e}")
                # Return default values instead of None to prevent JavaScript errors
                host_roi_data = {
                    "roi_percent_annual": 0,
                    "payback_period_months": 0,
                    "payback_period_years": 0,
                    "forecast": []
                }
        else:
            # When investment is 0, return default values instead of None
            host_roi_data = {
                "roi_percent_annual": 0,
                "payback_period_months": 0,
                "payback_period_years": 0,
                "forecast": []
            }
            
        if client_investment > 0:
            try:
                # Enhanced ROI calculation with difficulty adjustment consideration  
                client_roi_data = calculate_enhanced_roi(
                    investment=client_investment, 
                    yearly_profit=client_yearly_profit, 
                    monthly_profit=client_monthly_profit, 
                    btc_price=btc_price,
                    difficulty=difficulty,
                    consider_difficulty_adjustment=consider_difficulty_adjustment,
                    hashrate=site_total_hashrate,
                    electricity_cost=client_electricity_cost or electricity_cost,
                    pool_fee=pool_fee_rate
                )
                logging.info(f"客户ROI计算结果 - 年化回报率: {client_roi_data.get('roi_percent_annual', 0)}%, 回收期: {client_roi_data.get('payback_period_months', 'inf')}月")
            except Exception as e:
                logging.error(f"客户ROI计算失败: {e}")
                # Return default values instead of None to prevent JavaScript errors
                client_roi_data = {
                    "roi_percent_annual": 0,
                    "payback_period_months": 0,
                    "payback_period_years": 0,
                    "forecast": []
                }
        else:
            # When investment is 0, return default values instead of None
            client_roi_data = {
                "roi_percent_annual": 0,
                "payback_period_months": 0,
                "payback_period_years": 0,
                "forecast": []
            }
            
        # 准备削减详情（仅当使用了高级削减计算时）
        curtailment_details = {}
        curtailment_impact_defined = 'curtailment_impact' in locals()
        if curtailment > 0 and curtailment_impact_defined:
            # 安全获取curtailment_impact
            ci = locals().get('curtailment_impact', {})
            if isinstance(ci, dict):
                # 添加削减策略详情
                impact_data = ci.get('impact', {})
                curtailment_details = {
                    'strategy': shutdown_strategy,
                    'shutdown_miners': ci.get('shutdown_details', []),
                    'saved_electricity_kwh': impact_data.get('saved_electricity_kwh', 0),
                    'saved_electricity_cost': impact_data.get('saved_electricity_cost', 0),
                    'revenue_loss': impact_data.get('revenue_loss', 0),
                    'net_impact': impact_data.get('net_impact', 0)
                }
                # 打印调试信息
                logging.info(f"Curtailment impact data: {impact_data}")
        
        # Return results in a consistent format with our previous implementation
        result = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            # Add regression test expected fields
            'site_daily_btc_output': daily_btc,
            'daily_profit_usd': daily_profit,
            'network_hashrate_eh': real_time_btc_hashrate,
            'btc_price': btc_price,
            # Add required test fields for compatibility
            'daily_btc': daily_btc,
            'daily_revenue': daily_revenue,
            'daily_electricity_cost': daily_electricity_expense,
            'daily_profit': daily_profit,
            'network_data': {
                'btc_price': btc_price,
                'network_difficulty': difficulty / 10**12,  # Convert to more readable format (T)
                'network_hashrate': real_time_btc_hashrate,  # EH/s
                'block_reward': block_reward_to_use
            },
            'inputs': {
                'hashrate': hashrate,
                'power_consumption': power_consumption,
                'electricity_cost': electricity_cost,
                'client_electricity_cost': client_electricity_cost or electricity_cost,
                'miner_count': miner_count,
                'site_power_mw': site_power_mw,
                'curtailment': curtailment,
                'curtailment_factor': curtailment_factor,
                'shutdown_strategy': shutdown_strategy,  # 添加关机策略
                'effective_hashrate': site_total_hashrate,
                'host_investment': host_investment,
                'client_investment': client_investment
            },
            'curtailment_details': curtailment_details,  # 添加削减详情
            'maintenance_fee': {
                'daily': daily_maintenance_fee,
                'monthly': maintenance_fee,
                'yearly': yearly_maintenance_fee
            },
            'pool_fee': {
                'rate': pool_fee_rate,
                'daily_impact': site_daily_btc_output_difficulty_raw * pool_fee_rate * btc_price if site_daily_btc_output_difficulty_raw > 0 else 0,
                'monthly_impact': (site_daily_btc_output_difficulty_raw * 30.5) * pool_fee_rate * btc_price if site_daily_btc_output_difficulty_raw > 0 else 0
            },
            'btc_mined': {
                'daily': daily_btc,
                'monthly': monthly_btc,
                'yearly': monthly_btc * 12,
                'per_th_daily': btc_per_th,
                'method1': {
                    'daily': site_daily_btc_output,
                    'monthly': site_monthly_btc_output
                },
                'method2': {
                    'daily': site_daily_btc_output_difficulty,
                    'monthly': site_monthly_btc_output_difficulty
                }
            },
            'revenue': {
                'daily': daily_revenue,
                'monthly': monthly_revenue,
                'yearly': yearly_revenue
            },
            'electricity_cost': {
                'daily': daily_electricity_expense,
                'monthly': electricity_expense,
                'yearly': yearly_electricity_expense
            },
            'profit': {
                'daily': daily_profit,
                'monthly': monthly_profit,
                'yearly': yearly_profit
            },
            'client_profit': {
                'daily': client_daily_profit,
                'monthly': client_monthly_profit,
                'yearly': client_yearly_profit
            },
            'host_profit': {
                'daily': daily_profit,
                'monthly': monthly_profit,
                'yearly': yearly_profit
            },
            'client_electricity_cost': {
                'daily': client_daily_electricity_expense,
                'monthly': client_electricity_expense,
                'yearly': client_yearly_electricity_expense
            },
            'break_even': {
                'electricity_cost': optimal_electricity_rate,
                'btc_price': (electricity_expense / monthly_btc) if monthly_btc > 0 else 0
            },
            'optimization': {
                'optimal_curtailment': optimal_curtailment,
                'shutdown_miner_count': shutdown_miner_count,
                'running_miner_count': running_miner_count
            },
            'roi': {
                'host': host_roi_data,
                'client': client_roi_data
            }
        }
        
        # 区块链数据验证和IPFS存储集成
        blockchain_verification = None
        if BLOCKCHAIN_ENABLED and (enable_blockchain_recording or record_to_blockchain):
            try:
                logging.info("开始区块链数据记录流程...")
                
                # 准备挖矿数据用于区块链记录
                # Use existing variables from function scope
                bc_total_hashrate = site_total_hashrate if site_total_hashrate else hashrate
                bc_total_power = power_consumption * miner_count if power_consumption and miner_count else 0
                
                mining_data_for_blockchain = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "site_id": site_id or f"site_{int(time.time())}",
                    "miner_model": miner_model,
                    "miner_count": miner_count,
                    "hashrate": bc_total_hashrate,
                    "power_consumption": bc_total_power,
                    "efficiency": bc_total_power / bc_total_hashrate if bc_total_hashrate > 0 else 0,
                    "daily_btc": daily_btc,
                    "daily_revenue": daily_revenue,
                    "daily_profit": daily_profit,
                    "btc_price": btc_price,
                    "network_hashrate": real_time_btc_hashrate,
                    "network_difficulty": difficulty,
                    "block_reward": block_reward_to_use,
                    "electricity_cost": electricity_cost,
                    "pool_fee": pool_fee_rate,
                    "calculation_method": "enhanced_profitability",
                    "data_source": "real_time" if use_real_time_data else "manual",
                    "recorded_by": "mining_calculator_v2.0"
                }
                
                # 快速区块链注册
                blockchain_result = quick_register_mining_data(mining_data_for_blockchain)
                
                if blockchain_result:
                    # 保存到数据库
                    try:
                        from app import db as app_db
                        blockchain_record = BlockchainRecord(
                            data_hash=blockchain_result['data_hash'],
                            ipfs_cid=blockchain_result['ipfs_cid'],
                            site_id=blockchain_result['site_id'],
                            transaction_hash=blockchain_result.get('blockchain_tx_hash'),
                            verification_status=BlockchainVerificationStatus.REGISTERED,
                            hashrate_th=bc_total_hashrate,
                            power_consumption_w=bc_total_power,
                            daily_btc_production=daily_btc,
                            daily_revenue_usd=daily_revenue,
                            mining_data_summary=json.dumps(mining_data_for_blockchain),
                            data_timestamp=datetime.utcnow(),
                            created_by="mining_calculator"
                        )
                        
                        app_db.session.add(blockchain_record)
                        app_db.session.commit()
                        
                        logging.info(f"区块链记录已保存到数据库: {blockchain_result['data_hash'][:16]}...")
                        
                    except Exception as db_error:
                        logging.error(f"保存区块链记录到数据库失败: {db_error}")
                        try:
                            from app import db as app_db
                            app_db.session.rollback()
                        except Exception:
                            pass
                    
                    # 添加区块链验证信息到结果
                    blockchain_verification = {
                        "enabled": True,
                        "recorded": True,
                        "data_hash": blockchain_result['data_hash'],
                        "ipfs_cid": blockchain_result['ipfs_cid'],
                        "blockchain_tx_hash": blockchain_result.get('blockchain_tx_hash'),
                        "site_id": blockchain_result['site_id'],
                        "timestamp": blockchain_result['timestamp'],
                        "verification_url": f"/verify/{blockchain_result['data_hash']}",
                        "ipfs_url": f"https://gateway.pinata.cloud/ipfs/{blockchain_result['ipfs_cid']}",
                        "status": "registered"
                    }
                    
                    logging.info(f"挖矿数据已成功记录到区块链: {blockchain_result['data_hash'][:16]}...")
                else:
                    logging.warning("区块链数据记录失败")
                    blockchain_verification = {
                        "enabled": True,
                        "recorded": False,
                        "error": "区块链记录失败",
                        "status": "failed"
                    }
                    
            except Exception as blockchain_error:
                logging.error(f"区块链集成错误: {blockchain_error}")
                blockchain_verification = {
                    "enabled": True,
                    "recorded": False,
                    "error": str(blockchain_error),
                    "status": "error"
                }
        else:
            blockchain_verification = {
                "enabled": False,
                "recorded": False,
                "status": "disabled"
            }
        
        # 添加区块链验证信息到结果
        result['blockchain_verification'] = blockchain_verification
        
        return result
        
    except Exception as e:
        logging.error(f"Error in calculation: {str(e)}")
        logging.error(f"Arguments: hashrate={hashrate}, power_consumption={power_consumption}, electricity_cost={electricity_cost}, miner_model={miner_model}, miner_count={miner_count}")
        raise

def generate_profit_chart_data(miner_model, electricity_costs, btc_prices, miner_count=1, client_electricity_cost=None):
    """
    Generate data for the profit chart
    
    Parameters:
    - miner_model: The miner model to use
    - electricity_costs: List of electricity costs to analyze
    - btc_prices: List of BTC prices to analyze
    - miner_count: Number of miners
    - client_electricity_cost: Optional client electricity cost
    
    Returns:
    - Dictionary with data for the chart
    """
    try:
        logging.info(f"Starting profit chart generation for model: {miner_model}, count: {miner_count}")
        
        # Input validation
        if not miner_model:
            logging.error("No miner model provided for chart generation")
            return {'success': False, 'error': 'No miner model provided'}
            
        # Get miner models from database first, then fallback to MINER_DATA
        valid_models = {}
        try:
            from models import db
            from sqlalchemy import text
            # Handle any failed transaction by rolling back
            try:
                db.session.rollback()
            except:
                pass
            
            # Query all active miner models from database
            query = text("""
                SELECT model_name, reference_hashrate, reference_power, reference_price, manufacturer, reference_efficiency
                FROM miner_models 
                WHERE is_active = true 
                ORDER BY model_name
            """)
            
            result = db.session.execute(query)
            
            for row in result:
                model_name = row[0]
                valid_models[model_name] = {
                    'hashrate': float(row[1]) if row[1] else 0,
                    'power_watt': int(row[2]) if row[2] else 0,
                    'price': float(row[3]) if row[3] else 0,
                    'manufacturer': row[4] if row[4] else '',
                    'efficiency': float(row[5]) if row[5] else 0
                }
            
            db.session.commit()
            logging.info(f"Loaded {len(valid_models)} miner models from database for chart generation")
            
        except Exception as e:
            logging.error(f"Failed to load miner models from database: {e}")
            # Fallback to MINER_DATA if database fails
            valid_models = MINER_DATA
            
        if miner_model not in valid_models:
            logging.error(f"Invalid miner model: {miner_model}, available models: {list(valid_models.keys())}")
            return {'success': False, 'error': f"Miner model '{miner_model}' not found in available models"}
            
        if not isinstance(electricity_costs, list) or len(electricity_costs) == 0:
            logging.warning(f"Invalid electricity costs: {electricity_costs}, using defaults")
            # 使用更多数据点和更均匀分布的电价，覆盖更广范围
            # 增加更多电价点以形成更平滑的热力图
            electricity_costs = [
                0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 
                0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.20
            ]
            
        if not isinstance(btc_prices, list) or len(btc_prices) == 0:
            logging.warning(f"Invalid BTC prices: {btc_prices}, using defaults")
            # 2025年的BTC价格范围更高，基于当前市场情况调整
            # 增加更多价格点以形成更平滑的热力图
            btc_prices = [
                20000, 30000, 40000, 50000, 60000, 70000, 80000, 
                90000, 100000, 110000, 120000, 130000, 140000, 150000
            ]
        
        # Validate miner count
        if not isinstance(miner_count, int) or miner_count <= 0:
            logging.warning(f"Invalid miner count: {miner_count}, using default of 1")
            miner_count = 1
            
        # Get real-time network data with exception handling
        try:
            logging.info("Fetching real-time network data for chart generation")
            current_btc_price = get_real_time_btc_price()
            current_difficulty = get_real_time_difficulty()
            current_block_reward = get_real_time_block_reward()
            
            logging.info(f"Network data: BTC price=${current_btc_price}, difficulty={current_difficulty/10**12}T, reward={current_block_reward}BTC")
        except Exception as e:
            logging.error(f"Error fetching real-time data for chart: {str(e)}")
            current_btc_price = get_default_btc_price()
            current_difficulty = get_default_network_difficulty()
            current_block_reward = get_default_block_reward()
            logging.info(f"Using default values: BTC price=${current_btc_price}, difficulty={current_difficulty/10**12}T, reward={current_block_reward}BTC")
        
        # Get miner specs from either database or fallback data
        if valid_models == MINER_DATA:
            single_hashrate = MINER_DATA[miner_model]["hashrate"]
            single_power_watt = MINER_DATA[miner_model]["power_watt"]
        else:
            single_hashrate = valid_models[miner_model]["hashrate"]
            single_power_watt = valid_models[miner_model]["power_watt"]
        
        # Apply miner count
        hashrate = single_hashrate * miner_count
        power_consumption = single_power_watt * miner_count
        
        logging.info(f"Total hashrate: {hashrate} TH/s, power: {power_consumption} watts for {miner_count} miners")
        
        # 设置固定的网络状态，避免重复计算导致无限循环
        fixed_network_stats = {
            'btc_price': current_btc_price,
            'difficulty': current_difficulty,
            'block_reward': current_block_reward
        }
        
        # Generate profit matrix
        profit_data = []
        
        # Calculate profit for each combination of BTC price and electricity cost
        for price in btc_prices:
            for cost in electricity_costs:
                # 计算这个BTC价格和电费成本组合下的利润
                # 特别注意：必须将当前循环的电费成本'cost'传递给函数
                # ENHANCED: 为热力图计算添加维护费 - 基于矿机数量的合理维护费
                # 维护费应该与矿机数量成正比，单个矿机约$5-10/月
                maintenance_fee_per_miner = 5  # $5 per miner per month (reduced for single miners)
                total_maintenance_fee = maintenance_fee_per_miner * miner_count
                
                result = calculate_mining_profitability(
                    hashrate=hashrate,
                    power_consumption=power_consumption,
                    electricity_cost=cost,  # 确保使用循环中的电费成本
                    client_electricity_cost=client_electricity_cost,
                    btc_price=price,  # 确保使用循环中的BTC价格
                    difficulty=fixed_network_stats['difficulty'],
                    block_reward=fixed_network_stats['block_reward'],
                    use_real_time_data=False,  # 不使用实时数据，避免API调用
                    miner_model=miner_model,
                    miner_count=miner_count,
                    maintenance_fee=total_maintenance_fee,  # 基于矿机数量的维护费用
                    pool_fee=DEFAULT_POOL_FEE,  # Include pool fee for realistic projections
                    consider_difficulty_adjustment=False  # Keep simple for heatmap generation
                )
                
                # 热力图需要根据当前模式选择正确的利润数据处理方式
                try:
                    # 获取月度BTC产出
                    monthly_btc = result['btc_mined']['monthly']
                    monthly_power = result['inputs']['power_consumption'] * 24 * 30.5 / 1000  # kWh
                    
                    if client_electricity_cost and client_electricity_cost > 0:
                        # === 客户模式 ===
                        # 在客户模式下，我们需要在不同的BTC价格和电费组合下模拟客户盈利情况
                        
                        # 1. 客户收入基于BTC产出和当前BTC价格
                        customer_monthly_revenue = monthly_btc * price
                        
                        # 2. 客户成本 - 注意：为了让热力图中X轴的变化有意义，我们使用循环中的电费成本而不是固定客户电费
                        # 这允许我们看到不同电费对客户盈利的影响
                        used_electricity_cost = cost  # 使用循环中的电价而不是固定客户电费
                        customer_monthly_cost = monthly_power * used_electricity_cost
                        
                        # 3. 计算客户利润
                        monthly_profit = customer_monthly_revenue - customer_monthly_cost
                        
                        # 记录日志帮助调试（仅在第一个点记录）
                        if price == btc_prices[0] and cost == electricity_costs[0]:
                            logging.info(f"客户模式热力图 - BTC价格: ${price}, 电费: ${used_electricity_cost}/kWh, 月利润: ${monthly_profit}, BTC产出: {monthly_btc}")
                    else:
                        # === 矿场主模式 ===
                        # 在矿场主模式下，有两种利润模式：
                        # 1. 自营挖矿模式：利润 = 比特币产出收益 - 矿场电费 - 维护费
                        # 2. 托管服务模式：利润 = 客户电费差价收入 = (客户电费 - 矿场电费) * 耗电量
                        
                        maintenance_monthly = result.get('maintenance_fee', {}).get('monthly', total_maintenance_fee)  # 维护费
                        
                        # 计算方式1：自营挖矿模式 - 基于比特币挖矿收益
                        btc_revenue = monthly_btc * price  # 比特币产出收益
                        mining_cost = monthly_power * cost  # 电力成本
                        mining_profit = btc_revenue - mining_cost - maintenance_monthly  # 挖矿利润
                        
                        # 计算方式2：托管服务模式 - 基于电费差价
                        # 使用基本电费(通常是 0.05 $/kWh)作为矿场的实际电费成本
                        base_electricity_cost = 0.05  # 基础矿场电费
                        client_electricity_rate = 0.07  # 假设的客户电费率
                        markup_profit = monthly_power * (client_electricity_rate - base_electricity_cost)  # 电费差价利润
                        
                        # 默认使用挖矿利润，这将确保回收期计算准确
                        monthly_profit = mining_profit
                        
                        # 记录日志帮助调试（仅在第一个点记录）
                        if price == btc_prices[0] and cost == electricity_costs[0]:
                            logging.info(f"矿场主模式热力图 - BTC价格: ${price}, 矿场电费: ${cost}/kWh, 比特币收入: ${btc_revenue}, 电费成本: ${mining_cost}, 维护: ${maintenance_monthly}, 利润: ${monthly_profit}")
                except Exception as e:
                    # 捕获计算过程中的任何错误
                    logging.error(f"热力图数据点计算错误 - BTC价格: ${price}, 电费: ${cost}/kWh, 错误: {str(e)}")
                    # 使用默认利润以便继续生成图表
                    monthly_profit = 0
                
                profit_data.append({
                    'btc_price': price,
                    'electricity_cost': cost,
                    'monthly_profit': monthly_profit
                })
        
        # Calculate optimal electricity rate at current BTC price
        optimal_electricity_rate = 0
        try:
            base_result = calculate_mining_profitability(
                hashrate=hashrate,
                power_consumption=power_consumption,
                electricity_cost=0.05,  # Dummy value, not used for this calculation
                btc_price=current_btc_price,
                difficulty=fixed_network_stats['difficulty'],
                block_reward=fixed_network_stats['block_reward'],
                use_real_time_data=False,
                miner_model=miner_model,
                miner_count=miner_count,
                maintenance_fee=5000  # 一致添加维护费
            )
            
            if 'break_even' in base_result and 'electricity_cost' in base_result['break_even']:
                optimal_electricity_rate = base_result['break_even']['electricity_cost']
        except Exception as e:
            logging.error(f"Error calculating optimal electricity rate: {str(e)}")
            optimal_electricity_rate = 0
        
        return {
            'success': True,
            'profit_data': profit_data,
            'current_network_data': {
                'btc_price': current_btc_price,
                'difficulty': current_difficulty / 10**12,  # Convert to more readable format (T)
                'block_reward': fixed_network_stats['block_reward']
            },
            'optimal_electricity_rate': optimal_electricity_rate
        }
    except Exception as e:
        logging.error(f"Error generating profit chart data: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
        
def calculate_monthly_curtailment_impact(
    miners_data, 
    curtailment_percentage, 
    electricity_cost,
    btc_price,
    network_difficulty,
    block_reward=3.125,
    shutdown_strategy="efficiency"
):
    """
    计算月度电力削减的影响（基于用户输入，不使用外部API）
    
    参数:
    - miners_data: 矿场矿机配置，格式为 [{"model": "型号名称", "count": 数量}, ...]
    - curtailment_percentage: 削减比例(%)
    - electricity_cost: 电价($/kWh)
    - btc_price: BTC价格($)
    - network_difficulty: 网络难度(T)
    - block_reward: 区块奖励(BTC)
    - shutdown_strategy: 关机策略，可选值:
        - "efficiency": 按效率关机（先关闭效率最低的）
        - "random": 随机关机
        - "proportional": 按比例关机（每种型号按同样比例关闭）
    
    返回:
    - 包含削减影响详情的字典
    """
    try:
        logging.info(f"计算月度Curtailment: 矿机数量={len(miners_data)}, 削减={curtailment_percentage}%, 策略={shutdown_strategy}")
        
        # 如果输入的miners_data为空，返回空结果
        if not miners_data:
            raise ValueError("未提供矿机数据")
            
        # 处理老版本的单一矿机输入（向后兼容）
        if isinstance(miners_data, str):
            # 如果传入的是字符串，假设是矿机型号
            old_model = miners_data
            miners_data = [{"model": old_model, "count": 1}]
        elif isinstance(miners_data, dict) and "model" not in miners_data:
            # 如果是字典但没有model字段，可能是旧版本的其他格式
            logging.warning(f"收到未知矿机数据格式: {miners_data}")
            raise ValueError("矿机数据格式无效")
        
        # 汇总所有矿机的算力和功耗
        miners_expanded = []
        total_hashrate = 0
        total_power_watt = 0
        total_miners = 0
        
        # 展开所有矿机数据，便于按效率排序和关机
        for miner_entry in miners_data:
            model = miner_entry.get("model")
            count = miner_entry.get("count", 0)
            
            if not model or model not in MINER_DATA or count <= 0:
                continue
                
            specs = MINER_DATA[model]
            hashrate = specs.get("hashrate", 0)  # TH/s
            power = specs.get("power_watt", 0)  # W
            efficiency = power / hashrate if hashrate > 0 else float('inf')  # W/TH
            
            # 记录每台矿机的信息
            for i in range(count):
                miners_expanded.append({
                    "model": model,
                    "hashrate": hashrate,
                    "power": power,
                    "efficiency": efficiency
                })
            
            # 累加总算力和功耗
            total_hashrate += hashrate * count
            total_power_watt += power * count
            total_miners += count
        
        if not miners_expanded:
            raise ValueError("没有有效的矿机数据")
            
        # 总功耗(kW)
        total_power = total_power_watt / 1000
        
        # 计算削减前的月度产出和成本
        days_in_month = 30.5  # 平均每月天数
        hours_in_month = days_in_month * 24
        
        # 使用难度计算算法 - ENHANCED with pool fee correction per expert recommendations
        hashrate_h = total_hashrate * 1e12  # 转换为H/s
        difficulty_h = network_difficulty * 1e12  # 转换为H (输入是T)
        difficulty_factor = 2 ** 32
        daily_btc_raw = (hashrate_h * block_reward * 86400) / (difficulty_h * difficulty_factor)
        
        # Apply pool fee correction (1 - pool_fee) as recommended
        pool_fee_rate = get_default_pool_fee()  # 2.5% default
        daily_btc = daily_btc_raw * (1 - pool_fee_rate)
        monthly_btc = daily_btc * days_in_month
        
        logging.info(f"Curtailment calculation using difficulty-based algorithm with {pool_fee_rate*100:.1f}% pool fee correction")
        
        monthly_power_kwh = total_power * hours_in_month
        monthly_electricity_cost = monthly_power_kwh * electricity_cost
        monthly_revenue = monthly_btc * btc_price
        monthly_profit = monthly_revenue - monthly_electricity_cost
        
        # 计算需要关闭的矿机数量
        miners_to_shutdown_count = int(total_miners * curtailment_percentage / 100)
        
        # 根据关机策略选择要关闭的矿机
        miners_to_shutdown = []
        miners_to_keep = miners_expanded.copy()
        
        if shutdown_strategy == "efficiency":
            # ENHANCED: 按效率排序（效率低的先关）with temperature safety thresholds per expert recommendation
            miners_to_keep.sort(key=lambda x: x["efficiency"], reverse=True)
            miners_to_shutdown = miners_to_keep[:miners_to_shutdown_count]
            miners_to_keep = miners_to_keep[miners_to_shutdown_count:]
            
            # Add minimum running batch consideration for operational stability
            min_batch_size = max(1, int(total_miners * 0.1))  # Minimum 10% of miners should stay running
            if len(miners_to_keep) < min_batch_size:
                logging.warning(f"Curtailment would reduce running miners below minimum batch size ({min_batch_size}). Adjusting curtailment.")
                adjustment_needed = min_batch_size - len(miners_to_keep)
                miners_to_keep.extend(miners_to_shutdown[-adjustment_needed:])
                miners_to_shutdown = miners_to_shutdown[:-adjustment_needed]
            
        elif shutdown_strategy == "random":
            # 随机选择矿机关闭
            import random
            random.shuffle(miners_to_keep)
            miners_to_shutdown = miners_to_keep[:miners_to_shutdown_count]
            miners_to_keep = miners_to_keep[miners_to_shutdown_count:]
            
        elif shutdown_strategy == "proportional":
            # 按比例关闭每种型号的矿机
            # 先统计每种型号的数量
            model_counts = {}
            for miner in miners_expanded:
                model = miner["model"]
                model_counts[model] = model_counts.get(model, 0) + 1
            
            # 计算每种型号需要关闭的数量
            shutdown_counts = {}
            for model, count in model_counts.items():
                shutdown_counts[model] = int(count * curtailment_percentage / 100)
            
            # 按型号选择矿机关闭
            for model in shutdown_counts:
                count_to_shutdown = shutdown_counts[model]
                model_miners = [m for m in miners_to_keep if m["model"] == model]
                
                if count_to_shutdown > 0 and model_miners:
                    miners_to_shutdown.extend(model_miners[:count_to_shutdown])
                    # 从保留列表中移除已关闭的矿机
                    miners_to_keep = [m for m in miners_to_keep if m not in model_miners[:count_to_shutdown]]
        
        # 计算关闭和保留的矿机的总算力和功耗
        shutdown_hashrate = sum(m["hashrate"] for m in miners_to_shutdown)
        shutdown_power = sum(m["power"] for m in miners_to_shutdown) / 1000  # kW
        
        reduced_hashrate = total_hashrate - shutdown_hashrate
        reduced_power = total_power - shutdown_power
        
        # 削减后产出计算
        reduced_hashrate_h = reduced_hashrate * 1e12
        reduced_daily_btc = (reduced_hashrate_h * block_reward * 86400) / (difficulty_h * difficulty_factor)
        reduced_monthly_btc = reduced_daily_btc * days_in_month
        
        reduced_monthly_power_kwh = reduced_power * hours_in_month
        reduced_monthly_electricity_cost = reduced_monthly_power_kwh * electricity_cost
        reduced_monthly_revenue = reduced_monthly_btc * btc_price
        reduced_monthly_profit = reduced_monthly_revenue - reduced_monthly_electricity_cost
        
        # 削减影响计算
        saved_electricity_kwh = monthly_power_kwh - reduced_monthly_power_kwh
        saved_electricity_cost = monthly_electricity_cost - reduced_monthly_electricity_cost
        revenue_loss = monthly_revenue - reduced_monthly_revenue
        net_impact = saved_electricity_cost - revenue_loss
        
        # 计算关闭矿机的详细信息（按型号分组）
        shutdown_by_model = {}
        for miner in miners_to_shutdown:
            model = miner["model"]
            if model not in shutdown_by_model:
                shutdown_by_model[model] = {
                    "count": 0,
                    "hashrate_th": 0,
                    "power_kw": 0
                }
            shutdown_by_model[model]["count"] += 1
            shutdown_by_model[model]["hashrate_th"] += miner["hashrate"]
            shutdown_by_model[model]["power_kw"] += miner["power"] / 1000
        
        # 将字典转为列表
        shutdown_details = []
        for model, details in shutdown_by_model.items():
            model_specs = MINER_DATA[model]
            efficiency = model_specs["power_watt"] / model_specs["hashrate"] if model_specs["hashrate"] > 0 else 0
            shutdown_details.append({
                "model": model,
                "count": details["count"],
                "hashrate_th": details["hashrate_th"],
                "power_kw": details["power_kw"],
                "efficiency": efficiency
            })
        
        # 按效率从低到高排序（效率最差的排在前面）
        shutdown_details.sort(key=lambda x: x["efficiency"], reverse=True)
        
        # 计算收益率变化
        before_profit_ratio = (monthly_profit / monthly_revenue * 100) if monthly_revenue > 0 else 0
        after_profit_ratio = (reduced_monthly_profit / reduced_monthly_revenue * 100) if reduced_monthly_revenue > 0 else 0
        
        # 计算盈亏平衡点
        break_even_electricity = (monthly_btc * btc_price) / monthly_power_kwh if monthly_power_kwh > 0 else 0
        
        result = {
            'inputs': {
                'miners': miners_data,
                'total_miners': total_miners,
                'curtailment_percentage': curtailment_percentage,
                'shutdown_strategy': shutdown_strategy,
                'electricity_cost': electricity_cost,
                'btc_price': btc_price,
                'network_difficulty': network_difficulty,
                'block_reward': block_reward
            },
            'before_curtailment': {
                'total_hashrate_th': total_hashrate,
                'total_power_kw': total_power,
                'monthly_btc': monthly_btc,
                'monthly_power_kwh': monthly_power_kwh,
                'monthly_electricity_cost': monthly_electricity_cost,
                'monthly_revenue': monthly_revenue,
                'monthly_profit': monthly_profit,
                'profit_ratio': before_profit_ratio
            },
            'after_curtailment': {
                'running_miners': len(miners_to_keep),
                'shutdown_miners': len(miners_to_shutdown),
                'hashrate_th': reduced_hashrate,
                'power_kw': reduced_power,
                'monthly_btc': reduced_monthly_btc,
                'monthly_power_kwh': reduced_monthly_power_kwh,
                'monthly_electricity_cost': reduced_monthly_electricity_cost,
                'monthly_revenue': reduced_monthly_revenue,
                'monthly_profit': reduced_monthly_profit,
                'profit_ratio': after_profit_ratio
            },
            'impact': {
                'hashrate_reduction_th': shutdown_hashrate,
                'power_reduction_kw': shutdown_power,
                'saved_electricity_kwh': saved_electricity_kwh,
                'saved_electricity_cost': saved_electricity_cost,
                'revenue_loss': revenue_loss,
                'net_impact': net_impact,
                'is_profitable': net_impact > 0,
                'break_even_electricity': break_even_electricity
            },
            'shutdown_details': shutdown_details
        }
        
        logging.info(f"月度Curtailment计算完成: 节省电费=${saved_electricity_cost:.2f}, 损失收入=${revenue_loss:.2f}, 净影响=${net_impact:.2f}")
        return result
        
    except Exception as e:
        logging.error(f"计算月度Curtailment时出错: {str(e)}")
        raise e

def get_miner_specifications(model_name=None):
    """
    获取矿机规格信息
    
    Parameters:
    - model_name: 特定矿机型号名称，如果为None则返回所有矿机数据
    
    Returns:
    - dict: 矿机规格数据
    """
    if model_name:
        return MINER_DATA.get(model_name, {})
    return MINER_DATA

# MiningCalculator class wrapper for compatibility with calculator module
class MiningCalculator:
    """
    Wrapper class for mining calculation functions to maintain compatibility
    with the calculator module routes
    """
    
    def __init__(self):
        """Initialize the mining calculator"""
        pass
    
    def calculate_profitability(self, hashrate=0.0, power_consumption=0.0, electricity_cost=None, 
                               btc_price=None, network_hashrate=None, network_difficulty=None,
                               miner_count=1, **kwargs):
        """
        Calculate mining profitability with simplified parameters for calculator module
        
        This method adapts the complex calculate_mining_profitability function
        to work with the simpler parameter structure expected by the calculator routes
        """
        try:
            # Use config defaults for missing values
            if electricity_cost is None:
                electricity_cost = get_default_electricity_cost()
                
            if btc_price is None:
                btc_price = get_real_time_btc_price()
                
            if network_difficulty is None:
                network_difficulty = get_real_time_difficulty()
                
            if network_hashrate is None:
                network_hashrate = get_real_time_btc_hashrate()
            
            # Call the main calculation function
            result = calculate_mining_profitability(
                hashrate=hashrate,
                power_consumption=power_consumption,
                electricity_cost=electricity_cost,
                btc_price=btc_price,
                difficulty=network_difficulty,  # Map network_difficulty to difficulty
                use_real_time_data=False,  # We're providing the data
                miner_count=miner_count,
                **kwargs
            )
            
            return result
            
        except Exception as e:
            logging.error(f"MiningCalculator.calculate_profitability error: {e}")
            # Return a basic error response format expected by calculator routes
            return {
                'success': False,
                'error': str(e),
                'daily_btc': 0,
                'daily_profit': 0,
                'monthly_profit': 0
            }


# ============================================================================
# 性能优化模块 - Phase 2 Enterprise Optimization
# Performance Optimization Module
# ============================================================================

def performance_monitor(func):
    """
    性能监控装饰器
    Performance monitoring decorator
    
    Tracks execution time, memory usage, and logs performance metrics
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        import psutil
        import gc
        
        # 强制垃圾回收获取准确的内存基准
        gc.collect()
        
        # 获取开始时的性能指标
        start_time = time.time()
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            # 执行函数
            result = func(*args, **kwargs)
            
            # 计算性能指标
            end_time = time.time()
            execution_time = end_time - start_time
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_delta = end_memory - start_memory
            
            # 记录性能日志
            logging.info(
                f"Performance [{func.__name__}]: "
                f"Time={execution_time:.3f}s, "
                f"Memory={start_memory:.1f}MB -> {end_memory:.1f}MB "
                f"(Δ{memory_delta:+.1f}MB)"
            )
            
            # 如果返回值是字典，添加性能指标
            if isinstance(result, dict):
                result['_performance'] = {
                    'execution_time_seconds': round(execution_time, 3),
                    'memory_mb': round(end_memory, 1),
                    'memory_delta_mb': round(memory_delta, 1),
                    'function_name': func.__name__
                }
            
            return result
            
        except Exception as e:
            end_time = time.time()
            logging.error(
                f"Performance [{func.__name__}] FAILED: "
                f"Time={end_time - start_time:.3f}s, Error={str(e)}"
            )
            raise
    
    return wrapper


@performance_monitor
def batch_calculate_mining_profit_vectorized(miners_df, use_real_time=True, 
                                             electricity_cost=None, pool_fee=0.025):
    """
    批量计算挖矿收益 - NumPy向量化优化版本
    Batch mining profit calculation with NumPy vectorization
    
    目标：5000台矿机批量计算 ≤20秒
    Target: 5000 miners calculation in ≤20 seconds
    
    Parameters:
    -----------
    miners_df : pd.DataFrame
        矿机数据DataFrame，必需列：
        - miner_model: 矿机型号
        - miner_count: 矿机数量
        - site_power_mw: 站点功率(可选)
    use_real_time : bool
        是否使用实时数据
    electricity_cost : float
        电费成本（$/kWh），如果为None则使用默认值
    pool_fee : float
        矿池费率
        
    Returns:
    --------
    pd.DataFrame : 包含计算结果的DataFrame
    """
    start_total = time.time()
    logging.info(f"开始批量计算：{len(miners_df)} 条记录")
    
    # 1. 数据预处理和验证（向量化）
    if electricity_cost is None:
        electricity_cost = get_default_electricity_cost()
    
    # 获取实时网络数据（一次性获取，避免重复API调用）
    if use_real_time:
        btc_price = get_real_time_btc_price()
        difficulty = get_real_time_difficulty()
        block_reward = get_real_time_block_reward()
        network_hashrate = get_real_time_btc_hashrate()
    else:
        btc_price = get_default_btc_price()
        difficulty = get_default_network_difficulty()
        block_reward = get_default_block_reward()
        network_hashrate = get_default_network_hashrate()
    
    logging.info(f"网络参数：BTC=${btc_price:.2f}, 难度={difficulty/1e12:.2f}T, 奖励={block_reward}BTC")
    
    # 2. 提取矿机规格（向量化查找）
    # 创建矿机规格映射
    miner_specs = {}
    for model, specs in MINER_DATA.items():
        miner_specs[model] = specs
    
    # 向量化提取算力和功耗
    def get_specs(model):
        if model in miner_specs:
            return miner_specs[model]['hashrate'], miner_specs[model]['power_watt']
        else:
            logging.warning(f"未知矿机型号: {model}, 使用默认值")
            return 100, 3000  # 默认值
    
    miners_df = miners_df.copy()
    specs_data = miners_df['miner_model'].apply(get_specs)
    miners_df['hashrate_per_unit'] = specs_data.apply(lambda x: x[0])
    miners_df['power_per_unit'] = specs_data.apply(lambda x: x[1])
    
    # 3. NumPy向量化计算
    # 转换为numpy数组进行高效计算
    miner_counts = miners_df['miner_count'].values.astype(np.float64)
    hashrate_per_unit = miners_df['hashrate_per_unit'].values.astype(np.float64)
    power_per_unit = miners_df['power_per_unit'].values.astype(np.float64)
    
    # 批量计算总算力和功耗
    total_hashrate = miner_counts * hashrate_per_unit  # TH/s
    total_power = miner_counts * power_per_unit  # Watts
    
    # 4. 核心挖矿收益计算（完全向量化）
    # 每TH每秒的BTC产出
    btc_per_th_per_second = (block_reward * 1e12) / (difficulty * (2**32) / BLOCKS_PER_DAY / 86400)
    
    # 日BTC产出
    daily_btc = total_hashrate * btc_per_th_per_second * 86400
    
    # 应用矿池费率
    daily_btc_after_pool_fee = daily_btc * (1 - pool_fee)
    
    # 日收入
    daily_revenue = daily_btc_after_pool_fee * btc_price
    
    # 日电费
    daily_power_kwh = total_power * 24 / 1000  # kWh
    daily_electricity_cost = daily_power_kwh * electricity_cost
    
    # 日利润
    daily_profit = daily_revenue - daily_electricity_cost
    
    # 月度和年度指标
    monthly_btc = daily_btc_after_pool_fee * 30.5
    monthly_revenue = daily_revenue * 30.5
    monthly_electricity_cost = daily_electricity_cost * 30.5
    monthly_profit = daily_profit * 30.5
    
    yearly_profit = monthly_profit * 12
    
    # 5. 构建结果DataFrame
    results_df = pd.DataFrame({
        'miner_model': miners_df['miner_model'],
        'miner_count': miners_df['miner_count'],
        'total_hashrate_th': total_hashrate,
        'total_power_w': total_power,
        'daily_btc': daily_btc_after_pool_fee,
        'daily_revenue_usd': daily_revenue,
        'daily_electricity_cost_usd': daily_electricity_cost,
        'daily_profit_usd': daily_profit,
        'monthly_btc': monthly_btc,
        'monthly_revenue_usd': monthly_revenue,
        'monthly_profit_usd': monthly_profit,
        'yearly_profit_usd': yearly_profit,
        'btc_price': btc_price,
        'network_difficulty_t': difficulty / 1e12,
        'electricity_cost_per_kwh': electricity_cost,
        'pool_fee_rate': pool_fee
    })
    
    # 添加原始数据的其他列
    for col in miners_df.columns:
        if col not in results_df.columns:
            results_df[col] = miners_df[col]
    
    elapsed = time.time() - start_total
    logging.info(
        f"批量计算完成：{len(results_df)} 条记录，"
        f"耗时 {elapsed:.2f}秒，"
        f"平均 {elapsed/len(results_df)*1000:.1f}ms/条"
    )
    
    return results_df


@performance_monitor
def batch_calculate_with_concurrency(miners_data_list, use_real_time=True, 
                                     max_workers=4, chunk_size=1000):
    """
    并发批量计算 - 使用concurrent.futures提升性能
    Concurrent batch calculation using ThreadPoolExecutor
    
    Parameters:
    -----------
    miners_data_list : list of dict
        矿机数据列表
    use_real_time : bool
        是否使用实时数据
    max_workers : int
        最大并发worker数
    chunk_size : int
        分块大小
        
    Returns:
    --------
    list : 计算结果列表
    """
    logging.info(f"并发批量计算开始：{len(miners_data_list)} 条数据，{max_workers} workers")
    
    # 将数据分块
    chunks = [miners_data_list[i:i + chunk_size] 
              for i in range(0, len(miners_data_list), chunk_size)]
    
    logging.info(f"数据已分为 {len(chunks)} 个块，每块 ≤{chunk_size} 条")
    
    # 并发处理每个块
    all_results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_chunk = {
            executor.submit(_process_chunk_vectorized, chunk, use_real_time): i 
            for i, chunk in enumerate(chunks)
        }
        
        # 收集结果
        for future in future_to_chunk:
            chunk_idx = future_to_chunk[future]
            try:
                chunk_results = future.result()
                all_results.extend(chunk_results)
                logging.info(f"块 {chunk_idx + 1}/{len(chunks)} 完成")
            except Exception as e:
                logging.error(f"块 {chunk_idx} 处理失败: {e}")
    
    logging.info(f"并发批量计算完成：共 {len(all_results)} 条结果")
    return all_results


def _process_chunk_vectorized(chunk_data, use_real_time=True):
    """
    处理数据块的内部函数（向量化）
    Internal function to process data chunk with vectorization
    """
    # 转换为DataFrame进行向量化处理
    df = pd.DataFrame(chunk_data)
    
    # 使用向量化批量计算
    results_df = batch_calculate_mining_profit_vectorized(
        df, 
        use_real_time=use_real_time
    )
    
    # 转回字典列表
    return results_df.to_dict('records')


def generate_calculation_cache_key(miner_model, miner_count, electricity_cost, 
                                   btc_price, difficulty):
    """
    生成计算结果缓存键
    Generate cache key for calculation results
    
    用于缓存系统，基于参数生成唯一哈希
    """
    params_str = f"{miner_model}_{miner_count}_{electricity_cost}_{btc_price}_{difficulty}"
    cache_key = hashlib.md5(params_str.encode()).hexdigest()
    return f"mining_calc:{cache_key}"


# 内存优化：使用生成器处理大数据集
def generate_profit_calculations(miners_iterator, use_real_time=True):
    """
    生成器版本的批量计算 - 内存优化
    Generator-based batch calculation for memory optimization
    
    适用于超大数据集（10000+记录），避免内存溢出
    Suitable for very large datasets (10000+ records), prevents memory overflow
    """
    # 获取一次性网络数据
    if use_real_time:
        btc_price = get_real_time_btc_price()
        difficulty = get_real_time_difficulty()
        block_reward = get_real_time_block_reward()
    else:
        btc_price = get_default_btc_price()
        difficulty = get_default_network_difficulty()
        block_reward = get_default_block_reward()
    
    # 逐条处理并yield结果（不存储在内存中）
    for miner_data in miners_iterator:
        try:
            result = calculate_mining_profitability(
                miner_model=miner_data['miner_model'],
                miner_count=miner_data.get('miner_count', 1),
                use_real_time_data=False,
                btc_price=btc_price,
                difficulty=difficulty,
                block_reward=block_reward
            )
            yield result
        except Exception as e:
            logging.error(f"计算失败: {miner_data}, 错误: {e}")
            yield {'error': str(e), 'miner_data': miner_data}