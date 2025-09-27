"""
NFT相关路由
SLA证书NFT铸造、查询、验证
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, session, render_template

try:
    from ..services.nft_minting import sla_nft_minting_system
    from ..services.nft_metadata import nft_metadata_generator
    from .auth import require_wallet_auth
except ImportError:
    # Fallback for standalone execution
    from services.nft_minting import sla_nft_minting_system
    from services.nft_metadata import nft_metadata_generator
    from routes.auth import require_wallet_auth

logger = logging.getLogger(__name__)

# 创建蓝图
nft_bp = Blueprint('nft', __name__, url_prefix='/nft')

@nft_bp.route('/certificates', methods=['GET'])
@require_wallet_auth
def get_user_certificates():
    """获取用户的SLA证书NFT列表"""
    try:
        user_id = session.get('user_id')
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        
        # 在实际实现中，这里应该从数据库查询用户的证书
        certificates = []
        total_count = 0
        
        return jsonify({
            'success': True,
            'certificates': certificates,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"获取用户证书失败: {e}")
        return jsonify({'error': 'Failed to get certificates'}), 500

@nft_bp.route('/certificates/<int:certificate_id>', methods=['GET'])
@require_wallet_auth
def get_certificate_details(certificate_id):
    """获取证书详情"""
    try:
        user_id = session.get('user_id')
        
        # 在实际实现中，这里应该从数据库查询证书详情
        # 验证证书是否属于当前用户
        
        certificate = {
            'id': certificate_id,
            'month_year': 202509,
            'sla_score': 95.8,
            'status': 'minted',
            'token_id': 123,
            'contract_address': '0x123...abc',
            'token_uri': 'ipfs://QmExample...',
            'transaction_hash': '0xabc...def',
            'created_at': datetime.utcnow().isoformat(),
            'minted_at': datetime.utcnow().isoformat(),
            'metrics': {
                'uptime_percentage': 99.95,
                'response_time_avg': 150.5,
                'accuracy_percentage': 99.8,
                'transparency_score': 92.0
            }
        }
        
        return jsonify({
            'success': True,
            'certificate': certificate
        })
        
    except Exception as e:
        logger.error(f"获取证书详情失败: {e}")
        return jsonify({'error': 'Failed to get certificate details'}), 500

@nft_bp.route('/certificates/mint', methods=['POST'])
@require_wallet_auth
def mint_certificate():
    """手动铸造SLA证书NFT"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        # 验证必需字段
        required_fields = ['month_year', 'sla_score', 'metrics']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        month_year = data['month_year']
        sla_score = float(data['sla_score'])
        
        # 验证SLA分数范围
        if not (0 <= sla_score <= 100):
            return jsonify({'error': 'SLA score must be between 0 and 100'}), 400
        
        # 检查是否已经存在该月份的证书
        # 在实际实现中，这里应该查询数据库
        
        # 生成NFT元数据
        certificate_data = {
            'id': 1,  # 从数据库获取
            'month_year': month_year,
            'sla_score': sla_score,
            'metrics': data['metrics'],
            'user_info': {
                'wallet_address': session.get('wallet_address')
            }
        }
        
        metadata = nft_metadata_generator.generate_sla_certificate_metadata(certificate_data)
        
        # 添加到铸造队列
        # 在实际实现中，这里应该创建铸造任务
        
        return jsonify({
            'success': True,
            'message': 'Certificate minting initiated',
            'metadata': metadata,
            'estimated_completion': '5-10 minutes'
        })
        
    except ValueError as e:
        logger.error(f"铸造证书失败: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"铸造证书失败: {e}")
        return jsonify({'error': 'Failed to mint certificate'}), 500

@nft_bp.route('/certificates/<int:certificate_id>/metadata', methods=['GET'])
def get_certificate_metadata(certificate_id):
    """获取证书元数据（公开访问）"""
    try:
        # 在实际实现中，这里应该从数据库查询证书
        # 注意：这个端点是公开的，用于NFT市场显示
        
        certificate_data = {
            'id': certificate_id,
            'month_year': 202509,
            'sla_score': 95.8,
            'metrics': {
                'uptime_percentage': 99.95,
                'response_time_avg': 150.5,
                'accuracy_percentage': 99.8,
                'transparency_score': 92.0
            },
            'user_info': {
                'wallet_address': '0x123...abc'
            }
        }
        
        metadata = nft_metadata_generator.generate_sla_certificate_metadata(certificate_data)
        
        return jsonify(metadata)
        
    except Exception as e:
        logger.error(f"获取证书元数据失败: {e}")
        return jsonify({'error': 'Failed to get certificate metadata'}), 500

@nft_bp.route('/certificates/<int:certificate_id>/verify', methods=['POST'])
@require_wallet_auth
def verify_certificate(certificate_id):
    """验证证书（第三方验证者）"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        # 验证必需字段
        required_fields = ['is_valid', 'verification_note']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # 检查用户是否有验证权限
        # 在实际实现中，这里应该检查用户是否是授权验证者
        
        is_valid = data['is_valid']
        verification_note = data['verification_note']
        
        # 在实际实现中，这里应该：
        # 1. 更新数据库中的证书验证状态
        # 2. 调用智能合约的验证函数
        
        return jsonify({
            'success': True,
            'message': 'Certificate verification recorded',
            'verification': {
                'verifier': session.get('wallet_address'),
                'is_valid': is_valid,
                'note': verification_note,
                'verified_at': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"验证证书失败: {e}")
        return jsonify({'error': 'Failed to verify certificate'}), 500

@nft_bp.route('/minting/status', methods=['GET'])
@require_wallet_auth
def get_minting_status():
    """获取铸造服务状态"""
    try:
        stats = sla_nft_minting_system.get_minting_statistics()
        
        return jsonify({
            'success': True,
            'minting_service': stats
        })
        
    except Exception as e:
        logger.error(f"获取铸造状态失败: {e}")
        return jsonify({'error': 'Failed to get minting status'}), 500

@nft_bp.route('/minting/queue', methods=['GET'])
@require_wallet_auth
def get_minting_queue():
    """获取铸造队列状态"""
    try:
        user_id = session.get('user_id')
        
        # 在实际实现中，这里应该查询用户的铸造任务
        queue_status = {
            'pending_tasks': 0,
            'processing_tasks': 0,
            'completed_tasks': 5,
            'failed_tasks': 0,
            'user_tasks': []
        }
        
        return jsonify({
            'success': True,
            'queue': queue_status
        })
        
    except Exception as e:
        logger.error(f"获取铸造队列失败: {e}")
        return jsonify({'error': 'Failed to get minting queue'}), 500

@nft_bp.route('/monthly-report/<int:month_year>', methods=['GET'])
def get_monthly_report(month_year):
    """获取月度报告（公开访问）"""
    try:
        # 在实际实现中，这里应该从数据库或IPFS获取月度报告
        
        report = {
            'month_year': month_year,
            'total_certificates': 0,
            'average_sla': 0,
            'grade_distribution': {
                'excellent': 0,
                'good': 0,
                'acceptable': 0,
                'poor': 0,
                'failed': 0
            },
            'ipfs_cid': '',
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"获取月度报告失败: {e}")
        return jsonify({'error': 'Failed to get monthly report'}), 500

@nft_bp.route('/contract/info', methods=['GET'])
def get_contract_info():
    """获取NFT合约信息（公开访问）"""
    try:
        contract_info = {
            'name': 'SLA Proof NFT',
            'symbol': 'SLANFT',
            'version': '1.0.0',
            'contract_address': sla_nft_minting_system.sla_nft_contract_address,
            'network': 'Base' if sla_nft_minting_system.blockchain_integration.is_mainnet_mode else 'Base Sepolia',
            'total_supply': 0,  # 从合约查询
            'features': [
                'Soulbound (Non-transferable)',
                'Monthly SLA Certificates',
                'On-chain Verification',
                'IPFS Metadata Storage',
                'SVG Image Generation'
            ]
        }
        
        return jsonify({
            'success': True,
            'contract': contract_info
        })
        
    except Exception as e:
        logger.error(f"获取合约信息失败: {e}")
        return jsonify({'error': 'Failed to get contract info'}), 500

# 前端页面路由
@nft_bp.route('/page/certificates')
@require_wallet_auth
def certificates_page():
    """证书列表页面"""
    return render_template('nft/certificates.html')

@nft_bp.route('/page/certificate/<int:certificate_id>')
@require_wallet_auth
def certificate_detail_page(certificate_id):
    """证书详情页面"""
    return render_template('nft/certificate_detail.html', certificate_id=certificate_id)

@nft_bp.route('/page/mint')
@require_wallet_auth
def mint_page():
    """铸造页面"""
    return render_template('nft/mint.html')

@nft_bp.route('/page/verify')
@require_wallet_auth
def verify_page():
    """验证页面"""
    return render_template('nft/verify.html')