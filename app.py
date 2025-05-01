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
        # Log full form data for debugging
        logging.info(f"Received calculate request form data: {request.form}")
        
        # Get values from the form submission with detailed error handling
        try:
            hashrate = float(request.form.get('hashrate', 0))
        except ValueError as e:
            logging.error(f"Invalid hashrate value: {request.form.get('hashrate')} - {str(e)}")
            hashrate = 0
            
        hashrate_unit = request.form.get('hashrate_unit', 'TH/s')
        
        try:
            power_consumption = float(request.form.get('power_consumption', 0))
        except ValueError as e:
            logging.error(f"Invalid power consumption value: {request.form.get('power_consumption')} - {str(e)}")
            power_consumption = 0
            
        try:
            electricity_cost = float(request.form.get('electricity_cost', 0))
        except ValueError as e:
            logging.error(f"Invalid electricity cost value: {request.form.get('electricity_cost')} - {str(e)}")
            electricity_cost = 0.05  # Default value
            
        try:
            client_electricity_cost = float(request.form.get('client_electricity_cost', 0))
        except ValueError as e:
            logging.error(f"Invalid client electricity cost value: {request.form.get('client_electricity_cost')} - {str(e)}")
            client_electricity_cost = 0
            
        try:
            btc_price = float(request.form.get('btc_price', 0))
        except ValueError as e:
            logging.error(f"Invalid BTC price value: {request.form.get('btc_price')} - {str(e)}")
            btc_price = 0
            
        use_real_time = request.form.get('use_real_time') == 'on'
        miner_model = request.form.get('miner_model')
        
        try:
            miner_count = int(request.form.get('miner_count', 1))
        except ValueError as e:
            logging.error(f"Invalid miner count value: {request.form.get('miner_count')} - {str(e)}")
            miner_count = 1
            
        try:
            site_power_mw = float(request.form.get('site_power_mw', 1.0))
        except ValueError as e:
            logging.error(f"Invalid site power value: {request.form.get('site_power_mw')} - {str(e)}")
            site_power_mw = 1.0
            
        try:
            curtailment = float(request.form.get('curtailment', 0))
        except ValueError as e:
            logging.error(f"Invalid curtailment value: {request.form.get('curtailment')} - {str(e)}")
            curtailment = 0
            
        try:
            maintenance_fee = float(request.form.get('maintenance_fee', 0))
        except ValueError as e:
            logging.error(f"Invalid maintenance fee value: {request.form.get('maintenance_fee')} - {str(e)}")
            maintenance_fee = 0
        
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
        
        # Add maintenance fee to the result
        if maintenance_fee > 0:
            result['maintenance_fee'] = {
                'monthly': maintenance_fee,
                'daily': maintenance_fee / 30.5,
                'yearly': maintenance_fee * 12
            }
        
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
        # 添加详细日志以帮助调试
        import time
        start_time = time.time()
        
        # 记录完整的请求数据
        logging.info(f"Profit chart data request received with data: {request.form}")
        
        # Get parameters from request with detailed error handling
        miner_model = request.form.get('miner_model')
        logging.info(f"Miner model from request: {miner_model}")
        
        # Validate miner model
        if not miner_model:
            logging.error("No miner model provided in request")
            return jsonify({
                'success': False,
                'error': 'Please select a miner model.'
            }), 400
            
        if miner_model not in MINER_DATA:
            logging.error(f"Invalid miner model: {miner_model} not in available models: {list(MINER_DATA.keys())}")
            return jsonify({
                'success': False,
                'error': f"Selected miner model '{miner_model}' is not valid. Please select from available models."
            }), 400
        
        # Parse miner count with error handling
        try:
            miner_count = int(request.form.get('miner_count', 1))
            if miner_count <= 0:
                logging.warning(f"Invalid miner count: {miner_count}, using default of 1")
                miner_count = 1
        except (ValueError, TypeError) as e:
            logging.error(f"Error parsing miner count: {request.form.get('miner_count')} - {str(e)}")
            miner_count = 1
            
        # Parse client electricity cost with error handling
        try:
            client_electricity_cost = float(request.form.get('client_electricity_cost', 0))
        except (ValueError, TypeError) as e:
            logging.error(f"Error parsing client electricity cost: {request.form.get('client_electricity_cost')} - {str(e)}")
            client_electricity_cost = 0
        
        # 禁用缓存以避免使用旧的数据（此前的缓存可能包含错误数据）
        # 生成新的价格和电费成本范围
        try:
            current_btc_price = get_real_time_btc_price()
            logging.info(f"Current BTC price fetched: ${current_btc_price}")
        except Exception as e:
            logging.error(f"Error getting real-time BTC price: {str(e)}, using default")
            current_btc_price = 50000  # 使用默认值
            
        # 创建价格和电费点的网格(5x5)
        btc_price_factors = [0.5, 0.75, 1.0, 1.25, 1.5]
        btc_prices = [round(current_btc_price * factor) for factor in btc_price_factors]
        electricity_costs = [0.02, 0.04, 0.06, 0.08, 0.10]
        
        logging.info(f"Generating profit chart for {miner_model} with {miner_count} miners")
        logging.info(f"Using BTC prices: {btc_prices}")
        logging.info(f"Using electricity costs: {electricity_costs}")
        
        # 获取热力图数据
        try:
            # 尝试生成热力图数据
            chart_data = generate_profit_chart_data(
                miner_model=miner_model,
                electricity_costs=electricity_costs,
                btc_prices=btc_prices,
                miner_count=miner_count,
                client_electricity_cost=client_electricity_cost if client_electricity_cost > 0 else None
            )
            
            # 验证返回的数据结构
            if not chart_data.get('success', False):
                error_msg = chart_data.get('error', 'Unknown error in chart data generation')
                logging.error(f"Chart data generation failed: {error_msg}")
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 400
                
            # 验证profit_data是否为数组且非空
            profit_data = chart_data.get('profit_data', [])
            if not isinstance(profit_data, list) or len(profit_data) == 0:
                logging.error("Generated chart data has empty or invalid profit_data")
                return jsonify({
                    'success': False,
                    'error': 'Generated chart data is invalid (empty profit data)'
                }), 500
                
            # 验证利润值是否有变化
            unique_profits = set(item.get('monthly_profit', 0) for item in profit_data)
            if len(unique_profits) <= 1:
                logging.warning(f"All profit values are identical ({list(unique_profits)[0] if unique_profits else 'N/A'}), data may be incorrect")
                
            elapsed_time = time.time() - start_time
            logging.info(f"Chart data generated in {elapsed_time:.2f} seconds with {len(profit_data)} data points")
            
            return jsonify(chart_data)
            
        except Exception as e:
            logging.error(f"Error generating chart data: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'Error generating chart data: {str(e)}'
            }), 500
    except Exception as e:
        logging.error(f"Unhandled exception in profit chart data generation: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)