"""
Web3 SLA NFT接口
Web3 SLA NFT API

提供SLA证书NFT的铸造和查询功能
功能状态: Coming Soon (需要企业版订阅 + 区块链钱包设置)
"""

from flask import Blueprint, request, jsonify
from api_auth_middleware import require_api_auth
from common.rbac import require_permission, Permission
from common.feature_gates import require_feature, feature_disabled, is_feature_enabled

web3_sla_bp = Blueprint('web3_sla_api', __name__, url_prefix='/api/web3/sla')


@web3_sla_bp.route('/certificates', methods=['GET'])
@require_api_auth(required_permissions=[Permission.WEB3_READ], allow_session_auth=True)
@require_permission([Permission.WEB3_READ], require_all=True)
@require_feature('web3_sla')
def get_sla_certificates():
    """
    获取SLA证书NFT列表
    
    此功能需要:
    - Enterprise plan subscription
    - Blockchain wallet setup
    
    Returns:
        JSON: 证书列表（功能启用后）或 Coming Soon 响应
    """
    user_id = request.args.get('user_id', type=int)
    
    return jsonify({
        'status': 'success',
        'feature': 'web3_sla_certificates',
        'enabled': True,
        'data': {
            'certificates': [],
            'total': 0
        },
        'message': 'No certificates found. Mint your first SLA NFT certificate.'
    }), 200


@web3_sla_bp.route('/mint-request', methods=['POST'])
@require_api_auth(required_permissions=[Permission.WEB3_MINT], allow_session_auth=True)
@require_permission([Permission.WEB3_MINT], require_all=True)
@require_feature('web3_sla')
def request_mint_sla_nft():
    """
    请求铸造SLA证书NFT
    
    此功能需要:
    - Enterprise plan subscription
    - Blockchain wallet setup
    
    Request Body:
        - user_id: int (required)
        - hashrate_th: float (required)
        - contract_type: str (default: "SLA_CERTIFICATE")
        - metadata: dict (optional)
    
    Returns:
        JSON: Mint请求结果（功能启用后）或 Coming Soon 响应
    """
    data = request.get_json()
    
    if not data or 'user_id' not in data or 'hashrate_th' not in data:
        return jsonify({
            'status': 'error',
            'message': 'user_id and hashrate_th are required'
        }), 400
    
    return jsonify({
        'status': 'success',
        'feature': 'web3_mint_request',
        'enabled': True,
        'data': {
            'message': 'Mint request received. Processing...',
            'user_id': data['user_id'],
            'hashrate_th': data['hashrate_th'],
        }
    }), 202
