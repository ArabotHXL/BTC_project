"""
Batch calculator routes for handling multiple miner calculations.
"""
from flask import Blueprint, request, jsonify, render_template, session
from decorators import check_miner_limit, get_user_plan, UpgradeRequired
from mining_calculator import MiningCalculator
import logging

# Create blueprint
batch_calculator_bp = Blueprint('batch_calculator', __name__)

logger = logging.getLogger(__name__)


@batch_calculator_bp.route('/batch-calculator')
def batch_calculator_page():
    """Display the batch calculator interface."""
    try:
        user_id = session.get('user_id')
        user_plan = get_user_plan(user_id)
        
        if not user_plan:
            logger.warning(f"No plan found for user {user_id}")
            # Default to free plan
            from models_subscription import Plan
            user_plan = Plan.query.filter_by(id='free').first()
        
        # Get current language
        current_lang = request.args.get('lang', session.get('language', 'zh'))
        session['language'] = current_lang
        
        return render_template('batch_calculator.html', 
                             user_plan=user_plan,
                             current_lang=current_lang)
    
    except Exception as e:
        logger.error(f"Error loading batch calculator: {e}")
        return "Error loading batch calculator", 500


@batch_calculator_bp.route('/api/batch-calculate', methods=['POST'])
def batch_calculate():
    """Process batch mining calculations."""
    try:
        data = request.get_json()
        
        if not data or 'miners' not in data:
            return jsonify({
                'success': False,
                'error': 'invalid_request',
                'message': 'Invalid request data'
            }), 400
        
        miners = data['miners']
        settings = data.get('settings', {})
        
        # Calculate total miner count
        total_miners = sum(miner.get('quantity', 1) for miner in miners)
        
        # Check quota limits
        allowed, plan, message = check_miner_limit(total_miners)
        
        if not allowed:
            logger.warning(f"Quota exceeded: {total_miners} miners, plan allows {plan.max_miners}")
            return jsonify({
                'success': False,
                'error': 'upgrade_required',
                'message': message,
                'current_plan': plan.name if plan else 'unknown',
                'max_miners': plan.max_miners if plan else 1,
                'attempted_miners': total_miners
            }), 402
        
        # Process calculations
        calculator = MiningCalculator()
        results = []
        summary = {
            'total_miners': total_miners,
            'total_daily_profit': 0,
            'total_daily_revenue': 0,
            'total_daily_cost': 0,
            'average_roi': 0
        }
        
        btc_price = float(settings.get('btc_price', 116000))
        use_realtime = settings.get('use_realtime', True)
        
        # If using real-time data, get current market conditions
        if use_realtime:
            try:
                # Get real-time data from existing calculator
                from coinwarz_api import get_network_data
                network_data = get_network_data()
                if network_data:
                    btc_price = network_data.get('btc_price', btc_price)
                    difficulty = network_data.get('difficulty', 129435235580345)
                    hashrate = network_data.get('hashrate', 707.77)
                else:
                    # Fallback values
                    difficulty = 129435235580345
                    hashrate = 707.77
            except Exception as e:
                logger.warning(f"Failed to get real-time data: {e}")
                difficulty = 129435235580345
                hashrate = 707.77
        else:
            # Use default values
            difficulty = 129435235580345
            hashrate = 707.77
        
        total_roi_sum = 0
        valid_results = 0
        
        for miner in miners:
            try:
                # Calculate for this miner group
                result = calculator.calculate_mining_profitability({
                    'miner_model': miner['model'],
                    'miner_count': miner['quantity'],
                    'electricity_cost': miner['electricity_cost'],
                    'btc_price': btc_price,
                    'site_power_mw': miner['power'] * miner['quantity'] / 1000000,  # Convert W to MW
                    'use_real_time_data': use_realtime
                })
                
                if result and result.get('success', False):
                    miner_result = {
                        'model': miner['model'],
                        'quantity': miner['quantity'],
                        'hashrate': miner.get('hashrate', 0),
                        'power': miner['power'],
                        'electricity_cost': miner['electricity_cost'],
                        'daily_revenue': result.get('daily_revenue', 0),
                        'daily_cost': result.get('daily_cost', 0),
                        'daily_profit': result.get('daily_profit', 0),
                        'monthly_profit': result.get('monthly_profit', 0),
                        'annual_roi': result.get('annual_roi', 0),
                        'payback_days': result.get('payback_days', 0)
                    }
                    
                    results.append(miner_result)
                    
                    # Add to summary
                    summary['total_daily_revenue'] += miner_result['daily_revenue']
                    summary['total_daily_cost'] += miner_result['daily_cost']
                    summary['total_daily_profit'] += miner_result['daily_profit']
                    total_roi_sum += miner_result['annual_roi']
                    valid_results += 1
                    
                else:
                    logger.error(f"Calculation failed for miner {miner['model']}: {result}")
                    # Add failed result
                    results.append({
                        'model': miner['model'],
                        'quantity': miner['quantity'],
                        'error': 'Calculation failed',
                        'daily_profit': 0,
                        'annual_roi': 0
                    })
                    
            except Exception as e:
                logger.error(f"Error calculating for miner {miner.get('model', 'unknown')}: {e}")
                results.append({
                    'model': miner.get('model', 'Unknown'),
                    'quantity': miner.get('quantity', 0),
                    'error': str(e),
                    'daily_profit': 0,
                    'annual_roi': 0
                })
        
        # Calculate average ROI
        if valid_results > 0:
            summary['average_roi'] = total_roi_sum / valid_results
        
        logger.info(f"Batch calculation completed: {len(results)} miners processed")
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': summary,
            'settings': {
                'btc_price': btc_price,
                'use_realtime': use_realtime,
                'difficulty': difficulty if use_realtime else None,
                'hashrate': hashrate if use_realtime else None
            }
        })
        
    except UpgradeRequired as e:
        return jsonify({
            'success': False,
            'error': 'upgrade_required',
            'message': e.message,
            'current_plan': e.current_plan
        }), 402
        
    except Exception as e:
        logger.error(f"Batch calculation error: {e}")
        return jsonify({
            'success': False,
            'error': 'calculation_failed',
            'message': 'Batch calculation failed. Please try again.'
        }), 500


