"""
HashInsight Enterprise - Analytics Routes
分析功能路由
"""

import logging
from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta
from auth import login_required
from analytics.roi_heatmap_generator import ROIHeatmapGenerator

logger = logging.getLogger(__name__)

# 创建蓝图
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@analytics_bp.route('/roi-heatmap', methods=['POST'])
@login_required
def generate_roi_heatmap():
    """生成ROI热力图"""
    try:
        data = request.get_json()
        
        hashrate = float(data.get('hashrate', 110))
        power = int(data.get('power', 3250))
        electricity_cost = float(data.get('electricity_cost', 0.08))
        curtailment_scenario = data.get('curtailment_scenario', 'none')
        
        generator = ROIHeatmapGenerator()
        result = generator.generate_heatmap_data(
            hashrate, power, electricity_cost, curtailment_scenario
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"ROI heatmap generation failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/historical-replay', methods=['POST'])
@login_required
def historical_replay():
    """历史数据回放"""
    try:
        data = request.get_json()
        
        hashrate = float(data.get('hashrate', 110))
        power = int(data.get('power', 3250))
        electricity_cost = float(data.get('electricity_cost', 0.08))
        
        # 解析日期
        start_date = datetime.fromisoformat(data.get('start_date'))
        end_date = datetime.fromisoformat(data.get('end_date'))
        
        generator = ROIHeatmapGenerator()
        result = generator.simulate_historical_replay(
            hashrate, power, electricity_cost, start_date, end_date
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Historical replay failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/curtailment-simulation', methods=['POST'])
@login_required
def curtailment_simulation():
    """限电策略模拟"""
    try:
        data = request.get_json()
        
        miners = data.get('miners', [])
        btc_price = data.get('btc_price')
        difficulty_mult = float(data.get('difficulty_mult', 1.0))
        
        generator = ROIHeatmapGenerator()
        result = generator.generate_multi_miner_comparison(
            miners, btc_price, difficulty_mult
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Curtailment simulation failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
