"""
CRM集成接口
CRM Integration API

提供CRM系统对接功能（占位实现）
"""

from flask import Blueprint, request, jsonify
from api_auth_middleware import require_api_auth
from features import FeatureFlags
from common.rbac import require_permission, Permission

crm_integration_bp = Blueprint('crm_integration_api', __name__, url_prefix='/api/crm-integration')


def feature_check():
    """检查CRM功能是否启用"""
    if not FeatureFlags.CRM_ENABLED:
        return jsonify({
            'status': 'error',
            'message': 'CRM integration is disabled. Set FEATURE_CRM_ENABLED=true to enable.',
            'feature_enabled': False
        }), 503
    return None


@crm_integration_bp.route('/sync/customer', methods=['POST'])
@require_api_auth(required_permissions=[Permission.CRM_SYNC], allow_session_auth=True)
@require_permission([Permission.CRM_SYNC], require_all=True)
def sync_customer_to_crm():
    """
    同步客户数据到CRM（占位实现）
    
    Request Body:
        - customer_id: int (required)
        - sync_type: str ("create", "update", "delete")
    
    Returns:
        JSON: 同步结果
    """
    check_result = feature_check()
    if check_result:
        return check_result
    
    data = request.get_json()
    
    if not data or 'customer_id' not in data:
        return jsonify({
            'status': 'error',
            'message': 'customer_id is required'
        }), 400
    
    return jsonify({
        'status': 'success',
        'feature': 'crm_sync',
        'enabled': True,
        'data': {
            'customer_id': data['customer_id'],
            'sync_type': data.get('sync_type', 'update'),
            'crm_record_id': f"CRM-{data['customer_id']}",
            'synced_at': '2024-01-01T00:00:00Z',
            'note': 'Placeholder: Real CRM sync will use Salesforce/HubSpot API'
        }
    }), 200


@crm_integration_bp.route('/webhook/deal-stage', methods=['POST'])
@require_api_auth(required_permissions=[Permission.CRM_WEBHOOK], allow_session_auth=True)
@require_permission([Permission.CRM_WEBHOOK], require_all=True)
def handle_crm_deal_webhook():
    """
    接收CRM deal阶段变化webhook（占位实现）
    """
    check_result = feature_check()
    if check_result:
        return check_result
    
    data = request.get_json()
    
    return jsonify({
        'status': 'success',
        'feature': 'crm_webhook',
        'enabled': True,
        'data': {
            'webhook_id': f"WH-{hash(str(data))}",
            'processed': True,
            'note': 'Placeholder: Real webhook will trigger CRM workflow'
        }
    }), 200
