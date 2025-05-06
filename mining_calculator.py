import numpy as np
import pandas as pd
import requests
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)

# 导入多币种数据
from crypto_data import CRYPTOCURRENCIES, MINER_DATA_BY_ALGORITHM, get_real_time_crypto_price, get_real_time_network_data, get_miners_for_crypto

# Constants - 保留原始BTC常量作为向后兼容
BLOCKS_PER_DAY = 144  # BTC区块时间
DEFAULT_BTC_PRICE = 80000  # USD
DEFAULT_NETWORK_DIFFICULTY = 119116256505723  # ~119.12T
DEFAULT_NETWORK_HASHRATE = 900  # EH/s
BLOCK_REWARD = 3.125  # BTC

# Fixed miner data including hashrate and power consumption for each model - 保留原来的BTC矿机数据作为向后兼容
MINER_DATA = MINER_DATA_BY_ALGORITHM.get("SHA-256", {})

def calculate_roi(investment, yearly_profit, monthly_profit, btc_price, forecast_months=36):
    """
    Calculate ROI metrics and forecast data for investment analysis
    
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
            "payback_period_months": float('inf'),
            "payback_period_years": float('inf'),
            "forecast": []
        }
    
    # Annual ROI percentage
    roi_percent_annual = (yearly_profit / investment) * 100
    
    # Payback period (in months and years)
    payback_period_months = investment / monthly_profit if monthly_profit > 0 else float('inf')
    payback_period_years = payback_period_months / 12 if monthly_profit > 0 else float('inf')
    
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
    """Get the current Bitcoin price from CoinGecko API"""
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data['bitcoin']['usd'])
    except Exception as e:
        logging.warning(f"Unable to get real-time BTC price: {e}")
        return DEFAULT_BTC_PRICE

def get_real_time_difficulty():
    """Get the current Bitcoin network difficulty with fallback options"""
    # 尝试多个API源以增加可靠性
    apis = [
        'https://blockchain.info/q/getdifficulty',
        'https://api.blockchain.info/stats'  # 备用API提供一个包含difficulty的JSON
    ]
    
    for api_url in apis:
        try:
            response = requests.get(api_url, timeout=5)  # 减少超时时间以避免长时间等待
            
            if response.status_code == 200:
                if 'stats' in api_url:  # 处理JSON格式的响应
                    data = response.json()
                    if 'difficulty' in data:
                        return float(data['difficulty'])
                else:  # 处理纯文本响应
                    return float(response.text.strip())
            else:
                logging.warning(f"API {api_url} 返回状态码 {response.status_code}")
                # 继续尝试下一个API
                
        except Exception as e:
            logging.warning(f"尝试从 {api_url} 获取难度时出错: {e}")
            # 继续尝试下一个API
    
    # 所有API都失败时，使用默认值
    logging.warning(f"无法从任何API获取实时BTC难度，使用默认值 {DEFAULT_NETWORK_DIFFICULTY}")
    return DEFAULT_NETWORK_DIFFICULTY

def get_real_time_block_reward():
    """Get the current Bitcoin block reward based on block height"""
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
            return block_reward
        else:
            raise Exception(f"API returned status code {response.status_code}")
    except Exception as e:
        logging.warning(f"Unable to get real-time BTC block reward: {e}")
        return BLOCK_REWARD
        
def get_real_time_btc_hashrate():
    """获取实时比特币网络哈希率"""
    try:
        response = requests.get('https://blockchain.info/q/hashrate', timeout=5)
        if response.status_code == 200:
            hashrate_th = float(response.text.strip())  # 原始数据为 TH/s
            hashrate_eh = hashrate_th / 1e9  # 转换为 EH/s (1 EH/s = 1,000,000,000 TH/s)
            logging.info(f"成功获取网络哈希率: {hashrate_th} TH/s = {hashrate_eh} EH/s")
            return hashrate_eh
        else:
            logging.warning(f"获取哈希率API返回状态码: {response.status_code}")
            return DEFAULT_NETWORK_HASHRATE
    except Exception as e:
        logging.warning(f"无法获取实时BTC网络哈希率，使用默认值 {DEFAULT_NETWORK_HASHRATE} EH/s: {e}")
        return DEFAULT_NETWORK_HASHRATE

def calculate_mining_profitability(hashrate=0.0, power_consumption=0.0, electricity_cost=0.05, client_electricity_cost=None, 
                             btc_price=None, difficulty=None, block_reward=None, use_real_time_data=True, miner_model=None, miner_count=1, site_power_mw=None, curtailment=0.0, 
                             host_investment=0.0, client_investment=0.0, maintenance_fee=0.0, crypto_symbol="BTC"):
    """
    Calculate cryptocurrency mining profitability
    
    Parameters:
    - hashrate: Mining hashrate in appropriate unit for the selected cryptocurrency
    - power_consumption: Power consumption in watts
    - electricity_cost: Electricity cost in USD per kWh
    - client_electricity_cost: Electricity cost charged to customers (USD per kWh)
    - btc_price: Current cryptocurrency price in USD (optional if use_real_time_data=True)
    - difficulty: Network difficulty (optional if use_real_time_data=True) 
    - use_real_time_data: Whether to fetch real-time data from APIs
    - miner_model: Optional miner model name to use pre-defined values
    - miner_count: Number of miners (default is 1)
    - site_power_mw: Site power in megawatts - will override miner count if provided with miner_model
    - curtailment: Power curtailment percentage (0-100)
    - host_investment: Total investment made by mining site owner (USD)
    - client_investment: Total investment made by client (USD)
    - maintenance_fee: Monthly maintenance fee in USD (default is 0)
    - crypto_symbol: Cryptocurrency symbol (BTC, LTC, ETC, etc.)
    
    Returns:
    - Dictionary containing profitability metrics including ROI calculations
    """
    try:
        # Get cryptocurrency specific data and defaults
        crypto_data = CRYPTOCURRENCIES.get(crypto_symbol, CRYPTOCURRENCIES["BTC"])
        crypto_algorithm = crypto_data.get("algorithm", "SHA-256")
        
        # Get appropriate miner data for the cryptocurrency algorithm
        miner_data_for_algorithm = MINER_DATA_BY_ALGORITHM.get(crypto_algorithm, MINER_DATA)
        
        # Log selected cryptocurrency
        logging.info(f"Calculating profitability for {crypto_symbol} using {crypto_algorithm} algorithm")
        
        # Get values from miner model if provided
        if miner_model and miner_model in miner_data_for_algorithm:
            # Get single miner specs
            single_hashrate = miner_data_for_algorithm[miner_model]["hashrate"]
            single_power_watt = miner_data_for_algorithm[miner_model]["power_watt"]
            
            # Calculate miner count from site power if provided
            if site_power_mw and site_power_mw > 0:
                # Formula from original code: site_miner_count = int((site_power_mw * 1000) / (power_watt / 1000))
                miner_count = int((site_power_mw * 1000) / (single_power_watt / 1000))
                logging.info(f"Calculated {miner_count} miners for {site_power_mw} MW using {miner_model}")
            
            # Apply miner count to get total specs
            hashrate = single_hashrate * miner_count
            power_consumption = single_power_watt * miner_count
        
        # Set cryptocurrency-specific default values
        default_price = crypto_data.get("default_price", DEFAULT_BTC_PRICE)
        default_difficulty = crypto_data.get("default_difficulty", DEFAULT_NETWORK_DIFFICULTY / 10**12)  # Convert to appropriate scale
        default_hashrate = crypto_data.get("default_hashrate", DEFAULT_NETWORK_HASHRATE)
        default_block_reward = crypto_data.get("default_block_reward", BLOCK_REWARD)
        blocks_per_day = 86400 / crypto_data.get("block_time", 600)  # Default is BTC block time (600 seconds)
        
        # Log cryptocurrency parameters
        logging.info(f"Using {crypto_symbol} parameters - Block time: {crypto_data.get('block_time', 600)}s, Blocks per day: {blocks_per_day}")
        
        # Get real-time data if requested
        if use_real_time_data:
            if crypto_symbol == "BTC":
                # Use Bitcoin-specific functions
                real_time_crypto_price = get_real_time_btc_price()
                difficulty_raw = get_real_time_difficulty()
                real_time_network_hashrate = get_real_time_btc_hashrate() or default_hashrate
                current_block_reward = get_real_time_block_reward()
            else:
                # Use generic functions for other cryptocurrencies
                real_time_crypto_price = get_real_time_crypto_price(crypto_symbol)
                
                # Get network data (difficulty, hashrate, block reward)
                network_data = get_real_time_network_data(crypto_symbol)
                if network_data:
                    difficulty_raw = network_data.get('difficulty', default_difficulty)
                    if crypto_symbol == "BTC":
                        difficulty_raw = difficulty_raw * 10**12  # Convert from T to raw value if BTC
                    real_time_network_hashrate = network_data.get('hashrate', default_hashrate)
                    current_block_reward = network_data.get('block_reward', default_block_reward)
                else:
                    # Use defaults if network data is not available
                    difficulty_raw = default_difficulty
                    if crypto_symbol == "BTC":
                        difficulty_raw = difficulty_raw * 10**12  # Convert from T to raw value if BTC
                    real_time_network_hashrate = default_hashrate
                    current_block_reward = default_block_reward
        else:
            # Use provided values or defaults
            real_time_crypto_price = btc_price or default_price
            difficulty_raw = difficulty or (default_difficulty * 10**12 if crypto_symbol == "BTC" else default_difficulty)
            real_time_network_hashrate = default_hashrate
            current_block_reward = default_block_reward
        
        # Use provided values if given
        crypto_price = btc_price or real_time_crypto_price
        difficulty = difficulty_raw
        block_reward_to_use = block_reward or current_block_reward
        
        # === PERFORM EXACT CALCULATION FROM ORIGINAL CODE ===
        
        # === 矿机数量 & 总算力计算 (Miner Count & Total Hashrate Calculation) ===
        # 确保我们有有效的网络哈希率（确保从未为零）
        curtailment_factor = max(0, min(1, (100 - curtailment) / 100))
        site_total_hashrate = hashrate * curtailment_factor if hashrate is not None else 0
        
        # 计算运行中和停机的矿机数量
        running_miner_count = int(miner_count * curtailment_factor)
        shutdown_miner_count = miner_count - running_miner_count
        
        # 添加日志，记录限电率和矿机数量计算结果
        logging.info(f"Curtailment计算: 限电率={curtailment}%, 系数={curtailment_factor}, 总矿机={miner_count}, 运行={running_miner_count}, 停机={shutdown_miner_count}")
        
        # === 加密货币产出计算 (Cryptocurrency Output Calculation) ===
        # 获取加密货币特定的区块时间和每日区块数
        block_time = crypto_data.get("block_time", 600)  # 区块时间，默认为BTC的600秒
        daily_blocks = 86400 / block_time  # 每日区块数
        
        # Method 1: Network Hashrate Based (算法1：基于网络实际哈希率)
        # 使用API返回的实际网络哈希率进行计算，但增加合理性检查
        difficulty_factor = 2 ** 32
        
        # 按币种获取网络哈希率的转换单位
        hashrate_unit = crypto_data.get("unit", "TH/s")
        
        # 计算基于难度的参考哈希率，用于合理性检查
        block_time_to_use = crypto_data.get("block_time", 600)
        network_hashrate_from_difficulty = (difficulty_raw * difficulty_factor) / block_time_to_use  # H/s
        
        # 转换网络哈希率到适当单位
        unit_multiplier = 1
        if hashrate_unit == "TH/s":
            network_standard_from_difficulty = network_hashrate_from_difficulty / 1e12
            if crypto_symbol == "BTC":
                api_network_standard = real_time_network_hashrate * 1000000  # EH/s → TH/s
            else:
                api_network_standard = real_time_network_hashrate
            unit_multiplier = 1
        elif hashrate_unit == "GH/s":
            network_standard_from_difficulty = network_hashrate_from_difficulty / 1e9
            api_network_standard = real_time_network_hashrate * 1000  # TH/s → GH/s
            unit_multiplier = 1e-3
        elif hashrate_unit == "MH/s":
            network_standard_from_difficulty = network_hashrate_from_difficulty / 1e6
            api_network_standard = real_time_network_hashrate * 1000000  # TH/s → MH/s
            unit_multiplier = 1e-6
        elif hashrate_unit == "kSol/s":
            network_standard_from_difficulty = network_hashrate_from_difficulty / 1e3
            api_network_standard = real_time_network_hashrate * 1000  # MSol/s → kSol/s
            unit_multiplier = 1e-3
        else:
            # 默认转换为TH/s
            network_standard_from_difficulty = network_hashrate_from_difficulty / 1e12
            api_network_standard = real_time_network_hashrate
            unit_multiplier = 1
        
        # 比较API哈希率和难度推导哈希率的差异
        hashrate_ratio = api_network_standard / max(1, network_standard_from_difficulty)
        
        # 如果API哈希率与难度推导哈希率相差过大(>50%)，使用加权平均值
        if hashrate_ratio > 1.5 or hashrate_ratio < 0.67:
            logging.info(f"API哈希率与难度推导哈希率差异过大 (比率: {hashrate_ratio:.2f})，使用加权平均值")
            network_standard = (api_network_standard * 0.4 + network_standard_from_difficulty * 0.6)  # 偏向难度推导值，因为更稳定
        else:
            # 差异在合理范围内，直接使用API返回的哈希率
            network_standard = api_network_standard
            
        # 确保最小值，不同币种的最小值不同
        min_hashrate = 1
        if crypto_symbol == "BTC":
            min_hashrate = 1000  # TH/s
        elif crypto_symbol in ["LTC", "DOGE"]:
            min_hashrate = 100  # GH/s
        elif crypto_symbol in ["ETC", "RVN"]:
            min_hashrate = 10  # MH/s
        elif crypto_symbol == "ZEC":
            min_hashrate = 10  # kSol/s
            
        network_standard = max(min_hashrate, network_standard)
        
        # 全网日产出 = 区块奖励 * 每日区块数
        network_daily_output = block_reward_to_use * daily_blocks
        
        # 每单位算力每日产出 = 全网日产出 / 全网算力
        coin_per_unit = network_daily_output / network_standard
        
        # 矿场每日产出 = 矿场算力 * 每单位算力产出
        site_daily_output = site_total_hashrate * coin_per_unit
        site_monthly_output = site_daily_output * 30.5
        
        # 打印推导的网络哈希率与API返回的对比，便于调试
        logging.info(f"API Network Hashrate: {api_network_standard:.2f} {hashrate_unit} vs Derived from Difficulty: {network_standard_from_difficulty:.2f} {hashrate_unit}")
        
        # 计算单个矿机每日产出
        single_miner_hashrate = None
        if miner_model and miner_model in miner_data_for_algorithm:
            single_miner_hashrate = miner_data_for_algorithm[miner_model]["hashrate"]
        daily_coin_per_miner = coin_per_unit * (single_miner_hashrate if single_miner_hashrate else (hashrate / max(1, miner_count)))
        
        # Method 2: Difficulty Based (算法2：基于难度)
        # 矿场H/s = 矿场单位算力 * 单位转换
        site_hashrate_Hs = site_total_hashrate
        if hashrate_unit == "TH/s":
            site_hashrate_Hs = site_total_hashrate * 1e12
        elif hashrate_unit == "GH/s":
            site_hashrate_Hs = site_total_hashrate * 1e9
        elif hashrate_unit == "MH/s":
            site_hashrate_Hs = site_total_hashrate * 1e6
        elif hashrate_unit == "kSol/s":
            site_hashrate_Hs = site_total_hashrate * 1e3
            
        difficulty_factor = 2 ** 32
        site_daily_output_difficulty = (site_hashrate_Hs * block_reward_to_use * 86400) / (difficulty_raw * difficulty_factor)
        site_monthly_output_difficulty = site_daily_output_difficulty * 30.5
        
        # 打印两种算法的结果，方便调试
        logging.info(f"Algorithm 1 (Network Based) - Daily {crypto_symbol}: {site_daily_output:.8f}")
        logging.info(f"Algorithm 2 (Difficulty Based) - Daily {crypto_symbol}: {site_daily_output_difficulty:.8f}")
        
        # 使用难度方法的结果作为最终结果（更准确）
        # 如果两种方法差异过大(>100%)，使用算法2
        algo1_algo2_ratio = site_daily_output / site_daily_output_difficulty if site_daily_output_difficulty > 0 else float('inf')
        
        if algo1_algo2_ratio > 2 or algo1_algo2_ratio < 0.5:
            logging.info(f"警告: 算法1和算法2结果相差过大 (比率: {algo1_algo2_ratio:.2f})，使用算法2(基于难度)的结果")
            daily_coin = site_daily_output_difficulty
            monthly_coin = site_monthly_output_difficulty
        else:
            # 差异在允许范围内，两种方法平均值
            daily_coin = (site_daily_output + site_daily_output_difficulty) / 2
            monthly_coin = (site_monthly_output + site_monthly_output_difficulty) / 2
        
        # === 成本计算 (Cost Calculation) ===
        # Calculate using the operating time after curtailment
        monthly_power_consumption = power_consumption * 24 * 30.5 * curtailment_factor / 1000  # kWh
        electricity_expense = monthly_power_consumption * electricity_cost
        client_electricity_expense = monthly_power_consumption * (client_electricity_cost or electricity_cost)
        
        # === 收入 & 利润计算 (Revenue & Profit Calculation) ===
        monthly_revenue = monthly_coin * crypto_price
        
        # 矿场主的加密货币挖矿收益，减去电费和维护费
        monthly_mining_profit = monthly_revenue - electricity_expense - maintenance_fee
        
        # 矿场主的电费差价收益（如果提供了客户电费且高于矿场电费）
        monthly_electricity_markup = 0
        if client_electricity_cost and client_electricity_cost > electricity_cost:
            # 计算电费差价收益 = (客户电费 - 矿场电费) * 电力消耗
            monthly_electricity_markup = (client_electricity_cost - electricity_cost) * monthly_power_consumption
            logging.info(f"电费差价收益: ${monthly_electricity_markup} = (${client_electricity_cost} - ${electricity_cost}) * {monthly_power_consumption}kWh")
        
        # 矿场主总收益 = 挖矿收益 + 电费差价收益
        monthly_profit = monthly_mining_profit
        if client_electricity_cost:  # 如果是托管模式，使用电费差价作为收益
            monthly_profit = monthly_electricity_markup
        
        # 客户收益需要减去电费和维护费（与矿场主挖矿收益计算方式一样）
        client_monthly_profit = monthly_revenue - client_electricity_expense - maintenance_fee
        
        # === 最优电价 (Optimal Electricity Rate) 计算 ===
        optimal_electricity_rate = (monthly_coin * crypto_price) / monthly_power_consumption if monthly_power_consumption > 0 else 0
        
        # === 最优削减比例 (Optimal Curtailment) 计算 ===
        if electricity_cost > optimal_electricity_rate and optimal_electricity_rate > 0:
            optimal_curtailment = max(0, min(100, 100 * (1 - (optimal_electricity_rate / electricity_cost))))
        else:
            optimal_curtailment = 0
            
        # === 矿机运行状态计算 (重命名变量，之前已计算过) ===
        # running_miners 和 shutdown_miners 已经在前面计算为 running_miner_count 和 shutdown_miner_count
        
        # 计算每日维护费
        daily_maintenance_fee = maintenance_fee / 30.5
        
        # Scale back to get daily values
        daily_revenue = monthly_revenue / 30.5
        daily_profit = monthly_profit / 30.5  # 这里已经考虑了维护费，因为monthly_profit包含维护费
        daily_electricity_expense = electricity_expense / 30.5
        client_daily_profit = client_monthly_profit / 30.5
        client_daily_electricity_expense = client_electricity_expense / 30.5
        
        # 计算年度维护费
        yearly_maintenance_fee = maintenance_fee * 12
        
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
            host_roi_data = calculate_roi(host_investment, yearly_profit, monthly_profit, crypto_price)
            logging.info(f"矿场主ROI计算结果 - 年化回报率: {host_roi_data['roi_percent_annual']}%, 回收期: {host_roi_data['payback_period_months']}月")
            
        if client_investment > 0:
            client_roi_data = calculate_roi(client_investment, client_yearly_profit, client_monthly_profit, crypto_price)
            logging.info(f"客户ROI计算结果 - 年化回报率: {client_roi_data['roi_percent_annual']}%, 回收期: {client_roi_data['payback_period_months']}月")
            
        # Return results in a consistent format with our previous implementation
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'crypto_symbol': crypto_symbol,
            'hashrate_unit': hashrate_unit,
            'network_data': {
                'crypto_price': crypto_price,
                'network_difficulty': difficulty / 10**12,  # Convert to more readable format (T)
                'network_hashrate': real_time_network_hashrate,  # EH/s or appropriate unit
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
                'effective_hashrate': site_total_hashrate,
                'host_investment': host_investment,
                'client_investment': client_investment
            },
            'maintenance_fee': {
                'daily': daily_maintenance_fee,
                'monthly': maintenance_fee,
                'yearly': yearly_maintenance_fee
            },
            'coin_mined': {
                'daily': daily_coin,
                'monthly': monthly_coin,
                'yearly': monthly_coin * 12,
                'per_unit_daily': coin_per_unit,
                'method1': {
                    'daily': site_daily_output,
                    'monthly': site_monthly_output
                },
                'method2': {
                    'daily': site_daily_output_difficulty,
                    'monthly': site_monthly_output_difficulty
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
            'client_electricity_cost': {
                'daily': client_daily_electricity_expense,
                'monthly': client_electricity_expense,
                'yearly': client_yearly_electricity_expense
            },
            'break_even': {
                'electricity_cost': optimal_electricity_rate,
                'crypto_price': (electricity_expense / monthly_coin) if monthly_coin > 0 else 0,
                'btc_price': (electricity_expense / monthly_coin) if monthly_coin > 0 else 0  # 为了向后兼容
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
        
    except Exception as e:
        logging.error(f"Error in calculation: {str(e)}")
        logging.error(f"Arguments: hashrate={hashrate}, power_consumption={power_consumption}, electricity_cost={electricity_cost}, miner_model={miner_model}, miner_count={miner_count}")
        raise

def generate_profit_chart_data(miner_model, electricity_costs, crypto_prices, miner_count=1, client_electricity_cost=None, crypto_symbol="BTC"):
    """
    Generate data for the profit chart
    
    Parameters:
    - miner_model: The miner model to use
    - electricity_costs: List of electricity costs to analyze
    - crypto_prices: List of cryptocurrency prices to analyze
    - miner_count: Number of miners
    - client_electricity_cost: Optional client electricity cost
    - crypto_symbol: Cryptocurrency symbol (default: "BTC")
    
    Returns:
    - Dictionary with data for the chart
    """
    try:
        logging.info(f"Starting profit chart generation for model: {miner_model}, count: {miner_count}")
        
        # Input validation
        if not miner_model:
            logging.error("No miner model provided for chart generation")
            return {'success': False, 'error': 'No miner model provided'}
            
        if miner_model not in MINER_DATA:
            logging.error(f"Invalid miner model: {miner_model}, available models: {list(MINER_DATA.keys())}")
            return {'success': False, 'error': f"Miner model '{miner_model}' not found in available models"}
        
        if not isinstance(electricity_costs, list) or len(electricity_costs) == 0:
            logging.warning(f"Invalid electricity costs: {electricity_costs}, using defaults")
            # 使用更多数据点和更均匀分布的电价，覆盖更广范围
            # 增加更多电价点以形成更平滑的热力图
            electricity_costs = [
                0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 
                0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.20
            ]
            
        if not isinstance(crypto_prices, list) or len(crypto_prices) == 0:
            logging.warning(f"Invalid cryptocurrency prices: {crypto_prices}, using defaults")
            # 2025年的加密货币价格范围，基于当前市场情况调整
            # 增加更多价格点以形成更平滑的热力图
            if crypto_symbol == "BTC":
                crypto_prices = [
                    20000, 30000, 40000, 50000, 60000, 70000, 80000, 
                    90000, 100000, 110000, 120000, 130000, 140000, 150000
                ]
            elif crypto_symbol in ["LTC", "ETC"]:
                crypto_prices = [
                    50, 75, 100, 125, 150, 175, 200, 
                    225, 250, 275, 300, 325, 350, 375
                ]
            elif crypto_symbol in ["DOGE", "RVN"]:
                crypto_prices = [
                    0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 
                    0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70
                ]
            elif crypto_symbol == "ZEC":
                crypto_prices = [
                    100, 150, 200, 250, 300, 350, 400, 
                    450, 500, 550, 600, 650, 700, 750
                ]
            else:
                # Default for any other cryptocurrency
                crypto_prices = [
                    10, 25, 50, 75, 100, 150, 200, 
                    250, 300, 350, 400, 450, 500, 550
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
            current_btc_price = DEFAULT_BTC_PRICE
            current_difficulty = DEFAULT_NETWORK_DIFFICULTY
            current_block_reward = BLOCK_REWARD
            logging.info(f"Using default values: BTC price=${current_btc_price}, difficulty={current_difficulty/10**12}T, reward={current_block_reward}BTC")
        
        # Get miner specs
        single_hashrate = MINER_DATA[miner_model]["hashrate"]
        single_power_watt = MINER_DATA[miner_model]["power_watt"]
        
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
        
        # Calculate profit for each combination of cryptocurrency price and electricity cost
        for price in crypto_prices:
            for cost in electricity_costs:
                # 计算这个BTC价格和电费成本组合下的利润
                # 特别注意：必须将当前循环的电费成本'cost'传递给函数
                # 为热力图计算添加维护费 - 默认每月5000USD
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
                    maintenance_fee=5000  # 添加默认维护费用
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
                        if price == crypto_prices[0] and cost == electricity_costs[0]:
                            print(f"客户模式热力图 - {crypto_symbol}价格: ${price}, 电费: ${used_electricity_cost}/kWh, 月利润: ${monthly_profit}, {crypto_symbol}产出: {monthly_btc}")
                    else:
                        # === 矿场主模式 ===
                        # 在矿场主模式下，有两种利润模式：
                        # 1. 自营挖矿模式：利润 = 比特币产出收益 - 矿场电费 - 维护费
                        # 2. 托管服务模式：利润 = 客户电费差价收入 = (客户电费 - 矿场电费) * 耗电量
                        
                        maintenance_monthly = result.get('maintenance_fee', {}).get('monthly', 5000)  # 维护费
                        
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
                        if price == crypto_prices[0] and cost == electricity_costs[0]:
                            print(f"矿场主模式热力图 - {crypto_symbol}价格: ${price}, 矿场电费: ${cost}/kWh, 加密货币收入: ${btc_revenue}, 电费成本: ${mining_cost}, 维护: ${maintenance_monthly}, 利润: ${monthly_profit}")
                except Exception as e:
                    # 捕获计算过程中的任何错误
                    logging.error(f"热力图数据点计算错误 - {crypto_symbol}价格: ${price}, 电费: ${cost}/kWh, 错误: {str(e)}")
                    # 使用默认利润以便继续生成图表
                    monthly_profit = 0
                
                profit_data.append({
                    'crypto_price': price,
                    'crypto_symbol': crypto_symbol,
                    'electricity_cost': cost,
                    'monthly_profit': monthly_profit
                })
        
        # Calculate optimal electricity rate at current BTC price
        optimal_electricity_rate = 0
        try:
            # 使用calculate_mining_profitability函数计算盈亏平衡点
            base_result = calculate_mining_profitability(
                hashrate=hashrate,
                power_consumption=power_consumption,
                electricity_cost=0.05,  # Dummy value, not used for this calculation
                btc_price=current_btc_price,  # 仍然使用btc_price参数，因为函数内部使用这个参数名
                difficulty=fixed_network_stats['difficulty'],
                block_reward=fixed_network_stats['block_reward'],
                use_real_time_data=False,
                miner_model=miner_model,
                miner_count=miner_count,
                maintenance_fee=5000,  # 一致添加维护费
                crypto_symbol=crypto_symbol  # 添加加密货币符号
            )
            
            # 检查break_even是否存在以及包含必要字段
            if 'break_even' in base_result and 'electricity_cost' in base_result['break_even']:
                optimal_electricity_rate = base_result['break_even']['electricity_cost']
                
                # 确保break_even中有crypto_price字段
                if 'btc_price' in base_result['break_even'] and 'crypto_price' not in base_result['break_even']:
                    base_result['break_even']['crypto_price'] = base_result['break_even']['btc_price']
        except Exception as e:
            logging.error(f"Error calculating optimal electricity rate: {str(e)}")
            optimal_electricity_rate = 0
        
        return {
            'success': True,
            'profit_data': profit_data,
            'current_network_data': {
                'crypto_symbol': crypto_symbol,
                'crypto_price': current_btc_price,
                'btc_price': current_btc_price,  # 保留向后兼容
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