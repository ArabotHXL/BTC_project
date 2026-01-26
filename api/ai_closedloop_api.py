"""
AI Closed-Loop API
AI 闭环流程 API

提供完整的闭环流程接口:
告警(Detect) → 诊断(Diagnose) → 建议(Recommend) → 审批(Approve) → 执行(Act) → 审计(Audit) → 复盘(Learn)

Endpoints:
    GET  /api/v1/ai/recommendations - 获取建议列表
    POST /api/v1/ai/recommendations - 创建新建议
    GET  /api/v1/ai/recommendations/<id> - 获取建议详情
    POST /api/v1/ai/recommendations/<id>/approve - 审批建议
    POST /api/v1/ai/recommendations/<id>/reject - 拒绝建议
    POST /api/v1/ai/recommendations/<id>/execute - 执行建议
    POST /api/v1/ai/recommendations/<id>/feedback - 提交反馈
    GET  /api/v1/ai/learning/stats - 获取学习统计
"""

import logging
from functools import wraps
from flask import Blueprint, request, jsonify, g, session

from db import db
from models import UserAccess
from models_ai_closedloop import AIRecommendation, RecommendationStatus, RiskLevel
from services.ai_closedloop_service import ai_closedloop_service
from common.feature_gates import require_feature

logger = logging.getLogger(__name__)

ai_closedloop_bp = Blueprint('ai_closedloop_api', __name__)


