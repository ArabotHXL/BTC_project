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
    """Get the current Bitcoin network difficulty"""
    try:
        response = requests.get('https://blockchain.info/q/getdifficulty', timeout=10)
        if response.status_code == 200:
            difficulty = float(response.text.strip())
            return difficulty
        else:
            raise Exception(f"API returned status code {response.status_code}")
    except Exception as e:
        logging.warning(f"Unable to get real-time BTC difficulty: {e}")
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
    """Get the current Bitcoin network hashrate in EH/s"""
    try:
        response = requests.get('https://blockchain.info/q/hashrate', timeout=10)
        if response.status_code == 200:
            hashrate_th = float(response.text.strip())  # Original data is in TH/s
            return hashrate_th / 1e9  # Convert to EH/s
        else:
            raise Exception(f"API returned status code {response.status_code}")
    except Exception as e:
        logging.warning(f"Unable to get real-time BTC hashrate: {e}")
        return DEFAULT_NETWORK_HASHRATE

def calculate_mining_profitability(hashrate=0, power_consumption=0, electricity_cost=0.05, client_electricity_cost=None, 
                             btc_price=None, difficulty=None, use_real_time_data=True, miner_model=None, miner_count=1, site_power_mw=None, curtailment=0):
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
        
        # === PERFORM EXACT CALCULATION FROM ORIGINAL CODE ===
        
        # === 矿机数量 & 总算力计算 (Miner Count & Total Hashrate Calculation) ===
        # Ensure we always have a valid network hashrate (never zero)
        network_TH = max(1e6, real_time_btc_hashrate * 1e6)  # Convert from EH/s to TH/s and ensure minimum value
        curtailment_factor = max(0, min(1, (100 - curtailment) / 100))
        site_total_hashrate = hashrate * curtailment_factor if hashrate is not None else 0
        
        # === BTC 产出计算 (BTC Output Calculation) ===
        # Method 1: Network Hashrate Based
        btc_per_th = (current_block_reward * BLOCKS_PER_DAY) / network_TH
        site_daily_btc_output = site_total_hashrate * btc_per_th
        site_monthly_btc_output = site_daily_btc_output * 30.5
        # Calculate daily BTC per miner - handle both miner model and manual entry cases safely
        single_miner_hashrate = None
        if miner_model and miner_model in MINER_DATA:
            single_miner_hashrate = MINER_DATA[miner_model]["hashrate"]
        daily_btc_per_miner = btc_per_th * (single_miner_hashrate if single_miner_hashrate else (hashrate / max(1, miner_count)))
        
        # Method 2: Difficulty Based
        site_total_hashrate_Hs = site_total_hashrate * 1e12  # TH/s → H/s
        difficulty_factor = 2 ** 32
        site_daily_btc_output_difficulty = (site_total_hashrate_Hs * current_block_reward * 86400) / (difficulty_raw * difficulty_factor)
        site_monthly_btc_output_difficulty = site_daily_btc_output_difficulty * 30.5
        
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
                'block_reward': current_block_reward
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
                'per_th_daily': btc_per_th
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
    if miner_model not in MINER_DATA:
        return {'error': 'Invalid miner model'}
    
    # Get real-time network data once to reuse in all calculations
    current_btc_price = get_real_time_btc_price()
    current_difficulty = get_real_time_difficulty()
    current_block_reward = get_real_time_block_reward()
    
    # Get miner specs
    single_hashrate = MINER_DATA[miner_model]["hashrate"]
    single_power_watt = MINER_DATA[miner_model]["power_watt"]
    
    # Apply miner count
    hashrate = single_hashrate * miner_count
    power_consumption = single_power_watt * miner_count
    
    # Generate profit matrix
    profit_data = []
    
    for btc_price in btc_prices:
        for electricity_cost in electricity_costs:
            # Calculate profit for this combination
            result = calculate_mining_profitability(
                hashrate=hashrate,
                power_consumption=power_consumption,
                electricity_cost=electricity_cost,
                client_electricity_cost=client_electricity_cost,
                btc_price=btc_price,
                difficulty=current_difficulty,
                use_real_time_data=False
            )
            
            # Use client profit if available, otherwise use regular profit
            monthly_profit = result['client_profit']['monthly'] if client_electricity_cost and 'client_profit' in result else result['profit']['monthly']
            
            profit_data.append({
                'btc_price': btc_price,
                'electricity_cost': electricity_cost,
                'monthly_profit': monthly_profit
            })
    
    # Calculate optimal electricity rate at current BTC price
    optimal_result = calculate_mining_profitability(
        hashrate=hashrate,
        power_consumption=power_consumption,
        electricity_cost=0.05,  # Dummy value, not used for this calculation
        client_electricity_cost=client_electricity_cost,
        btc_price=current_btc_price,
        difficulty=current_difficulty,
        use_real_time_data=False
    )
    
    optimal_electricity_rate = optimal_result['break_even']['electricity_cost']
    
    return {
        'success': True,
        'profit_data': profit_data,
        'current_network_data': {
            'btc_price': current_btc_price,
            'difficulty': current_difficulty / 10**12,  # Convert to more readable format (T)
            'block_reward': current_block_reward
        },
        'optimal_electricity_rate': optimal_electricity_rate
    }