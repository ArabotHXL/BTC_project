"""
Web3 SLA NFT接口
Web3 SLA NFT API

提供SLA证书NFT的铸造和查询功能（占位实现）
"""

from flask import Blueprint, request, jsonify
from api_auth_middleware import require_api_auth
from common.rbac import require_permission, Permission
from features import FeatureFlags

web3_sla_bp = Blueprint('web3_sla_api', __name__, url_prefix='/api/web3/sla')


def feature_check():
    """检查Web3功能是否启用"""
    if not FeatureFlags.WEB3_ENABLED:
        return jsonify({
            'status': 'error',
            'message': 'Web3 feature is disabled. Set FEATURE_WEB3_ENABLED=true to enable.',
            'feature_enabled': False
        }), 503
    return None


@web3_sla_bp.route('/certificates', methods=['GET'])
@require_api_auth(required_permissions=[Permission.WEB3_READ], allow_session_auth=True)
@require_permission([Permission.WEB3_READ], require_all=True)
def get_sla_certificates():
    """
    获取SLA证书NFT列表（占位实现）
    
    Returns:
        JSON: 证书列表或功能未启用提示
    """
    check_result = feature_check()
    if check_result:
        return check_result
    
    user_id = request.args.get('user_id', type=int)
    
    return jsonify({
        'status': 'success',
        'feature': 'web3_sla_certificates',
        'enabled': True,
        'data': {
            'certificates': [
                {
                    'certificate_id': 'CERT-001',
                    'user_id': user_id or 1,
                    'nft_address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0',
                    'token_id': 1001,
                    'hashrate_th': 100.0,
                    'start_date': '2024-01-01',
                    'end_date': '2024-12-31',
                    'minted_at': '2024-01-01T00:00:00Z'
                }
            ],
            'total': 1
        },
        'note': 'This is a placeholder implementation. Real NFT data will be fetched from blockchain when integrated.'
    }), 200


@web3_sla_bp.route('/mint-request', methods=['POST'])
@require_api_auth(required_permissions=[Permission.WEB3_MINT], allow_session_auth=True)
@require_permission([Permission.WEB3_MINT], require_all=True)
def request_mint_sla_nft():
    """
    请求铸造SLA证书NFT（占位实现）
    
    Request Body:
        - user_id: int (required)
        - hashrate_th: float (required)
        - contract_type: str (default: "SLA_CERTIFICATE")
        - metadata: dict (optional)
    
    Returns:
        JSON: Mint请求结果
    """
    check_result = feature_check()
    if check_result:
        return check_result
    
    data = request.get_json()
    
    if not data or 'user_id' not in data or 'hashrate_th' not in data:
        return jsonify({
            'status': 'error',
            'message': 'user_id and hashrate_th are required'
        }), 400
    
    mint_request = {
        'mint_id': f"MINT-{data['user_id']}-{hash(str(data))}",
        'user_id': data['user_id'],
        'hashrate_th': data['hashrate_th'],
        'contract_type': data.get('contract_type', 'SLA_CERTIFICATE'),
        'status': 'pending',
        'estimated_completion': '2-5 minutes',
        'note': 'Placeholder: Real mint will interact with smart contract'
    }
    
    return jsonify({
        'status': 'success',
        'feature': 'web3_mint_request',
        'enabled': True,
        'data': mint_request
    }), 202