def require_user_auth(f):
    """Require user authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id or not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        g.user = user
        g.user_id = user.id
        g.user_role = user.role or 'user'
        return f(*args, **kwargs)
    return decorated


@ai_closedloop_bp.route('/api/v1/ai/recommendations', methods=['GET'])
@require_user_auth
def list_recommendations():
    """Get AI recommendations list
    
    Query Parameters:
        site_id (int, optional): Filter by site
        status (string, optional): Filter by status
        limit (int, optional): Max results (default 50)
    """
    site_id = request.args.get('site_id', type=int)
    status = request.args.get('status')
    limit = min(request.args.get('limit', 50, type=int), 200)
    
    if status == 'pending':
        recommendations = ai_closedloop_service.get_pending_recommendations(
            site_id=site_id,
            limit=limit
        )
    elif site_id:
        recommendations = ai_closedloop_service.get_recommendation_history(
            site_id=site_id,
            status=status,
            limit=limit
        )
    else:
        query = AIRecommendation.query
        if status:
            query = query.filter_by(status=status)
        recommendations = query.order_by(
            AIRecommendation.created_at.desc()
        ).limit(limit).all()
    
    return jsonify({
        'recommendations': [r.to_dict() for r in recommendations],
        'count': len(recommendations),
    })


@ai_closedloop_bp.route('/api/v1/ai/recommendations', methods=['POST'])
@require_user_auth
def create_recommendation():
    """Create a new AI recommendation
    
    Request Body:
        - site_id (int, required)
        - trigger_type (string, required): alert, anomaly, schedule, user_request
        - trigger_id (string, optional)
        - trigger_data (object, optional)
        - diagnosis (object, required): {root_cause, evidence, confidence}
        - action_type (string, required)
        - action_params (object, optional)
        - target_ids (array, optional)
        - risk_level (string, optional): low, medium, high, critical
        - confidence_score (number, optional): 0-1
        - priority (int, optional): 1-10
        - expected_benefit (object, optional)
    """
    data = request.get_json() or {}
    
    required_fields = ['site_id', 'trigger_type', 'diagnosis', 'action_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    try:
        recommendation = ai_closedloop_service.create_recommendation(
            site_id=data['site_id'],
            trigger_type=data['trigger_type'],
            trigger_id=data.get('trigger_id'),
            trigger_data=data.get('trigger_data'),
            diagnosis=data['diagnosis'],
            action_type=data['action_type'],
            action_params=data.get('action_params'),
            target_ids=data.get('target_ids'),
            risk_level=data.get('risk_level', RiskLevel.MEDIUM),
            confidence_score=data.get('confidence_score'),
            priority=data.get('priority', 5),
            expected_benefit=data.get('expected_benefit'),
        )
        
        return jsonify({
            'success': True,
            'recommendation': recommendation.to_dict(),
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create recommendation: {e}")
        return jsonify({'error': str(e)}), 500


@ai_closedloop_bp.route('/api/v1/ai/recommendations/<recommendation_id>', methods=['GET'])
@require_user_auth
def get_recommendation(recommendation_id):
    """Get AI recommendation details"""
    recommendation = AIRecommendation.query.get(recommendation_id)
    if not recommendation:
        return jsonify({'error': 'Recommendation not found'}), 404
    
    feedback_entries = recommendation.feedback_entries.all()
    
    return jsonify({
        'recommendation': recommendation.to_dict(include_evidence=True),
        'feedback': [f.to_dict() for f in feedback_entries],
    })


@ai_closedloop_bp.route('/api/v1/ai/recommendations/<recommendation_id>/approve', methods=['POST'])
@require_user_auth
def approve_recommendation(recommendation_id):
    """Approve a pending recommendation
    
    Request Body:
        - reason (string, optional): Approval reason
    """
    data = request.get_json() or {}
    reason = data.get('reason')
    
    try:
        recommendation = ai_closedloop_service.approve_recommendation(
            recommendation_id=recommendation_id,
            user_id=g.user_id,
            reason=reason,
        )
        
        return jsonify({
            'success': True,
            'recommendation': recommendation.to_dict(),
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to approve recommendation: {e}")
        return jsonify({'error': str(e)}), 500


@ai_closedloop_bp.route('/api/v1/ai/recommendations/<recommendation_id>/reject', methods=['POST'])
@require_user_auth
def reject_recommendation(recommendation_id):
    """Reject a pending recommendation
    
    Request Body:
        - reason (string, required): Rejection reason
    """
    data = request.get_json() or {}
    reason = data.get('reason')
    
    if not reason:
        return jsonify({'error': 'reason is required'}), 400
    
    try:
        recommendation = ai_closedloop_service.reject_recommendation(
            recommendation_id=recommendation_id,
            user_id=g.user_id,
            reason=reason,
        )
        
        return jsonify({
            'success': True,
            'recommendation': recommendation.to_dict(),
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to reject recommendation: {e}")
        return jsonify({'error': str(e)}), 500


@ai_closedloop_bp.route('/api/v1/ai/recommendations/<recommendation_id>/execute', methods=['POST'])
@require_user_auth
def execute_recommendation(recommendation_id):
    """Execute an approved recommendation
    
    Creates a command in Control Plane v1 and dispatches it.
    """
    try:
        result = ai_closedloop_service.execute_recommendation(
            recommendation_id=recommendation_id,
            operator_id=g.user_id,
        )
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to execute recommendation: {e}")
        return jsonify({'error': str(e)}), 500


@ai_closedloop_bp.route('/api/v1/ai/recommendations/<recommendation_id>/feedback', methods=['POST'])
@require_user_auth
def add_feedback(recommendation_id):
    """Add feedback for learning loop
    
    Request Body:
        - feedback_type (string, required): execution_result, user_review, automated_check
        - was_effective (bool, optional)
        - outcome_metrics (object, optional)
        - user_rating (int, optional): 1-5
        - user_comment (string, optional)
        - side_effects (object, optional)
    """
    data = request.get_json() or {}
    
    if 'feedback_type' not in data:
        return jsonify({'error': 'feedback_type is required'}), 400
    
    try:
        feedback = ai_closedloop_service.add_feedback(
            recommendation_id=recommendation_id,
            feedback_type=data['feedback_type'],
            was_effective=data.get('was_effective'),
            outcome_metrics=data.get('outcome_metrics'),
            user_rating=data.get('user_rating'),
            user_comment=data.get('user_comment'),
            side_effects=data.get('side_effects'),
            user_id=g.user_id,
        )
        
        return jsonify({
            'success': True,
            'feedback': feedback.to_dict(),
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to add feedback: {e}")
        return jsonify({'error': str(e)}), 500


@ai_closedloop_bp.route('/api/v1/ai/learning/stats', methods=['GET'])
@require_user_auth
def get_learning_stats():
    """Get learning statistics for a site
    
    Query Parameters:
        - site_id (int, required)
    """
    site_id = request.args.get('site_id', type=int)
    
    if not site_id:
        return jsonify({'error': 'site_id is required'}), 400
    
    try:
        stats = ai_closedloop_service.get_learning_stats(site_id)
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Failed to get learning stats: {e}")
        return jsonify({'error': str(e)}), 500


def register_ai_closedloop_routes(app):
    """Register the AI closed-loop blueprint with the Flask app"""
    app.register_blueprint(ai_closedloop_bp)
    logger.info("AI Closed-Loop API registered")
