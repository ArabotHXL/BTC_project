"""
Intelligence Layer - Explanation API
=====================================

Flask blueprint for ROI explanation and recommendation endpoints.

Endpoints:
- GET /api/intelligence/explain/roi/<user_id> - Get ROI explanation
- GET /api/intelligence/explain/roi/<user_id>/change - Get ROI change analysis
- GET /api/intelligence/explain/roi/<user_id>/recommendations - Get recommendations
"""

import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError

from models import UserAccess
from api_auth_middleware import require_api_auth
from intelligence.explain import calculate_roi_factors
from common.rbac import require_permission, Permission

logger = logging.getLogger(__name__)

explain_bp = Blueprint('explain_api', __name__, url_prefix='/api/intelligence/explain')


@explain_bp.route('/roi/<int:user_id>', methods=['GET'])
@require_api_auth(required_permissions=['read'], allow_session_auth=True)
@require_permission([Permission.INTEL_READ, Permission.INTEL_EXPLAIN], require_all=True)
def get_roi_explanation(user_id):
    """
    Get ROI explanation with factor breakdown
    
    Returns detailed analysis of what factors affect the user's mining profitability
    
    Returns:
        JSON with ROI factor breakdown including:
        - Current ROI metrics
        - Factor impacts (BTC price, difficulty, offline rate, electricity)
        - Factor contributions as percentages
    """
    try:
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': f'User {user_id} not found'
            }), 404
        
        logger.info(f"Calculating ROI explanation for user {user_id}")
        
        roi_factors = calculate_roi_factors(user_id)
        
        if not roi_factors:
            return jsonify({
                'status': 'error',
                'message': 'Unable to calculate ROI factors. Check user mining data.'
            }), 500
        
        logger.info(f"ROI explanation calculated for user {user_id}. Current ROI: {roi_factors['current_metrics']['annual_roi_percent']:.2f}%")
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'roi_analysis': roi_factors,
            'generated_at': roi_factors.get('generated_at')
        }), 200
        
    except SQLAlchemyError as e:
        logger.error(f"Database error calculating ROI for user {user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred',
            'error': str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Error calculating ROI for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500


@explain_bp.route('/roi/<int:user_id>/change', methods=['GET'])
@require_api_auth(required_permissions=['read'], allow_session_auth=True)
@require_permission([Permission.INTEL_READ, Permission.INTEL_EXPLAIN], require_all=True)
def get_roi_change_analysis(user_id):
    """
    Get ROI change analysis
    
    Query Parameters:
    - scenario: Scenario to analyze (price_up, price_down, difficulty_up, difficulty_down, etc.)
    - magnitude: Change magnitude as decimal (default: 0.1 for 10%)
    
    Returns:
        JSON with ROI change impact analysis
    """
    try:
        scenario = request.args.get('scenario', 'price_up')
        magnitude = request.args.get('magnitude', 0.1, type=float)
        
        if magnitude <= 0 or magnitude > 1.0:
            return jsonify({
                'status': 'error',
                'message': 'Magnitude must be between 0 and 1.0'
            }), 400
        
        valid_scenarios = ['price_up', 'price_down', 'difficulty_up', 'difficulty_down', 
                          'offline_increase', 'electricity_up', 'electricity_down']
        
        if scenario not in valid_scenarios:
            return jsonify({
                'status': 'error',
                'message': f'Invalid scenario. Must be one of: {", ".join(valid_scenarios)}'
            }), 400
        
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': f'User {user_id} not found'
            }), 404
        
        logger.info(f"Calculating ROI change analysis for user {user_id}, scenario: {scenario}, magnitude: {magnitude}")
        
        roi_factors = calculate_roi_factors(user_id)
        
        if not roi_factors:
            return jsonify({
                'status': 'error',
                'message': 'Unable to calculate ROI factors'
            }), 500
        
        current_roi = roi_factors['current_metrics']['annual_roi_percent']
        
        scenario_map = {
            'price_up': roi_factors['factor_impacts']['btc_price']['impact_per_10pct_change'],
            'price_down': -roi_factors['factor_impacts']['btc_price']['impact_per_10pct_change'],
            'difficulty_up': -roi_factors['factor_impacts']['difficulty']['impact_per_10pct_change'],
            'difficulty_down': roi_factors['factor_impacts']['difficulty']['impact_per_10pct_change'],
            'offline_increase': -roi_factors['factor_impacts']['offline_rate']['impact_per_5pct_offline'],
            'electricity_up': -roi_factors['factor_impacts']['electricity_cost']['impact_per_10pct_change'],
            'electricity_down': roi_factors['factor_impacts']['electricity_cost']['impact_per_10pct_change']
        }
        
        impact = scenario_map.get(scenario, 0)
        new_roi = current_roi + (impact * magnitude / 0.1)
        roi_change = new_roi - current_roi
        roi_change_percent = (roi_change / current_roi * 100) if current_roi != 0 else 0
        
        logger.info(f"ROI change analysis for user {user_id}: {scenario} -> ROI change: {roi_change:.2f}%")
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'scenario': scenario,
            'magnitude': magnitude,
            'analysis': {
                'current_roi': current_roi,
                'projected_roi': new_roi,
                'roi_change': roi_change,
                'roi_change_percent': roi_change_percent,
                'impact_description': f"{scenario.replace('_', ' ').title()} by {magnitude*100:.0f}%"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in ROI change analysis for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500


@explain_bp.route('/roi/<int:user_id>/recommendations', methods=['GET'])
@require_api_auth(required_permissions=['read'], allow_session_auth=True)
@require_permission([Permission.INTEL_READ, Permission.INTEL_EXPLAIN], require_all=True)
def get_recommendations(user_id):
    """
    Get ROI improvement recommendations
    
    Returns:
        JSON with actionable recommendations to improve ROI
    """
    try:
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': f'User {user_id} not found'
            }), 404
        
        logger.info(f"Generating recommendations for user {user_id}")
        
        roi_factors = calculate_roi_factors(user_id)
        
        if not roi_factors:
            return jsonify({
                'status': 'error',
                'message': 'Unable to generate recommendations'
            }), 500
        
        recommendations = []
        factor_contributions = {
            'electricity_contribution': roi_factors['factor_impacts']['electricity_cost']['contribution_percent'],
            'difficulty_contribution': roi_factors['factor_impacts']['difficulty']['contribution_percent'],
            'btc_price_contribution': roi_factors['factor_impacts']['btc_price']['contribution_percent'],
            'offline_contribution': roi_factors['factor_impacts']['offline_rate']['contribution_percent']
        }
        current_metrics = roi_factors['current_metrics']
        
        if factor_contributions['electricity_contribution'] > 30:
            recommendations.append({
                'priority': 'high',
                'category': 'electricity_cost',
                'title': 'Optimize Electricity Costs',
                'description': f'Electricity cost is your biggest ROI factor ({factor_contributions["electricity_contribution"]:.1f}%). Consider power curtailment during peak hours.',
                'potential_impact': 'High - Can improve ROI by 5-15%',
                'action': 'Use curtailment optimization API to reduce costs during peak hours'
            })
        
        if factor_contributions['difficulty_contribution'] > 25:
            recommendations.append({
                'priority': 'medium',
                'category': 'network_difficulty',
                'title': 'Monitor Difficulty Trends',
                'description': f'Network difficulty significantly impacts your ROI ({factor_contributions["difficulty_contribution"]:.1f}%). Track forecasts closely.',
                'potential_impact': 'Medium - Stay informed on profitability changes',
                'action': 'Review difficulty forecasts weekly via forecast API'
            })
        
        if factor_contributions['btc_price_contribution'] > 35:
            recommendations.append({
                'priority': 'high',
                'category': 'btc_price',
                'title': 'BTC Price Sensitivity',
                'description': f'Your ROI is highly sensitive to BTC price ({factor_contributions["btc_price_contribution"]:.1f}%). Consider hedging strategies.',
                'potential_impact': 'High - Protect against price volatility',
                'action': 'Consider using derivatives or DCA selling strategies'
            })
        
        if factor_contributions['offline_contribution'] > 20:
            recommendations.append({
                'priority': 'high',
                'category': 'uptime',
                'title': 'Improve Miner Uptime',
                'description': f'Offline time is significantly impacting ROI ({factor_contributions["offline_contribution"]:.1f}%). Focus on reliability.',
                'potential_impact': 'High - Each 1% uptime improvement adds to ROI',
                'action': 'Implement automated monitoring and rapid response protocols'
            })
        
        if current_metrics['annual_roi_percent'] < 20:
            recommendations.append({
                'priority': 'high',
                'category': 'general',
                'title': 'Low ROI Alert',
                'description': f'Current ROI is {current_metrics["annual_roi_percent"]:.1f}%, which is below industry average. Urgent optimization needed.',
                'potential_impact': 'Critical - Address immediately',
                'action': 'Review all operational parameters and consider equipment upgrade or relocation'
            })
        
        recommendations.sort(key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['priority']])
        
        logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'recommendations': recommendations,
            'roi_context': {
                'current_roi': current_metrics['annual_roi_percent'],
                'daily_profit': current_metrics['daily_profit_usd']
            },
            'generated_at': roi_factors.get('generated_at')
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating recommendations for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500
