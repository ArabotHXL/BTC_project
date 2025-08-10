"""
Batch calculator routes for handling multiple miner calculations.
"""
from flask import Blueprint, request, jsonify, render_template, session
from decorators import check_miner_limit, get_user_plan, UpgradeRequired
from mining_calculator import calculate_mining_profitability, MINER_DATA
import logging

# Create blueprint
batch_calculator_bp = Blueprint('batch_calculator', __name__)

logger = logging.getLogger(__name__)


@batch_calculator_bp.route('/batch-calculator')
def batch_calculator():
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
        results = []
        total_daily_profit = 0
        total_daily_revenue = 0
        total_daily_cost = 0
        
        for miner in miners:
            try:
                # Extract miner details
                model = miner.get('model', 'Antminer S19 Pro')
                quantity = int(miner.get('quantity', 1))
                power_consumption = float(miner.get('power_consumption', 3250))
                electricity_cost = float(miner.get('electricity_cost', 0.08))
                
                # Calculate for this miner type
                calc_result = calculate_mining_profitability(
                    miner_type=model,
                    power_consumption=power_consumption,
                    electricity_cost=electricity_cost,
                    quantity=quantity
                )
                
                # Add to results
                result_entry = {
                    'model': model,
                    'quantity': quantity,
                    'power_consumption': power_consumption,
                    'electricity_cost': electricity_cost,
                    'daily_profit': calc_result.get('daily_profit', 0) * quantity,
                    'daily_revenue': calc_result.get('daily_revenue', 0) * quantity,
                    'daily_cost': calc_result.get('daily_cost', 0) * quantity,
                    'monthly_profit': calc_result.get('monthly_profit', 0) * quantity,
                    'roi_days': calc_result.get('roi_days', 0),
                    'hash_rate': calc_result.get('hash_rate', 0)
                }
                
                results.append(result_entry)
                
                # Add to totals
                total_daily_profit += result_entry['daily_profit']
                total_daily_revenue += result_entry['daily_revenue']
                total_daily_cost += result_entry['daily_cost']
                
            except Exception as e:
                logger.error(f"Error calculating for miner {miner}: {e}")
                continue
        
        summary = {
            'total_miners': total_miners,
            'total_daily_profit': total_daily_profit,
            'total_daily_revenue': total_daily_revenue,
            'total_daily_cost': total_daily_cost,
            'total_monthly_profit': total_daily_profit * 30,
            'average_roi_days': sum(r.get('roi_days', 0) for r in results) / len(results) if results else 0
        }
        
        logger.info(f"Batch calculation completed: {len(results)} miners processed")
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': summary,
            'plan_info': {
                'current_plan': plan.name if plan else 'Free',
                'max_miners': plan.max_miners if plan else 1,
                'used_miners': total_miners
            }
        })
        
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