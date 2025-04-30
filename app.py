import os
import logging
from flask import Flask, render_template, request, jsonify
from mining_calculator import (
    calculate_mining_profitability, 
    get_real_time_btc_price, 
    get_real_time_difficulty,
    get_real_time_block_reward,
    MINER_DATA
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

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
        pool_fee = float(request.form.get('pool_fee', 0))
        btc_price = float(request.form.get('btc_price', 0))
        use_real_time = request.form.get('use_real_time', 'false').lower() == 'true'
        miner_model = request.form.get('miner_model')
        
        # Convert hashrate to TH/s for calculation
        if hashrate_unit == 'PH/s':
            hashrate = hashrate * 1000
        elif hashrate_unit == 'EH/s':
            hashrate = hashrate * 1000000
        
        # Calculate mining profitability
        result = calculate_mining_profitability(
            hashrate=hashrate,
            power_consumption=power_consumption,
            electricity_cost=electricity_cost,
            pool_fee=pool_fee,
            btc_price=btc_price if not use_real_time else None,
            use_real_time_data=use_real_time,
            miner_model=miner_model if miner_model else None
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
