from flask import Flask, render_template, request, jsonify
import logging
import json
import numpy as np
from mining_calculator import (
    MINER_DATA,
    get_real_time_btc_price,
    get_real_time_difficulty,
    get_real_time_block_reward,
    get_real_time_btc_hashrate,
    calculate_mining_profitability,
    generate_profit_chart_data
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def index():
    """Render the main page of the BTC mining calculator"""
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """Handle the calculation request and return results as JSON"""
    try:
        # Get values from the form submission
        hashrate = float(request.form.get('hashrate', 0))
        hashrate_unit = request.form.get('hashrate_unit', 'TH/s')
        power_consumption = float(request.form.get('power_consumption', 0))
        electricity_cost = float(request.form.get('electricity_cost', 0))
        client_electricity_cost = float(request.form.get('client_electricity_cost', 0))
        btc_price = float(request.form.get('btc_price', 0))
        use_real_time = request.form.get('use_real_time') == 'on'
        miner_model = request.form.get('miner_model')
        miner_count = int(request.form.get('miner_count', 1))
        site_power_mw = float(request.form.get('site_power_mw', 1.0))
        curtailment = float(request.form.get('curtailment', 0))
        
        logging.info(f"Calculate request: model={miner_model}, count={miner_count}, real_time={use_real_time}, "
                     f"site_power={site_power_mw}MW, curtailment={curtailment}%")
        
        # Convert hashrate to TH/s for calculation
        if hashrate_unit == 'PH/s':
            hashrate = hashrate * 1000
        elif hashrate_unit == 'EH/s':
            hashrate = hashrate * 1000000
                
        # Calculate mining profitability using the new function with all parameters
        result = calculate_mining_profitability(
            hashrate=hashrate,
            power_consumption=power_consumption,
            electricity_cost=electricity_cost,
            client_electricity_cost=client_electricity_cost,
            btc_price=btc_price if not use_real_time else None,
            use_real_time_data=use_real_time,
            miner_model=miner_model,
            miner_count=miner_count,
            site_power_mw=site_power_mw,
            curtailment=curtailment
        )
        
        # Return results as JSON
        return jsonify(result)
        
    except ValueError as e:
        logging.error(f"Invalid input: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Please ensure all inputs are valid numbers.'
        }), 400
    except Exception as e:
        logging.error(f"Error calculating profitability: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during calculation. Please try again.'
        }), 500

@app.route('/btc_price', methods=['GET'])
def get_btc_price():
    """Get the current Bitcoin price from API"""
    try:
        current_btc_price = get_real_time_btc_price()
        return jsonify({
            'success': True,
            'price': current_btc_price
        })
    except Exception as e:
        logging.error(f"Error fetching BTC price: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Could not fetch BTC price.'
        }), 500

@app.route('/network_stats', methods=['GET'])
def get_network_stats():
    """Get current Bitcoin network statistics"""
    try:
        price = get_real_time_btc_price()
        difficulty = get_real_time_difficulty()
        block_reward = get_real_time_block_reward()
        hashrate = get_real_time_btc_hashrate()
        
        return jsonify({
            'success': True,
            'price': price,
            'difficulty': difficulty / 10**12,  # Convert to T for readability
            'hashrate': hashrate,  # EH/s
            'block_reward': block_reward
        })
    except Exception as e:
        logging.error(f"Error fetching network stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Could not fetch Bitcoin network statistics.'
        }), 500

@app.route('/miners', methods=['GET'])
def get_miners():
    """Get the list of available miner models and their specifications"""
    try:
        miners_list = []
        for name, specs in MINER_DATA.items():
            miners_list.append({
                'name': name,
                'hashrate': specs['hashrate'],
                'power_watt': specs['power_watt'],
                'efficiency': round(specs['power_watt'] / specs['hashrate'], 2) # W/TH
            })
        
        return jsonify({
            'success': True,
            'miners': miners_list
        })
    except Exception as e:
        logging.error(f"Error fetching miners data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Could not fetch miners data.'
        }), 500

@app.route('/profit_chart_data', methods=['POST'])
def get_profit_chart_data():
    """Generate profit chart data for visualization"""
    try:
        # 添加防重复调用锁，防止前端重复请求同一数据
        import time
        start_time = time.time()
        
        # Get parameters from request
        miner_model = request.form.get('miner_model')
        miner_count = int(request.form.get('miner_count', 1))
        client_electricity_cost = float(request.form.get('client_electricity_cost', 0))
        
        if not miner_model or miner_model not in MINER_DATA:
            return jsonify({
                'success': False,
                'error': 'Please select a valid miner model.'
            }), 400
        
        # 生成缓存键，用于检查是否为重复请求
        cache_key = f"{miner_model}_{miner_count}_{client_electricity_cost}"
        
        # 检查是否有静态缓存数据（简单示例）
        import os
        cache_file = f".chart_cache_{cache_key.replace('.', '_')}.json"
        
        if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
            try:
                with open(cache_file, 'r') as f:
                    import json
                    cached_data = json.load(f)
                    logging.info(f"Using cached chart data for {miner_model} with {miner_count} miners")
                    return jsonify(cached_data)
            except Exception as e:
                logging.error(f"Error reading cache: {str(e)}")
                # 继续执行，重新生成数据
        
        # Generate price and electricity cost ranges
        current_btc_price = get_real_time_btc_price()
        
        # Create a simplified set of price and electricity points (5x5 grid)
        btc_price_factors = [0.5, 0.75, 1.0, 1.25, 1.5]
        btc_prices = [round(current_btc_price * factor) for factor in btc_price_factors]
        electricity_costs = [0.02, 0.04, 0.06, 0.08, 0.10]
        
        logging.info(f"Generating profit chart for {miner_model} with {miner_count} miners")
        logging.info(f"Using BTC prices: {btc_prices}")
        logging.info(f"Using electricity costs: {electricity_costs}")
        
        # Get profit chart data
        chart_data = generate_profit_chart_data(
            miner_model=miner_model,
            electricity_costs=electricity_costs,
            btc_prices=btc_prices,
            miner_count=miner_count,
            client_electricity_cost=client_electricity_cost if client_electricity_cost > 0 else None
        )
        
        # 缓存结果，避免重复计算
        try:
            with open(cache_file, 'w') as f:
                import json
                json.dump(chart_data, f)
        except Exception as e:
            logging.error(f"Error caching chart data: {str(e)}")
        
        elapsed_time = time.time() - start_time
        logging.info(f"Chart data generated in {elapsed_time:.2f} seconds")
        
        return jsonify(chart_data)
        
    except Exception as e:
        logging.error(f"Error generating profit chart data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while generating chart data.'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)