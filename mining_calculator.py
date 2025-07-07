import numpy as np
import pandas as pd
import requests
import logging
import json
import calendar
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)

# Constants
BLOCKS_PER_DAY = 144
DEFAULT_BTC_PRICE = 80000  # USD
DEFAULT_NETWORK_DIFFICULTY = 119116256505723  # ~119.12T
DEFAULT_NETWORK_HASHRATE = 900  # EH/s
BLOCK_REWARD = 3.125  # BTC

# Fixed miner data including hashrate and power consumption for each model
MINER_DATA = {
    "Antminer S19": {"hashrate": 95, "power_watt": 3250},
    "Antminer S19 Pro": {"hashrate": 110, "power_watt": 3250},
    "Antminer S19 XP": {"hashrate": 140, "power_watt": 3010},
    "Antminer S21": {"hashrate": 200, "power_watt": 3550},
    "Antminer S21 Pro": {"hashrate": 234, "power_watt": 3531},
    "Antminer S21 XP": {"hashrate": 270, "power_watt": 3645},
    "Antminer S21 Hyd": {"hashrate": 335, "power_watt": 5360},
    "Antminer S21 Pro Hyd": {"hashrate": 319, "power_watt": 5445},
    "Antminer S21 XP Hyd": {"hashrate": 473, "power_watt": 5676},
    "WhatsMiner M50": {"hashrate": 114, "power_watt": 3306}
}

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
    """Get the current Bitcoin price from analytics database first, then CoinGecko API"""
    try:
        # 首先尝试从analytics数据库获取最新价格
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
            logging.info(f"使用analytics数据库价格: ${analytics_price:,.2f}")
            return analytics_price
            
    except Exception as e:
        logging.warning(f"Analytics数据库价格获取失败: {e}")
    
    # 如果analytics数据库失败，尝试CoinGecko API
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
    # 使用API密钥获取更准确的难度数据
    headers = {'X-API-Key': '8dd87e048ec84b6c8ad3322fb07f747a'}
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
    """获取实时比特币网络哈希率 - 使用minerstat API作为主要数据源"""
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
                
                logging.info(f"Minerstat算力数据: {hashrate_eh:.2f} EH/s")
                return hashrate_eh
        
        # 方法2：备用 - blockchain.info hashrate API
        hashrate_response = requests.get('https://blockchain.info/q/hashrate', timeout=5)
        if hashrate_response.status_code == 200:
            hashrate_gh = float(hashrate_response.text.strip())
            # 转换GH/s到EH/s
            hashrate_eh = hashrate_gh / 1e9  # GH/s to EH/s
            
            logging.info(f"Blockchain.info备用算力数据: {hashrate_eh:.2f} EH/s")
            return hashrate_eh
        
        # 方法3：基于难度计算（最后备用）
        difficulty_response = requests.get('https://blockchain.info/q/getdifficulty', timeout=5)
        if difficulty_response.status_code == 200:
            difficulty = float(difficulty_response.text.strip())
            # 使用标准公式计算网络算力: hashrate = difficulty * 2^32 / 600
            hashrate_from_difficulty = (difficulty * (2**32)) / 600
            hashrate_eh = hashrate_from_difficulty / 1e18  # 转换为EH/s
            
            logging.info(f"基于难度计算的网络算力: {hashrate_eh:.2f} EH/s")
            return hashrate_eh
            
    except Exception as e:
        logging.error(f"获取网络算力时出错: {e}")
    
    # 最后的fallback
    logging.warning(f"使用默认网络算力: {DEFAULT_NETWORK_HASHRATE} EH/s")
    return DEFAULT_NETWORK_HASHRATE

