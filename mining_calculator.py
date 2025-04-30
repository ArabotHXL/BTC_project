import logging
from datetime import datetime

# Network difficulty is constantly changing, but for this example
# we'll use a fixed value that can be updated via API in a real implementation
DEFAULT_NETWORK_DIFFICULTY = 79.8 * 10**12  # 79.8T (as of April 2023, for example)
BLOCK_REWARD = 6.25  # Current BTC block reward (halves approximately every 4 years)
BLOCKS_PER_DAY = 144  # 6 blocks per hour * 24 hours

def calculate_mining_profitability(hashrate, power_consumption, electricity_cost, pool_fee, btc_price, difficulty=DEFAULT_NETWORK_DIFFICULTY):
    """
    Calculate Bitcoin mining profitability
    
    Parameters:
    - hashrate: Mining hashrate in TH/s
    - power_consumption: Power consumption in watts
    - electricity_cost: Electricity cost in USD per kWh
    - pool_fee: Mining pool fee in percentage
    - btc_price: Current Bitcoin price in USD
    - difficulty: Network difficulty (default is a fixed value)
    
    Returns:
    - Dictionary containing profitability metrics
    """
    try:
        # Convert from TH/s to H/s for calculation
        hashrate_in_h = hashrate * 10**12
        
        # Calculate expected BTC mined per day
        network_hashrate = difficulty * 2**32 / 600  # Estimated network hashrate
        btc_per_day = (hashrate_in_h / network_hashrate) * BLOCK_REWARD * BLOCKS_PER_DAY
        
        # Apply pool fee
        btc_per_day_after_fee = btc_per_day * (1 - pool_fee / 100)
        
        # Calculate revenue
        daily_revenue_usd = btc_per_day_after_fee * btc_price
        monthly_revenue_usd = daily_revenue_usd * 30
        yearly_revenue_usd = daily_revenue_usd * 365
        
        # Calculate electricity cost
        daily_power_kwh = power_consumption * 24 / 1000  # kWh per day
        daily_electricity_cost = daily_power_kwh * electricity_cost
        monthly_electricity_cost = daily_electricity_cost * 30
        yearly_electricity_cost = daily_electricity_cost * 365
        
        # Calculate profit
        daily_profit_usd = daily_revenue_usd - daily_electricity_cost
        monthly_profit_usd = monthly_revenue_usd - monthly_electricity_cost
        yearly_profit_usd = yearly_revenue_usd - yearly_electricity_cost
        
        # Calculate ROI (assuming zero hardware costs for simplicity)
        # In a real app, you would add hardware costs input
        
        # Calculate break-even electricity cost
        if btc_per_day_after_fee > 0:
            break_even_electricity = (daily_revenue_usd / daily_power_kwh) if daily_power_kwh > 0 else 0
        else:
            break_even_electricity = 0
            
        # Return results
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'inputs': {
                'hashrate': hashrate,
                'power_consumption': power_consumption,
                'electricity_cost': electricity_cost,
                'pool_fee': pool_fee,
                'btc_price': btc_price
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
            'break_even': {
                'electricity_cost': break_even_electricity
            }
        }
        
    except Exception as e:
        logging.error(f"Error in calculation: {str(e)}")
        raise
