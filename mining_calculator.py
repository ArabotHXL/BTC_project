import pandas as pd
import numpy as np
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

def calculate_mining_profitability(hashrate, power_consumption, electricity_cost, client_electricity_cost=None, btc_price=None, difficulty=None, use_real_time_data=False, miner_model=None, miner_count=1):
    """
    Calculate Bitcoin mining profitability
    
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
    
    Returns:
    - Dictionary containing profitability metrics
    """
    try:
        # Get values from miner model if provided
        if miner_model and miner_model in MINER_DATA:
            # Get single miner specs
            single_hashrate = MINER_DATA[miner_model]["hashrate"]
            single_power_watt = MINER_DATA[miner_model]["power_watt"]
            
            # Apply miner count to get total specs
            hashrate = single_hashrate * miner_count
            power_consumption = single_power_watt * miner_count
            
        # Get real-time data if requested
        if use_real_time_data:
            current_btc_price = get_real_time_btc_price()
            current_difficulty = get_real_time_difficulty()
            current_block_reward = get_real_time_block_reward()
        else:
            current_btc_price = btc_price or DEFAULT_BTC_PRICE
            current_difficulty = difficulty or DEFAULT_NETWORK_DIFFICULTY
            current_block_reward = BLOCK_REWARD
        
        # Use provided values if given
        btc_price = btc_price or current_btc_price
        difficulty = difficulty or current_difficulty
            
        # Convert from TH/s to H/s for calculation
        hashrate_in_h = hashrate * 10**12
        
        # Calculate expected BTC mined per day
        network_hashrate = difficulty * 2**32 / 600  # Estimated network hashrate
        btc_per_day = (hashrate_in_h / network_hashrate) * current_block_reward * BLOCKS_PER_DAY
        
        # No pool fee anymore
        btc_per_day_after_fee = btc_per_day
        
        # Calculate revenue
        daily_revenue_usd = btc_per_day_after_fee * btc_price
        monthly_revenue_usd = daily_revenue_usd * 30
        yearly_revenue_usd = daily_revenue_usd * 365
        
        # Calculate electricity cost
        daily_power_kwh = power_consumption * 24 / 1000  # kWh per day
        daily_electricity_cost = daily_power_kwh * electricity_cost
        monthly_electricity_cost = daily_electricity_cost * 30
        yearly_electricity_cost = daily_electricity_cost * 365
        
        # Calculate mining site profit
        daily_profit_usd = daily_revenue_usd - daily_electricity_cost
        monthly_profit_usd = monthly_revenue_usd - monthly_electricity_cost
        yearly_profit_usd = yearly_revenue_usd - yearly_electricity_cost
        
        # Calculate client profit (if client electricity cost is provided)
        if client_electricity_cost and client_electricity_cost > 0:
            client_daily_electricity_cost = daily_power_kwh * client_electricity_cost
            client_monthly_electricity_cost = client_daily_electricity_cost * 30
            client_yearly_electricity_cost = client_daily_electricity_cost * 365
            
            client_daily_profit_usd = daily_revenue_usd - client_daily_electricity_cost
            client_monthly_profit_usd = monthly_revenue_usd - client_monthly_electricity_cost
            client_yearly_profit_usd = yearly_revenue_usd - client_yearly_electricity_cost
        else:
            # If no client electricity cost provided, use the same as the site
            client_daily_electricity_cost = daily_electricity_cost
            client_monthly_electricity_cost = monthly_electricity_cost
            client_yearly_electricity_cost = yearly_electricity_cost
            
            client_daily_profit_usd = daily_profit_usd
            client_monthly_profit_usd = monthly_profit_usd
            client_yearly_profit_usd = yearly_profit_usd
        
        # Calculate break-even electricity cost
        if btc_per_day_after_fee > 0:
            break_even_electricity = (daily_revenue_usd / daily_power_kwh) if daily_power_kwh > 0 else 0
        else:
            break_even_electricity = 0
            
        # Calculate optimal curtailment (% of power to reduce when electricity is too expensive)
        if electricity_cost > break_even_electricity and break_even_electricity > 0:
            optimal_curtailment = max(0, min(100, 100 * (1 - (break_even_electricity / electricity_cost))))
        else:
            optimal_curtailment = 0
            
        # Return results
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'network_data': {
                'btc_price': btc_price,
                'network_difficulty': difficulty / 10**12,  # Convert to more readable format (T)
                'block_reward': current_block_reward
            },
            'inputs': {
                'hashrate': hashrate,
                'power_consumption': power_consumption,
                'electricity_cost': electricity_cost,
                'client_electricity_cost': client_electricity_cost or electricity_cost
            },
            'btc_mined': {
                'daily': btc_per_day_after_fee,
                'monthly': btc_per_day_after_fee * 30,
                'yearly': btc_per_day_after_fee * 365
            },
            'revenue': {
                'daily': daily_revenue_usd,
                'monthly': monthly_revenue_usd,
                'yearly': yearly_revenue_usd
            },
            'electricity_cost': {
                'daily': daily_electricity_cost,
                'monthly': monthly_electricity_cost,
                'yearly': yearly_electricity_cost
            },
            'profit': {
                'daily': daily_profit_usd,
                'monthly': monthly_profit_usd,
                'yearly': yearly_profit_usd
            },
            'client_profit': {
                'daily': client_daily_profit_usd,
                'monthly': client_monthly_profit_usd,
                'yearly': client_yearly_profit_usd
            },
            'client_electricity_cost': {
                'daily': client_daily_electricity_cost,
                'monthly': client_monthly_electricity_cost,
                'yearly': client_yearly_electricity_cost
            },
            'break_even': {
                'electricity_cost': break_even_electricity
            },
            'optimization': {
                'optimal_curtailment': optimal_curtailment
            }
        }
        
    except Exception as e:
        logging.error(f"Error in calculation: {str(e)}")
        raise

def generate_profit_chart_data(miner_model, electricity_costs, btc_prices, miner_count=1):
    """
    Generate data for the profit chart
    
    Parameters:
    - miner_model: The miner model to use
    - electricity_costs: List of electricity costs to analyze
    - btc_prices: List of BTC prices to analyze
    - miner_count: Number of miners
    
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
                btc_price=btc_price,
                difficulty=current_difficulty,
                use_real_time_data=False
            )
            
            profit_data.append({
                'btc_price': btc_price,
                'electricity_cost': electricity_cost,
                'monthly_profit': result['profit']['monthly']
            })
    
    # Calculate optimal electricity rate at current BTC price
    optimal_result = calculate_mining_profitability(
        hashrate=hashrate,
        power_consumption=power_consumption,
        electricity_cost=0.05,  # Dummy value, not used for this calculation
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