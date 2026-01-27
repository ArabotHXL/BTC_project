"""
AI Auto Execution API
AI 自动执行 API

Phase 3 endpoints:
- 风险评估
- 自动审批规则管理
- 待审批建议查询
- 执行自动审批的建议
"""

import logging
from functools import wraps
from flask import Blueprint, request, jsonify, g, session

from db import db
from models import UserAccess
from models_ai_closedloop import AIRecommendation, AutoApproveRule, RecommendationStatus

logger = logging.getLogger(__name__)

ai_auto_execution_bp = Blueprint('ai_auto_execution_api', __name__)


def require_auth(f):
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


def require_operator(f):
    """Require operator or higher role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if g.user_role not in ('operator', 'manager', 'admin'):
            return jsonify({'error': 'Operator access required'}), 403
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Require admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if g.user_role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


@ai_auto_execution_bp.route('/api/v1/ai/auto/assess-risk', methods=['POST'])
@require_auth
def assess_risk():
    """Assess risk of a proposed action
    
    Request Body:
        - action_type (string): Action type (power_off, curtail, etc.)
        - target_ids (array): Target device IDs
        - power_impact_kw (float): Estimated power impact
        - revenue_impact_pct (float): Estimated revenue impact percentage
        - confidence_score (float): AI confidence (0-1)
    
    Response:
        - risk_assessment: Risk level, score, factors, auto-execute eligibility
    """
    from services.ai_auto_execution_service import ai_auto_execution_service
    
    data = request.get_json() or {}
    
    if 'action_type' not in data:
        return jsonify({'error': 'action_type is required'}), 400
    
    assessment = ai_auto_execution_service.assess_risk(
        action_type=data['action_type'],
        target_ids=data.get('target_ids', []),
        power_impact_kw=data.get('power_impact_kw', 0),
        revenue_impact_pct=data.get('revenue_impact_pct', 0),
        confidence_score=data.get('confidence_score', 0.5),
        historical_success_rate=data.get('historical_success_rate', 0.9),
        time_of_day_risk=data.get('time_of_day_risk', 0.0),
    )
    
    return jsonify({
        'success': True,
        'risk_assessment': assessment.to_dict(),
    })


@ai_auto_execution_bp.route('/api/v1/ai/auto/recommendations', methods=['GET'])
@require_auth
def get_pending_recommendations():
    """Get pending AI recommendations awaiting approval
    
    Query Parameters:
        - site_id (int, optional): Filter by site
        - status (string, optional): Filter by status
        - limit (int, optional): Limit results (default 50)
    """
    site_id = request.args.get('site_id', type=int)
    status = request.args.get('status', 'pending')
    limit = request.args.get('limit', 50, type=int)
    
    query = AIRecommendation.query
    
    if site_id:
        query = query.filter_by(site_id=site_id)
    
    if status and status != 'all':
        query = query.filter_by(status=status)
    
    recommendations = query.order_by(
        AIRecommendation.priority,
        AIRecommendation.created_at.desc()
    ).limit(limit).all()
    
    return jsonify({
        'success': True,
        'recommendations': [r.to_dict(include_evidence=False) for r in recommendations],
        'count': len(recommendations),
    })


@ai_auto_execution_bp.route('/api/v1/ai/auto/recommendations/<rec_id>/approve', methods=['POST'])
@require_auth
@require_operator
def approve_recommendation(rec_id):
    """Approve a pending recommendation
    
    Request Body:
        - reason (string, optional): Approval reason
    """
    from services.ai_closedloop_service import AIClosedLoopService
    
    data = request.get_json() or {}
    
    try:
        rec = AIClosedLoopService.approve_recommendation(
            recommendation_id=rec_id,
            user_id=g.user_id,
            reason=data.get('reason'),
        )
        
        return jsonify({
            'success': True,
            'recommendation': rec.to_dict(),
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to approve recommendation: {e}")
        return jsonify({'error': str(e)}), 500


@ai_auto_execution_bp.route('/api/v1/ai/auto/recommendations/<rec_id>/reject', methods=['POST'])
@require_auth
@require_operator
def reject_recommendation(rec_id):
    """Reject a pending recommendation
    
    Request Body:
        - reason (string, required): Rejection reason
    """
    from services.ai_closedloop_service import AIClosedLoopService
    
    data = request.get_json() or {}
    
    if not data.get('reason'):
        return jsonify({'error': 'reason is required'}), 400
    
    try:
        rec = AIClosedLoopService.reject_recommendation(
            recommendation_id=rec_id,
            user_id=g.user_id,
            reason=data['reason'],
        )
        
        return jsonify({
            'success': True,
            'recommendation': rec.to_dict(),
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to reject recommendation: {e}")
        return jsonify({'error': str(e)}), 500


@ai_auto_execution_bp.route('/api/v1/ai/auto/recommendations/<rec_id>/execute', methods=['POST'])
@require_auth
@require_operator
def execute_recommendation(rec_id):
    """Execute an approved recommendation"""
    from services.ai_closedloop_service import AIClosedLoopService
    
    try:
        result = AIClosedLoopService.execute_recommendation(
            recommendation_id=rec_id,
            operator_id=g.user_id,
        )
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to execute recommendation: {e}")
        return jsonify({'error': str(e)}), 500


@ai_auto_execution_bp.route('/api/v1/ai/auto/rules', methods=['GET'])
@require_auth
def get_auto_approve_rules():
    """Get auto-approve rules for a site
    
    Query Parameters:
        - site_id (int, required): Site ID
    """
    site_id = request.args.get('site_id', type=int)
    if not site_id:
        return jsonify({'error': 'site_id is required'}), 400
    
    rules = AutoApproveRule.query.filter_by(site_id=site_id).all()
    
    return jsonify({
        'success': True,
        'rules': [r.to_dict() for r in rules],
        'count': len(rules),
    })


@ai_auto_execution_bp.route('/api/v1/ai/auto/rules', methods=['POST'])
@require_auth
@require_admin
def create_auto_approve_rule():
    """Create a new auto-approve rule
    
    Request Body:
        - site_id (int, required): Site ID
        - name (string, required): Rule name
        - description (string, optional): Rule description
        - conditions (object, required): Auto-approve conditions
            - max_risk_level (string): Maximum risk level (low, medium)
            - min_confidence (float): Minimum AI confidence (0-1)
            - allowed_actions (array): Allowed action types
            - max_targets (int): Maximum number of targets
    """
    from services.ai_auto_execution_service import ai_auto_execution_service
    
    data = request.get_json() or {}
    
    required_fields = ['site_id', 'name', 'conditions']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    try:
        rule = ai_auto_execution_service.create_auto_approve_rule(
            site_id=data['site_id'],
            name=data['name'],
            conditions=data['conditions'],
            description=data.get('description'),
            created_by_user_id=g.user_id,
        )
        
        return jsonify({
            'success': True,
            'rule': rule.to_dict(),
        })
        
    except Exception as e:
        logger.error(f"Failed to create auto-approve rule: {e}")
        return jsonify({'error': str(e)}), 500


@ai_auto_execution_bp.route('/api/v1/ai/auto/rules/<int:rule_id>', methods=['PUT'])
@require_auth
@require_admin
def update_auto_approve_rule(rule_id):
    """Update an auto-approve rule"""
    from services.ai_auto_execution_service import ai_auto_execution_service
    
    data = request.get_json() or {}
    
    try:
        rule = ai_auto_execution_service.update_auto_approve_rule(
            rule_id=rule_id,
            conditions=data.get('conditions'),
            is_active=data.get('is_active'),
            name=data.get('name'),
            description=data.get('description'),
        )
        
        return jsonify({
            'success': True,
            'rule': rule.to_dict(),
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Failed to update auto-approve rule: {e}")
        return jsonify({'error': str(e)}), 500


@ai_auto_execution_bp.route('/api/v1/ai/auto/rules/<int:rule_id>', methods=['DELETE'])
@require_auth
@require_admin
def delete_auto_approve_rule(rule_id):
    """Delete (deactivate) an auto-approve rule"""
    rule = AutoApproveRule.query.get(rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    
    rule.is_active = False
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Rule deactivated',
    })


@ai_auto_execution_bp.route('/api/v1/ai/auto/execute-approved', methods=['POST'])
@require_auth
@require_operator
def execute_auto_approved():
    """Execute all auto-approved recommendations for a site
    
    Request Body:
        - site_id (int, optional): Limit to specific site
    """
    from services.ai_auto_execution_service import ai_auto_execution_service
    
    data = request.get_json() or {}
    
    results = ai_auto_execution_service.execute_auto_approved(
        site_id=data.get('site_id'),
        operator_id=g.user_id,
    )
    
    success_count = sum(1 for r in results if r.get('success'))
    
    return jsonify({
        'success': True,
        'results': results,
        'executed_count': success_count,
        'failed_count': len(results) - success_count,
    })


@ai_auto_execution_bp.route('/api/v1/ai/auto/curtailment/create', methods=['POST'])
@require_auth
@require_operator
def create_curtailment_recommendation():
    """Create a curtailment recommendation from AI advisor plan
    
    Request Body:
        - site_id (int, required): Site ID
        - curtailment_plan (object, required): Output from CurtailmentAdvisorService
    """
    from services.ai_auto_execution_service import ai_auto_execution_service
    
    data = request.get_json() or {}
    
    if 'site_id' not in data:
        return jsonify({'error': 'site_id is required'}), 400
    if 'curtailment_plan' not in data:
        return jsonify({'error': 'curtailment_plan is required'}), 400
    
    try:
        recommendation = ai_auto_execution_service.create_curtailment_recommendation(
            site_id=data['site_id'],
            curtailment_plan=data['curtailment_plan'],
            trigger_type=data.get('trigger_type', 'user_request'),
            trigger_id=data.get('trigger_id'),
            operator_id=g.user_id,
        )
        
        auto_executed = getattr(recommendation, '_auto_executed', False)
        was_auto_approved = (
            recommendation.status in [
                RecommendationStatus.APPROVED,
                RecommendationStatus.EXECUTING,
                RecommendationStatus.COMPLETED
            ]
        )
        
        return jsonify({
            'success': True,
            'recommendation': recommendation.to_dict(),
            'auto_approved': was_auto_approved,
            'auto_executed': auto_executed,
        })
        
    except Exception as e:
        logger.error(f"Failed to create curtailment recommendation: {e}")
        return jsonify({'error': str(e)}), 500