def calculate_mining_profitability(hashrate=0.0, power_consumption=0.0, electricity_cost=0.05, client_electricity_cost=None, 
                             btc_price=None, difficulty=None, block_reward=None, use_real_time_data=True, miner_model=None, miner_count=1, site_power_mw=None, curtailment=0.0, 
                             shutdown_strategy="efficiency", host_investment=0.0, client_investment=0.0, maintenance_fee=0.0, manual_network_hashrate=None):
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
    - host_investment: Total investment made by mining site owner (USD)
    - client_investment: Total investment made by client (USD)
    - maintenance_fee: Monthly maintenance fee in USD (default is 0)
    
    Returns:
    - Dictionary containing profitability metrics including ROI calculations
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
            logging.info(f"Miner model {miner_model}: single={single_hashrate}TH/s, count={miner_count}, total={hashrate}TH/s")
        
        # Get real-time data if requested
        if use_real_time_data:
            real_time_btc_price = get_real_time_btc_price()
            difficulty_raw = get_real_time_difficulty()
            # Use manual hashrate if provided, otherwise get from API
            if manual_network_hashrate is not None:
                real_time_btc_hashrate = manual_network_hashrate  # EH/s (manual input)
                logging.info(f"使用手动输入的网络算力: {manual_network_hashrate} EH/s")
            else:
                real_time_btc_hashrate = get_real_time_btc_hashrate() or DEFAULT_NETWORK_HASHRATE  # EH/s
            current_block_reward = get_real_time_block_reward()
        else:
            real_time_btc_price = btc_price or DEFAULT_BTC_PRICE
            difficulty_raw = difficulty or DEFAULT_NETWORK_DIFFICULTY
            # Use manual hashrate if provided, otherwise use default
            if manual_network_hashrate is not None:
                real_time_btc_hashrate = manual_network_hashrate  # EH/s (manual input)
                logging.info(f"使用手动输入的网络算力: {manual_network_hashrate} EH/s")
            else:
                real_time_btc_hashrate = DEFAULT_NETWORK_HASHRATE  # EH/s
            current_block_reward = BLOCK_REWARD
        
        # Use provided values if given
        btc_price = btc_price or real_time_btc_price
        difficulty = difficulty_raw
        block_reward_to_use = block_reward or current_block_reward
        
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
            print(f"API哈希率与难度推导哈希率差异过大 (比率: {hashrate_ratio:.2f})，使用加权平均值")
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
        print(f"API Network Hashrate: {real_time_btc_hashrate:.2f} EH/s vs Derived from Difficulty: {network_TH_from_difficulty/1e6:.2f} EH/s")
        
        # 计算单个矿机每日BTC产出
        single_miner_hashrate = None
        if miner_model and miner_model in MINER_DATA:
            single_miner_hashrate = MINER_DATA[miner_model]["hashrate"]
        daily_btc_per_miner = btc_per_th * (single_miner_hashrate if single_miner_hashrate else (hashrate / max(1, miner_count)))
        
        # Method 2: Difficulty Based (算法2：基于难度)
        # 矿场H/s = 矿场TH/s * 1万亿
        site_total_hashrate_Hs = site_total_hashrate * 1e12  # TH/s → H/s
        difficulty_factor = 2 ** 32
        site_daily_btc_output_difficulty = (site_total_hashrate_Hs * block_reward_to_use * 86400) / (difficulty_raw * difficulty_factor)
        site_monthly_btc_output_difficulty = site_daily_btc_output_difficulty * 30.5
        
        # 打印两种算法的结果，方便调试
        print(f"Algorithm 1 (Network Based) - Daily BTC: {site_daily_btc_output:.8f}")
        print(f"Algorithm 2 (Difficulty Based) - Daily BTC: {site_daily_btc_output_difficulty:.8f}")
        
        # 使用难度方法的结果作为最终结果（更准确）
        # 如果两种方法差异过大(>100%)，使用算法2
        algo1_algo2_ratio = site_daily_btc_output / site_daily_btc_output_difficulty if site_daily_btc_output_difficulty > 0 else float('inf')
        
        if algo1_algo2_ratio > 2 or algo1_algo2_ratio < 0.5:
            print(f"警告: 算法1和算法2结果相差过大 (比率: {algo1_algo2_ratio:.2f})，使用算法2(基于难度)的结果")
            daily_btc = site_daily_btc_output_difficulty
            monthly_btc = site_monthly_btc_output_difficulty
        else:
            # 差异在允许范围内，两种方法平均值
            daily_btc = (site_daily_btc_output + site_daily_btc_output_difficulty) / 2
            monthly_btc = (site_monthly_btc_output + site_monthly_btc_output_difficulty) / 2
        
        # === 成本计算 (Cost Calculation) ===
        # Calculate using the operating time after curtailment
        monthly_power_consumption = power_consumption * 24 * 30.5 * curtailment_factor / 1000  # kWh
        electricity_expense = monthly_power_consumption * electricity_cost
        client_electricity_expense = monthly_power_consumption * (client_electricity_cost or electricity_cost)
        
        # === 收入 & 利润计算 (Revenue & Profit Calculation) ===
        monthly_revenue = monthly_btc * btc_price
        
        # 矿场主的比特币挖矿收益，减去电费和维护费
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
        optimal_electricity_rate = (monthly_btc * btc_price) / monthly_power_consumption if monthly_power_consumption > 0 else 0
        
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
            try:
                host_roi_data = calculate_roi(host_investment, yearly_profit, monthly_profit, btc_price)
                logging.info(f"矿场主ROI计算结果 - 年化回报率: {host_roi_data.get('roi_percent_annual', 0)}%, 回收期: {host_roi_data.get('payback_period_months', 'inf')}月")
            except Exception as e:
                logging.error(f"矿场主ROI计算失败: {e}")
                host_roi_data = None
            
        if client_investment > 0:
            try:
                client_roi_data = calculate_roi(client_investment, client_yearly_profit, client_monthly_profit, btc_price)
                logging.info(f"客户ROI计算结果 - 年化回报率: {client_roi_data.get('roi_percent_annual', 0)}%, 回收期: {client_roi_data.get('payback_period_months', 'inf')}月")
            except Exception as e:
                logging.error(f"客户ROI计算失败: {e}")
                client_roi_data = None
            
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
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            # Add regression test expected fields
            'site_daily_btc_output': daily_btc,
            'daily_profit_usd': daily_profit,
            'network_hashrate_eh': real_time_btc_hashrate,
            'btc_price': btc_price,
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
                'shutdown_miner_count': shutdown_miner_count,
                'running_miner_count': running_miner_count
            },
            'roi': {
                'host': host_roi_data,
                'client': client_roi_data
            }
        }
        
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
                        if price == btc_prices[0] and cost == electricity_costs[0]:
                            print(f"客户模式热力图 - BTC价格: ${price}, 电费: ${used_electricity_cost}/kWh, 月利润: ${monthly_profit}, BTC产出: {monthly_btc}")
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
                        if price == btc_prices[0] and cost == electricity_costs[0]:
                            print(f"矿场主模式热力图 - BTC价格: ${price}, 矿场电费: ${cost}/kWh, 比特币收入: ${btc_revenue}, 电费成本: ${mining_cost}, 维护: ${maintenance_monthly}, 利润: ${monthly_profit}")
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
        
        # 使用难度计算算法
        hashrate_h = total_hashrate * 1e12  # 转换为H/s
        difficulty_h = network_difficulty * 1e12  # 转换为H (输入是T)
        difficulty_factor = 2 ** 32
        daily_btc = (hashrate_h * block_reward * 86400) / (difficulty_h * difficulty_factor)
        monthly_btc = daily_btc * days_in_month
        
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
            # 按效率排序（效率低的先关）
            miners_to_keep.sort(key=lambda x: x["efficiency"], reverse=True)
            miners_to_shutdown = miners_to_keep[:miners_to_shutdown_count]
            miners_to_keep = miners_to_keep[miners_to_shutdown_count:]
            
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