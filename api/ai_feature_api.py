"""
AI Feature API
AI 功能 API - 第一阶段：解释与建议（不自动执行）

提供三个高频场景的 AI 辅助:
1. 告警解释 - 减少值班人员"看图猜原因"的时间
2. 工单草稿 - 把"写工单"从 10–20 分钟压到 1–2 分钟
3. 限电建议 - 把"凭经验拍脑袋"变成"可解释的策略建议"

验收口径：AI 不需要 100% 正确，但要做到：可复核、有证据、能节省时间

Endpoints:
    POST /api/v1/ai/diagnose/alert - 告警诊断
    POST /api/v1/ai/diagnose/batch - 批量告警诊断
    POST /api/v1/ai/ticket/draft - 生成工单草稿
    POST /api/v1/ai/curtailment/plan - 生成限电计划
"""

import logging
from functools import wraps
from flask import Blueprint, request, jsonify, g, session

from db import db
from models import UserAccess

logger = logging.getLogger(__name__)

ai_feature_bp = Blueprint('ai_feature_api', __name__)


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


@ai_feature_bp.route('/api/v1/ai/diagnose/alert', methods=['POST'])
@require_user_auth
def diagnose_alert():
    """诊断单个告警
    
    Request Body:
        - site_id (int, required): 站点ID
        - miner_id (string, required): 矿机ID
        - alert_type (string, required): 告警类型
        - alert_id (string, optional): 告警ID
    
    Response:
        - diagnosis: 诊断结果，包含 Top3 根因假设、证据、建议动作
    """
    from services.ai_alert_diagnosis_service import alert_diagnosis_service
    
    data = request.get_json() or {}
    
    required_fields = ['site_id', 'miner_id', 'alert_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    try:
        result = alert_diagnosis_service.diagnose_alert(
            site_id=data['site_id'],
            miner_id=data['miner_id'],
            alert_type=data['alert_type'],
            alert_id=data.get('alert_id'),
        )
        
        return jsonify({
            'success': True,
            'diagnosis': alert_diagnosis_service.to_dict(result),
        })
        
    except Exception as e:
        logger.error(f"Failed to diagnose alert: {e}")
        return jsonify({'error': str(e)}), 500


@ai_feature_bp.route('/api/v1/ai/diagnose/batch', methods=['POST'])
@require_user_auth
def diagnose_batch():
    """批量诊断多台矿机
    
    Request Body:
        - site_id (int, required): 站点ID
        - alert_type (string, required): 告警类型
        - miner_ids (array, required): 矿机ID列表
    
    Response:
        - diagnoses: 诊断结果字典，key 为 miner_id
    """
    from services.ai_alert_diagnosis_service import alert_diagnosis_service
    
    data = request.get_json() or {}
    
    required_fields = ['site_id', 'alert_type', 'miner_ids']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    if not isinstance(data['miner_ids'], list) or not data['miner_ids']:
        return jsonify({'error': 'miner_ids must be a non-empty array'}), 400
    
    try:
        results = alert_diagnosis_service.diagnose_batch(
            site_id=data['site_id'],
            alert_type=data['alert_type'],
            miner_ids=data['miner_ids'],
        )
        
        return jsonify({
            'success': True,
            'diagnoses': {
                miner_id: alert_diagnosis_service.to_dict(result)
                for miner_id, result in results.items()
            },
            'count': len(results),
        })
        
    except Exception as e:
        logger.error(f"Failed to diagnose batch: {e}")
        return jsonify({'error': str(e)}), 500


@ai_feature_bp.route('/api/v1/ai/ticket/draft', methods=['POST'])
@require_user_auth
def generate_ticket_draft():
    """生成工单草稿
    
    Request Body:
        - site_id (int, required): 站点ID
        - miner_ids (array, required): 受影响矿机ID列表
        - alert_type (string, required): 告警类型
        - diagnosis (object, optional): 诊断结果（如果已有）
        - site_info (object, optional): 站点信息
        - miner_info (object, optional): 矿机信息
    
    Response:
        - ticket_draft: 结构化工单草稿
    """
    from services.ai_alert_diagnosis_service import alert_diagnosis_service
    from services.ai_ticket_draft_service import ticket_draft_service
    
    data = request.get_json() or {}
    
    required_fields = ['site_id', 'miner_ids', 'alert_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    if not isinstance(data['miner_ids'], list) or not data['miner_ids']:
        return jsonify({'error': 'miner_ids must be a non-empty array'}), 400
    
    try:
        diagnosis_result = data.get('diagnosis')
        if not diagnosis_result:
            first_miner = data['miner_ids'][0]
            result = alert_diagnosis_service.diagnose_alert(
                site_id=data['site_id'],
                miner_id=first_miner,
                alert_type=data['alert_type'],
            )
            diagnosis_result = alert_diagnosis_service.to_dict(result)
        
        draft = ticket_draft_service.generate_ticket_draft(
            site_id=data['site_id'],
            miner_ids=data['miner_ids'],
            alert_type=data['alert_type'],
            diagnosis_result=diagnosis_result,
            site_info=data.get('site_info'),
            miner_info=data.get('miner_info'),
        )
        
        return jsonify({
            'success': True,
            'ticket_draft': ticket_draft_service.to_dict(draft),
        })
        
    except Exception as e:
        logger.error(f"Failed to generate ticket draft: {e}")
        return jsonify({'error': str(e)}), 500


@ai_feature_bp.route('/api/v1/ai/curtailment/plan', methods=['POST'])
@require_user_auth
def generate_curtailment_plan():
    """生成限电计划
    
    Request Body:
        - site_id (int, required): 站点ID
        - target_reduction_kw (float, optional): 目标削减功率 (kW)
        - target_power_kw (float, optional): 目标总功率 (kW)
        - target_reduction_pct (float, optional): 目标削减百分比
        - electricity_price (float, optional): 电价 ($/kWh)，默认 0.05
        - btc_price (float, optional): BTC价格
        - strategy (string, optional): 关停策略
            - efficiency_first: 效率优先（先关效率低的）
            - power_first: 功率优先（先关功率大的）
            - revenue_first: 收益优先（先关利润低的）
            - temperature_first: 温度优先（先关温度高的）
        - max_miners_to_curtail (int, optional): 最大关停矿机数
        - exclude_miner_ids (array, optional): 排除的矿机ID列表
    
    Response:
        - curtailment_plan: 限电计划，包含关停顺序、收益损失预估、风险点
    """
    from services.ai_curtailment_advisor_service import curtailment_advisor_service
    
    data = request.get_json() or {}
    
    if 'site_id' not in data:
        return jsonify({'error': 'site_id is required'}), 400
    
    if not any(k in data for k in ['target_reduction_kw', 'target_power_kw', 'target_reduction_pct']):
        data['target_reduction_pct'] = 20
    
    try:
        plan = curtailment_advisor_service.generate_curtailment_plan(
            site_id=data['site_id'],
            target_reduction_kw=data.get('target_reduction_kw'),
            target_power_kw=data.get('target_power_kw'),
            target_reduction_pct=data.get('target_reduction_pct'),
            electricity_price=data.get('electricity_price', 0.05),
            btc_price=data.get('btc_price'),
            strategy=data.get('strategy', 'efficiency_first'),
            max_miners_to_curtail=data.get('max_miners_to_curtail'),
            exclude_miner_ids=data.get('exclude_miner_ids'),
        )
        
        return jsonify({
            'success': True,
            'curtailment_plan': curtailment_advisor_service.to_dict(plan),
        })
        
    except Exception as e:
        logger.error(f"Failed to generate curtailment plan: {e}")
        return jsonify({'error': str(e)}), 500


@ai_feature_bp.route('/api/v1/ai/curtailment/strategies', methods=['GET'])
@require_user_auth
def list_curtailment_strategies():
    """获取可用的限电策略列表"""
    strategies = [
        {
            'id': 'efficiency_first',
            'name': 'Efficiency First',
            'name_zh': '效率优先',
            'description': 'Shut down miners with worst efficiency (highest J/TH) first',
            'description_zh': '优先关停效率最差（J/TH 最高）的矿机',
        },
        {
            'id': 'power_first',
            'name': 'Power First',
            'name_zh': '功率优先',
            'description': 'Shut down highest power consuming miners first',
            'description_zh': '优先关停功耗最高的矿机',
        },
        {
            'id': 'revenue_first',
            'name': 'Revenue First',
            'name_zh': '收益优先',
            'description': 'Shut down miners with lowest profit margin first',
            'description_zh': '优先关停利润最低的矿机',
        },
        {
            'id': 'temperature_first',
            'name': 'Temperature First',
            'name_zh': '温度优先',
            'description': 'Shut down hottest running miners first',
            'description_zh': '优先关停运行温度最高的矿机',
        },
    ]
    
    return jsonify({
        'strategies': strategies,
    })


def register_ai_feature_routes(app):
    """Register the AI Feature blueprint with the Flask app"""
    app.register_blueprint(ai_feature_bp)
    logger.info("AI Feature API registered")
