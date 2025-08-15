"""
Batch calculator routes for handling multiple miner calculations.
"""
from flask import Blueprint, request, jsonify, render_template, session, render_template_string, send_file, make_response
from decorators import check_miner_limit, get_user_plan, UpgradeRequired, require_feature
from mining_calculator import calculate_mining_profitability, MINER_DATA
from optimized_batch_processor import batch_processor
import logging
import io
import os
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
import xlsxwriter

# Create blueprint
batch_calculator_bp = Blueprint('batch_calculator', __name__)

logger = logging.getLogger(__name__)


@batch_calculator_bp.route('/batch-calculator')
@require_feature('batch_calculator')
def batch_calculator():
    """Display the batch calculator interface."""
    try:
        user_id = session.get('user_id')
        user_plan_raw = get_user_plan(user_id)
        
        # Use the actual user plan from database
        user_plan = user_plan_raw
        
        # Only create default plan if we don't have a valid plan object
        if not user_plan or not hasattr(user_plan, 'name'):
            class DefaultPlan:
                id = 'free'
                name = 'Free'
                max_miners = 1
                price = 0
                allow_advanced_analytics = False
                allow_api = False
                allow_scenarios = False
            user_plan = DefaultPlan()
        
        # Get current language
        current_lang = request.args.get('lang', session.get('language', 'zh'))
        session['language'] = current_lang
        
        plan_name = getattr(user_plan, 'name', user_plan) if user_plan else 'Free'
        logger.info(f"Rendering batch calculator with plan: {plan_name}, language: {current_lang}")
        
        # Pass session data to template
        template_data = {
            'user_plan': user_plan,
            'current_lang': current_lang,
            'session': session
        }
        
        return render_template('batch_calculator.html', **template_data)
    
    except Exception as e:
        logger.error(f"Error loading batch calculator: {e}", exc_info=True)
        # Return a working basic page
        return render_template_string('''
<!DOCTYPE html>
<html lang="zh-CN" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>批量挖矿计算器</title>
    <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark border-bottom">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">
                <i class="bi bi-calculator me-2"></i>BTC挖矿计算器
            </a>
            <div class="d-flex gap-2">
                <a href="/" class="btn btn-outline-light btn-sm">
                    <i class="bi bi-arrow-left me-1"></i>返回计算器
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row mb-4">
            <div class="col-12">
                <h2 class="mb-1">批量挖矿计算器</h2>
                <p class="text-muted mb-0">一次性计算多台矿机的收益率</p>
                
                <div class="alert alert-info mt-3">
                    <i class="bi bi-info-circle me-2"></i>
                    <strong>系统维护中</strong>
                    <p class="mb-0">批量计算器正在升级优化，请稍后再试。您可以先使用主页的单台矿机计算功能。</p>
                </div>
                
                <div class="text-center mt-4">
                    <a href="/" class="btn btn-primary">返回主计算器</a>
                    <a href="/billing/plans" class="btn btn-outline-secondary ms-2">查看订阅计划</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
        ''')


