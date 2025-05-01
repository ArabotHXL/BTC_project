from flask import Flask, render_template, request, jsonify
import logging
import json
import numpy as np
from mining_calculator import (
    MINER_DATA,
    get_real_time_btc_price,
    get_real_time_difficulty,
    get_real_time_block_reward,
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
        use_real_time = request.form.get('use_real_time', 'false').lower() == 'true'
        miner_model = request.form.get('miner_model')
        miner_count = int(request.form.get('miner_count', 1))
        site_power_mw = float(request.form.get('site_power_mw', 1.0))
        
        # Convert hashrate to TH/s for calculation
        if hashrate_unit == 'PH/s':
            hashrate = hashrate * 1000
        elif hashrate_unit == 'EH/s':
            hashrate = hashrate * 1000000
        
        # For the backend calculation, we calculate based on the miner model and count,
        # or use the manual hashrate if no model is selected
        selected_miner_model = None
        if miner_model and miner_model in MINER_DATA:
            selected_miner_model = miner_model
            
            # Calculate miner count based on site power if we have a valid site power and miner model
            if site_power_mw > 0:
                single_power_watt = MINER_DATA[miner_model]["power_watt"]
                # Formula from original code: site_miner_count = int((input_values['site_power_mw'] * 1000) / (input_values['power_watt'] / 1000))
                calculated_miner_count = int((site_power_mw * 1000) / (single_power_watt / 1000))
                miner_count = calculated_miner_count
                logging.debug(f"Calculated {miner_count} miners for {site_power_mw} MW using {miner_model}")
            
            # We only need to pass the miner model name if we're using it
            # The calculator will handle getting the hashrate and power consumption
            # If we're using a manual entry, we'll pass the values explicitly
            logging.debug(f"Using miner model: {miner_model}, count: {miner_count}")
        
        # Calculate mining profitability
        result = calculate_mining_profitability(
            hashrate=hashrate,
            power_consumption=power_consumption,
            electricity_cost=electricity_cost,
            client_electricity_cost=client_electricity_cost,
            btc_price=btc_price if not use_real_time else None,
            use_real_time_data=use_real_time,
            miner_model=selected_miner_model,
            miner_count=miner_count
        )
        
        # Add additional information to the result for display
        result['inputs']['miner_count'] = miner_count
        result['inputs']['site_power_mw'] = site_power_mw
        
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
        
        return jsonify({
            'success': True,
            'price': price,
            'difficulty': difficulty / 10**12,  # Convert to T for readability
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
        # Get parameters from request
        miner_model = request.form.get('miner_model')
        miner_count = int(request.form.get('miner_count', 1))
        client_electricity_cost = float(request.form.get('client_electricity_cost', 0))
        
        if not miner_model or miner_model not in MINER_DATA:
            return jsonify({
                'success': False,
                'error': 'Please select a valid miner model.'
            }), 400
        
        # Generate price and electricity cost ranges
        current_btc_price = get_real_time_btc_price()
        btc_prices = np.linspace(current_btc_price * 0.8, current_btc_price * 1.2, 10).tolist()
        electricity_costs = np.around(np.linspace(0.02, 0.10, 5), 2).tolist()
        
        # Get profit chart data
        chart_data = generate_profit_chart_data(
            miner_model=miner_model,
            electricity_costs=electricity_costs,
            btc_prices=btc_prices,
            miner_count=miner_count,
            client_electricity_cost=client_electricity_cost if client_electricity_cost > 0 else None
        )
        
        return jsonify(chart_data)
        
    except Exception as e:
        logging.error(f"Error generating profit chart data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while generating chart data.'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)