import numpy as np
import pandas as pd
import requests
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)

# Constants
BLOCKS_PER_DAY = 144
DEFAULT_BTC_PRICE = 80000  # USD
DEFAULT_NETWORK_DIFFICULTY = 56000000000000  # ~56T
DEFAULT_NETWORK_HASHRATE = 700  # EH/s
BLOCK_REWARD = 3.125  # BTC

# Fixed miner data including hashrate and power consumption for each model
MINER_DATA = {
    "Antminer S21 XP Hyd": {"hashrate": 473, "power_watt": 5676},
    "Antminer S21 XP": {"hashrate": 270, "power_watt": 3645},
    "Antminer S21": {"hashrate": 200, "power_watt": 3500},
    "Antminer S21 Hyd": {"hashrate": 335, "power_watt": 5360},
    "Antminer S19": {"hashrate": 95, "power_watt": 3250},
    "Antminer S19 Pro": {"hashrate": 110, "power_watt": 3250},
    "Antminer S19j Pro": {"hashrate": 100, "power_watt": 3050},
    "Antminer S19 XP": {"hashrate": 140, "power_watt": 3010},
    "Antminer S19 Hydro": {"hashrate": 158, "power_watt": 5451},
    "Antminer S19 Pro+ Hyd": {"hashrate": 198, "power_watt": 5445}
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
    """获取实时比特币网络哈希率，带有多个备用API选项"""
    apis = [
        'https://blockchain.info/q/hashrate',  # 返回TH/s
        'https://api.blockchain.info/stats',   # 返回包含hashrate的JSON (Hash/s)
        'https://mempool.space/api/v1/mining/hashrate/3d'  # 备用API - 3天平均哈希率
    ]
    
    for api_url in apis:
        try:
            response = requests.get(api_url, timeout=5)
            
            if response.status_code == 200:
                if 'stats' in api_url:  # 处理blockchain.info/stats JSON响应
                    data = response.json()
                    if 'hash_rate' in data:
                        # 该API返回的是每秒哈希数 (Hash/s)，需要转换为EH/s
                        hashrate_h = float(data['hash_rate'])
                        return hashrate_h / 1e18  # 转换为 EH/s
                elif 'mempool.space' in api_url:  # 处理mempool.space API响应
                    data = response.json()
                    # mempool返回的是每秒平均哈希数 (Hash/s)，需要计算平均值并转换为EH/s
                    if isinstance(data, list) and len(data) > 0:
                        # 计算最近数据的平均值
                        avg_hashrate = sum(entry['hashrate'] for entry in data) / len(data)
                        return avg_hashrate / 1e18  # 转换为 EH/s
                else:  # 处理blockchain.info/q/hashrate的纯文本响应
                    hashrate_th = float(response.text.strip())  # 该API返回的是TH/s
                    return hashrate_th / 1e3  # 转换为 EH/s (1000 TH/s = 1 EH/s)
            else:
                logging.warning(f"API {api_url} 返回状态码 {response.status_code}")
                # 继续尝试下一个API
                
        except Exception as e:
            logging.warning(f"尝试从 {api_url} 获取网络哈希率时出错: {e}")
            # 继续尝试下一个API
    
    # 所有API都失败时，使用默认值
    logging.warning(f"无法从任何API获取实时BTC网络哈希率，使用默认值 {DEFAULT_NETWORK_HASHRATE} EH/s")
    return DEFAULT_NETWORK_HASHRATE

def calculate_mining_profitability(hashrate=0.0, power_consumption=0.0, electricity_cost=0.05, client_electricity_cost=None, 
                             btc_price=None, difficulty=None, block_reward=None, use_real_time_data=True, miner_model=None, miner_count=1, site_power_mw=None, curtailment=0.0):
    """
    Calculate Bitcoin mining profitability using the exact calculation method from the original code
    
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
    
    Returns:
    - Dictionary containing profitability metrics
    """
    try:
        # Get values from miner model if provided
        if miner_model and miner_model in MINER_DATA:
            # Get single miner specs
            single_hashrate = MINER_DATA[miner_model]["hashrate"]
            single_power_watt = MINER_DATA[miner_model]["power_watt"]
            
            # Calculate miner count from site power if provided
            if site_power_mw and site_power_mw > 0:
                # Formula from original code: site_miner_count = int((site_power_mw * 1000) / (power_watt / 1000))
                miner_count = int((site_power_mw * 1000) / (single_power_watt / 1000))
                logging.info(f"Calculated {miner_count} miners for {site_power_mw} MW using {miner_model}")
            
            # Apply miner count to get total specs
            hashrate = single_hashrate * miner_count
            power_consumption = single_power_watt * miner_count
        
        # Get real-time data if requested
        if use_real_time_data:
            real_time_btc_price = get_real_time_btc_price()
            difficulty_raw = get_real_time_difficulty()
            real_time_btc_hashrate = get_real_time_btc_hashrate() or DEFAULT_NETWORK_HASHRATE  # EH/s
            current_block_reward = get_real_time_block_reward()
        else:
            real_time_btc_price = btc_price or DEFAULT_BTC_PRICE
            difficulty_raw = difficulty or DEFAULT_NETWORK_DIFFICULTY
            real_time_btc_hashrate = DEFAULT_NETWORK_HASHRATE  # EH/s
            current_block_reward = BLOCK_REWARD
        
        # Use provided values if given
        btc_price = btc_price or real_time_btc_price
        difficulty = difficulty_raw
        block_reward_to_use = block_reward or current_block_reward
        
        # === PERFORM EXACT CALCULATION FROM ORIGINAL CODE ===
        
        # === 矿机数量 & 总算力计算 (Miner Count & Total Hashrate Calculation) ===
        # Ensure we always have a valid network hashrate (never zero)
        network_TH = max(1e6, real_time_btc_hashrate * 1e6)  # Convert from EH/s to TH/s and ensure minimum value
        curtailment_factor = max(0, min(1, (100 - curtailment) / 100))
        site_total_hashrate = hashrate * curtailment_factor if hashrate is not None else 0
        
        # === BTC 产出计算 (BTC Output Calculation) ===
        # Method 1: Network Hashrate Based
        btc_per_th = (block_reward_to_use * BLOCKS_PER_DAY) / network_TH
        site_daily_btc_output = site_total_hashrate * btc_per_th
        site_monthly_btc_output = site_daily_btc_output * 30.5
        # Calculate daily BTC per miner - handle both miner model and manual entry cases safely
        single_miner_hashrate = None
        if miner_model and miner_model in MINER_DATA:
            single_miner_hashrate = MINER_DATA[miner_model]["hashrate"]
        daily_btc_per_miner = btc_per_th * (single_miner_hashrate if single_miner_hashrate else (hashrate / max(1, miner_count)))
        
        # Method 2: Difficulty Based (从原始代码中完全复制的算法)
        site_total_hashrate_Hs = site_total_hashrate * 1e12  # TH/s → H/s
        difficulty_factor = 2 ** 32
        # 确保使用正确的时间计算（86400秒/天）
        site_daily_btc_output_difficulty = (site_total_hashrate_Hs * block_reward_to_use * 86400) / (difficulty_raw * difficulty_factor)
        site_monthly_btc_output_difficulty = site_daily_btc_output_difficulty * 30.5
        
        # 打印两种算法的结果，方便调试
        print(f"Algorithm 1 (Network Based) - Daily BTC: {site_daily_btc_output:.8f}")
        print(f"Algorithm 2 (Difficulty Based) - Daily BTC: {site_daily_btc_output_difficulty:.8f}")
        
        # Take the average of both methods or use the difficulty method if network hashrate is missing
        daily_btc = site_daily_btc_output if real_time_btc_hashrate else site_daily_btc_output_difficulty
        monthly_btc = site_monthly_btc_output if real_time_btc_hashrate else site_monthly_btc_output_difficulty
        
        # === 成本计算 (Cost Calculation) ===
        # Calculate using the operating time after curtailment
        monthly_power_consumption = power_consumption * 24 * 30.5 * curtailment_factor / 1000  # kWh
        electricity_expense = monthly_power_consumption * electricity_cost
        client_electricity_expense = monthly_power_consumption * (client_electricity_cost or electricity_cost)
        
        # === 收入 & 利润计算 (Revenue & Profit Calculation) ===
        monthly_revenue = monthly_btc * btc_price
        monthly_profit = monthly_revenue - electricity_expense
        client_monthly_profit = monthly_revenue - client_electricity_expense
        
        # === 最优电价 (Optimal Electricity Rate) 计算 ===
        optimal_electricity_rate = (monthly_btc * btc_price) / monthly_power_consumption if monthly_power_consumption > 0 else 0
        
        # === 最优削减比例 (Optimal Curtailment) 计算 ===
        if electricity_cost > optimal_electricity_rate and optimal_electricity_rate > 0:
            optimal_curtailment = max(0, min(100, 100 * (1 - (optimal_electricity_rate / electricity_cost))))
        else:
            optimal_curtailment = 0
        
        # Scale back to get daily values
        daily_revenue = monthly_revenue / 30.5
        daily_profit = monthly_profit / 30.5
        daily_electricity_expense = electricity_expense / 30.5
        client_daily_profit = client_monthly_profit / 30.5
        client_daily_electricity_expense = client_electricity_expense / 30.5
        
        # Scale to get yearly values
        yearly_revenue = monthly_revenue * 12
        yearly_profit = monthly_profit * 12
        yearly_electricity_expense = electricity_expense * 12
        client_yearly_profit = client_monthly_profit * 12
        client_yearly_electricity_expense = client_electricity_expense * 12
            
        # Return results in a consistent format with our previous implementation
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
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
                'curtailment': curtailment
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
                'shutdown_miner_count': int(miner_count * (curtailment / 100))
            }
        }
        
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
        
        # Calculate profit for each combination of BTC price and electricity cost
        for price in btc_prices:
            for cost in electricity_costs:
                # 计算这个BTC价格和电费成本组合下的利润
                # 特别注意：必须将当前循环的电费成本'cost'传递给函数
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
                    miner_count=miner_count
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
                            print(f"客户模式热力图 - BTC价格: ${price}, 电费: ${used_electricity_cost}/kWh, 月利润: ${monthly_profit}, BTC产出: {monthly_btc}")
                    else:
                        # === 矿场主模式 ===
                        # 在矿场主模式下，我们展示不同电费和BTC价格组合下的矿场利润
                        
                        # 1. 矿场收入 - 基于客户电费收入
                        host_monthly_revenue = monthly_power * cost  # 收入：电力消耗 * 当前循环中的电费（表示矿场收取的费用）
                        
                        # 2. 矿场成本 - 基于矿场实际电费 + 维护费
                        # 使用基本电费(通常是 0.05 $/kWh)作为矿场的实际电费成本
                        base_electricity_cost = 0.05  # 基础矿场电费
                        host_monthly_cost = monthly_power * base_electricity_cost  # 电力成本
                        maintenance_monthly = result.get('maintenance_fee', {}).get('monthly', 5000)  # 维护费
                        
                        # 3. 计算矿场利润
                        monthly_profit = host_monthly_revenue - host_monthly_cost - maintenance_monthly
                        
                        # 记录日志帮助调试（仅在第一个点记录）
                        if price == btc_prices[0] and cost == electricity_costs[0]:
                            print(f"矿场主模式热力图 - BTC价格: ${price}, 矿场电费: ${cost}/kWh, 收入: ${host_monthly_revenue}, 成本: ${host_monthly_cost}, 维护: ${maintenance_monthly}, 利润: ${monthly_profit}")
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
                miner_count=miner_count
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