@batch_calculator_bp.route('/api/batch-calculate', methods=['POST'])
def batch_calculate():
    """Process batch mining calculations with optimized performance for large datasets."""
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
        
        # Enhanced memory management for large datasets
        if total_miners > 1000:
            logger.info(f"Processing large batch: {total_miners} miners - Using optimized processor")
            
            # 使用优化处理器处理大批量数据
            result = batch_processor.process_large_batch(miners, use_real_time_data=True)
            if result['success']:
                logger.info(f"优化处理器成功处理: {result['summary']['total_miners']} 矿机")
                return jsonify(result)
            else:
                logger.error(f"优化处理器失败: {result.get('error', 'Unknown error')}")
                # 如果优化处理器失败，继续使用标准处理
            
        # Check quota limits
        allowed = check_miner_limit(total_miners)
        
        if not allowed:
            logger.warning(f"Quota exceeded: {total_miners} miners")
            return jsonify({
                'success': False,
                'error': 'upgrade_required',
                'message': 'Quota exceeded. Please upgrade your plan.',
                'current_plan': 'Free',
                'max_miners': 1,
                'attempted_miners': total_miners
            }), 402
        
        # Optimized batch processing
        results = []
        total_daily_profit = 0
        total_daily_revenue = 0
        total_daily_cost = 0
        batch_size = 100  # Process in chunks to manage memory
        
        # Group identical miners to optimize calculations
        miner_groups = {}
        for miner in miners:
            key = (
                miner.get('model', 'Antminer S19 Pro'),
                float(miner.get('power_consumption', 3250)),
                float(miner.get('electricity_cost', 0.08))
            )
            if key not in miner_groups:
                miner_groups[key] = 0
            miner_groups[key] += int(miner.get('quantity', 1))
        
        logger.info(f"Optimized {len(miners)} entries into {len(miner_groups)} unique groups")
        
        # Calculate once per unique group
        for (model, power_consumption, electricity_cost), quantity in miner_groups.items():
            try:
                # Single calculation for the entire group with batch optimization
                calc_result = calculate_mining_profitability(
                    power_consumption=power_consumption,
                    electricity_cost=electricity_cost,
                    miner_model=model,
                    miner_count=quantity,
                    _batch_mode=True  # Enable batch optimization
                )
                
                result_entry = {
                    'model': model,
                    'quantity': quantity,
                    'power_consumption': power_consumption,
                    'electricity_cost': electricity_cost,
                    'daily_profit': calc_result.get('daily_profit', 0),
                    'daily_revenue': calc_result.get('daily_revenue', 0),
                    'daily_cost': calc_result.get('daily_cost', 0),
                    'monthly_profit': calc_result.get('monthly_profit', 0),
                    'roi_days': calc_result.get('roi_days', 0),
                    'hash_rate': calc_result.get('hash_rate', 0)
                }
                
                results.append(result_entry)
                
                # Add to totals
                total_daily_profit += result_entry['daily_profit']
                total_daily_revenue += result_entry['daily_revenue']
                total_daily_cost += result_entry['daily_cost']
                
            except Exception as e:
                logger.error(f"Error calculating for miner group {model}: {e}")
                continue
        
        # Create summary with reduced precision to save memory
        summary = {
            'total_miners': total_miners,
            'total_daily_profit': round(total_daily_profit, 2),
            'total_daily_revenue': round(total_daily_revenue, 2),
            'total_daily_cost': round(total_daily_cost, 2),
            'total_monthly_profit': round(total_daily_profit * 30, 2),
            'unique_groups': len(results),
            'average_roi_days': round(sum(r.get('roi_days', 0) for r in results) / len(results), 1) if results else 0
        }
        
        logger.info(f"Optimized batch calculation completed: {len(results)} unique groups, {total_miners} total miners")
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': summary,
            'optimization_info': {
                'original_entries': len(miners),
                'optimized_groups': len(results),
                'total_miners': total_miners,
                'memory_optimized': total_miners > 1000
            }
        })
        
    except UpgradeRequired as e:
        return jsonify({
            'success': False,
            'error': 'upgrade_required',
            'message': str(e),
            'current_plan': 'Free'
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
        
        # Generate CSV content with 3 decimal places precision
        csv_lines = ['Model,Quantity,Daily Revenue,Daily Cost,Daily Profit,Monthly Profit,ROI Days,Hash Rate (TH/s),Power (W),Machine Price,Total Cost,Daily BTC,Monthly BTC']
        
        for result in results:
            line = ','.join([
                f'"{result.get("model", "")}"',
                str(result.get('quantity', 0)),
                f"{result.get('daily_revenue', 0):.2f}",
                f"{result.get('daily_cost', 0):.2f}",
                f"{result.get('daily_profit', 0):.2f}",
                f"{result.get('monthly_profit', 0):.2f}",
                str(result.get('roi_days', 0)),
                f"{result.get('hash_rate', 0):.0f}",
                f"{result.get('power_consumption', 0):.0f}",
                f"{result.get('machine_price', 0):.2f}",
                f"{result.get('total_machine_cost', 0):.2f}",
                f"{result.get('daily_btc', 0):.8f}",
                f"{result.get('monthly_btc', 0):.8f}"
            ])
            csv_lines.append(line)
        
        csv_content = '\n'.join(csv_lines)
        
        # Return CSV file as download
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename="batch_mining_results_{len(results)}_miners.csv"'
        return response
        
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
        if not plan or plan == 'free':
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
        
        # Generate Excel file using openpyxl
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        if worksheet is not None:
            worksheet.title = "Mining Results"
        
        # Define styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Headers with 3 decimal places precision
        headers = [
            'Miner Model', 'Quantity', 'Daily Revenue (USD)', 'Daily Cost (USD)', 
            'Daily Profit (USD)', 'Monthly Profit (USD)', 'Annual ROI (%)', 
            'Payback Days', 'Hash Rate (TH/s)', 'Power (W)', 
            'Daily BTC', 'Monthly BTC'
        ]
        
        # Set headers
        if worksheet is not None:
            for col, header in enumerate(headers, 1):
                cell = worksheet.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = border
        
        # Add data rows with 3 decimal places
        if worksheet is not None:
            for row, result in enumerate(results, 2):
                data_row = [
                    result.get('model', ''),
                    result.get('quantity', 0),
                    round(result.get('daily_revenue', 0), 3),
                    round(result.get('daily_cost', 0), 3),
                    round(result.get('daily_profit', 0), 3),
                    round(result.get('monthly_profit', 0), 3),
                    round(result.get('annual_roi', 0), 3),
                    round(result.get('payback_days', 0), 3),
                    round(result.get('hashrate', 0), 3),
                    round(result.get('power', 0), 3),
                    round(result.get('daily_btc', 0), 8),
                    round(result.get('monthly_btc', 0), 8)
                ]
                
                for col, value in enumerate(data_row, 1):
                    cell = worksheet.cell(row=row, column=col, value=value)
                    cell.border = border
                    if isinstance(value, (int, float)) and col > 2:
                        cell.number_format = '0.000'  # 3 decimal places
        
        # Auto-adjust column widths
        if worksheet is not None:
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 20)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Save to BytesIO
        excel_buffer = io.BytesIO()
        workbook.save(excel_buffer)
        excel_buffer.seek(0)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"batch_mining_results_{len(results)}_miners_{timestamp}.xlsx"
        
        return send_file(
            excel_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
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
        if not plan or plan == 'free':
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


@batch_calculator_bp.route('/api/batch-calculate-optimized', methods=['POST'])
def batch_calculate_optimized():
    """优化的批量计算接口，专门处理大量数据 (5000+ miners)"""
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
        
        # 计算总矿机数量
        total_miners = sum(miner.get('quantity', 1) for miner in miners)
        
        logger.info(f"优化批量计算: {len(miners)} 条目, {total_miners} 矿机")
        
        # 检查权限
        allowed = check_miner_limit(total_miners)
        if not allowed:
            return jsonify({
                'success': False,
                'error': 'upgrade_required',
                'message': f'您的计划不支持 {total_miners} 台矿机。Pro 计划支持无限制批量计算。'
            }), 402
        
        # 使用优化处理器
        result = batch_processor.process_large_batch(
            miners, 
            use_real_time_data=settings.get('use_real_time_data', True)
        )
        
        if result['success']:
            logger.info(f"优化计算完成: {result['summary']['total_miners']} 矿机, 日收益 ${result['summary']['total_daily_profit']:,.2f}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"优化批量计算错误: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'calculation_failed',
            'message': '优化批量计算失败，请重试'
        }), 500