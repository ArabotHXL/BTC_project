import os
import logging
from flask import Flask, render_template, request, jsonify
from mining_calculator import calculate_mining_profitability

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
            btc_price=btc_price
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

# Add endpoint to get current BTC price (in a real app, this would connect to an API)
@app.route('/btc_price', methods=['GET'])
def get_btc_price():
    """
    In a real application, this would fetch the current BTC price from an API.
    For now, we'll return a fixed value.
    """
    try:
        # In a real app, you would fetch this from an API like CoinGecko or Binance
        current_btc_price = 65000  # Sample price in USD
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