@batch_calculator_bp.route('/api/export/batch-csv', methods=['POST'])
def export_batch_csv():
    """Export batch calculation results to CSV."""
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({
                'success': False,
                'message': 'No results to export'
            }), 400
        
        # Generate CSV content
        csv_lines = ['Model,Quantity,Daily Revenue,Daily Cost,Daily Profit,Monthly Profit,Annual ROI,Payback Days']
        
        for result in results:
            line = ','.join([
                result.get('model', ''),
                str(result.get('quantity', 0)),
                f"{result.get('daily_revenue', 0):.2f}",
                f"{result.get('daily_cost', 0):.2f}",
                f"{result.get('daily_profit', 0):.2f}",
                f"{result.get('monthly_profit', 0):.2f}",
                f"{result.get('annual_roi', 0):.1f}%",
                str(result.get('payback_days', 0))
            ])
            csv_lines.append(line)
        
        csv_content = '\n'.join(csv_lines)
        
        return jsonify({
            'success': True,
            'csv_content': csv_content,
            'filename': f"batch_mining_results_{len(results)}_miners.csv"
        })
        
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        return jsonify({
            'success': False,
            'message': 'Export failed'
        }), 500


@batch_calculator_bp.route('/api/export/batch-excel', methods=['POST'])
def export_batch_excel():
    """Export batch calculation results to Excel (Basic+ plans only)."""
    try:
        user_id = session.get('user_id')
        plan = get_user_plan(user_id)
        
        # Check if user has Excel export permissions
        if not plan or plan.id == 'free':
            return jsonify({
                'success': False,
                'error': 'upgrade_required',
                'message': 'Excel export requires Basic plan or higher'
            }), 402
        
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({
                'success': False,
                'message': 'No results to export'
            }), 400
        
        # For now, return success message
        # TODO: Implement actual Excel generation using openpyxl or xlsxwriter
        
        return jsonify({
            'success': True,
            'message': 'Excel export feature coming soon',
            'filename': f"batch_mining_results_{len(results)}_miners.xlsx"
        })
        
    except Exception as e:
        logger.error(f"Excel export error: {e}")
        return jsonify({
            'success': False,
            'message': 'Export failed'
        }), 500


@batch_calculator_bp.route('/api/export/batch-pdf', methods=['POST'])
def export_batch_pdf():
    """Export batch calculation results to PDF (Pro+ plans only)."""
    try:
        user_id = session.get('user_id')
        plan = get_user_plan(user_id)
        
        # Check if user has PDF export permissions
        if not plan or not plan.allow_advanced_analytics:
            return jsonify({
                'success': False,
                'error': 'upgrade_required',
                'message': 'PDF export requires Pro plan or higher'
            }), 402
        
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({
                'success': False,
                'message': 'No results to export'
            }), 400
        
        # For now, return success message
        # TODO: Implement actual PDF generation using reportlab or weasyprint
        
        return jsonify({
            'success': True,
            'message': 'PDF export feature coming soon',
            'filename': f"batch_mining_report_{len(results)}_miners.pdf"
        })
        
    except Exception as e:
        logger.error(f"PDF export error: {e}")
        return jsonify({
            'success': False,
            'message': 'Export failed'
        }), 500