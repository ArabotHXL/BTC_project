#!/usr/bin/env python3
"""
SLA NFT API路由
SLA NFT API Routes for BTC Mining Calculator

提供SLA证明NFT系统的RESTful API端点
Provides RESTful API endpoints for SLA Proof NFT system
"""

import logging
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
import os

# Flask导入
from flask import Blueprint, request, jsonify, session, send_file, abort, url_for
from sqlalchemy import desc, and_, or_
from sqlalchemy.orm import joinedload

# 项目模块导入
from models import (
    SLAMetrics, SLACertificateRecord, MonthlyReport, 
    SLAStatus, NFTMintStatus, SystemPerformanceLog, db
)
from auth import login_required
from decorators import requires_admin_or_owner, log_access_attempt
from security_enhancements import SecurityManager

# SLA系统组件导入
try:
    from sla_collector_engine import get_sla_collector
    from nft_metadata_generator import get_nft_generator  
    from sla_nft_minting_system import get_sla_minting_system
    from blockchain_integration import get_blockchain_integration
except ImportError as e:
    logging.warning(f"SLA system components not fully available: {e}")
    # 创建占位符函数
    def get_sla_collector(): return None
    def get_nft_generator(): return None
    def get_sla_minting_system(): return None
    def get_blockchain_integration(): return None

# 设置日志
logger = logging.getLogger(__name__)

# 创建SLA NFT蓝图
sla_nft_bp = Blueprint('sla_nft', __name__)

# ============================================================================
# SLA NFT查询API端点
# SLA NFT Query API Endpoints
# ============================================================================

@sla_nft_bp.route('/api/sla/certificates', methods=['GET'])
@login_required
@log_access_attempt('sla_certificates_api')
def get_user_certificates():
    """
    获取用户的SLA证书NFT列表
    Get user's SLA certificate NFTs
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 50)
        status_filter = request.args.get('status', None)
        month_year = request.args.get('month_year', None)
        
        # 构建查询
        query = SLACertificateRecord.query
        
        # 添加过滤条件
        if status_filter:
            try:
                status_enum = NFTMintStatus(status_filter)
                query = query.filter(SLACertificateRecord.mint_status == status_enum)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid status: {status_filter}'
                }), 400
        
        if month_year:
            try:
                month_year_int = int(month_year)
                query = query.filter(SLACertificateRecord.month_year == month_year_int)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid month_year format: {month_year}'
                }), 400
        
        # 加载关联的SLA指标数据
        query = query.options(joinedload(SLACertificateRecord.sla_metrics))
        
        # 分页查询
        pagination = query.order_by(desc(SLACertificateRecord.month_year)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        certificates = []
        for cert in pagination.items:
            cert_data = cert.to_dict()
            if cert.sla_metrics:
                cert_data['sla_metrics'] = cert.sla_metrics.to_dict()
            certificates.append(cert_data)
        
        return jsonify({
            'success': True,
            'data': {
                'certificates': certificates,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取用户证书失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取证书列表失败'
        }), 500

@sla_nft_bp.route('/api/sla/certificates/<certificate_id>', methods=['GET'])
@login_required
@log_access_attempt('sla_certificate_detail_api')
def get_certificate_details(certificate_id):
    """
    获取单个SLA证书的详细信息
    Get detailed information for a single SLA certificate
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # 查询证书记录
        certificate = SLACertificateRecord.query.options(
            joinedload(SLACertificateRecord.sla_metrics)
        ).filter_by(id=certificate_id).first()
        
        if not certificate:
            return jsonify({
                'success': False,
                'error': 'Certificate not found'
            }), 404
        
        # 构建详细响应
        cert_data = certificate.to_dict()
        if certificate.sla_metrics:
            cert_data['sla_metrics'] = certificate.sla_metrics.to_dict()
        
        # 添加NFT元数据链接
        if certificate.metadata_ipfs_hash:
            cert_data['metadata_url'] = f"https://ipfs.io/ipfs/{certificate.metadata_ipfs_hash}"
        
        # 添加区块链浏览器链接
        if certificate.transaction_hash:
            # 以太坊主网浏览器链接
            cert_data['etherscan_url'] = f"https://etherscan.io/tx/{certificate.transaction_hash}"
        
        # 添加OpenSea链接（如果已铸造）
        if certificate.mint_status == NFTMintStatus.MINTED and certificate.token_id:
            contract_address = certificate.contract_address or os.environ.get('SLA_NFT_CONTRACT_ADDRESS')
            if contract_address:
                cert_data['opensea_url'] = f"https://opensea.io/assets/ethereum/{contract_address}/{certificate.token_id}"
        
        return jsonify({
            'success': True,
            'data': cert_data
        })
        
    except Exception as e:
        logger.error(f"获取证书详情失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取证书详情失败'
        }), 500

@sla_nft_bp.route('/api/sla/metrics/<int:month_year>', methods=['GET'])
@login_required 
@log_access_attempt('sla_metrics_api')
def get_monthly_sla_metrics(month_year):
    """
    获取指定月份的SLA指标数据
    Get SLA metrics for a specific month
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # 查询SLA指标
        sla_metrics = SLAMetrics.query.filter_by(month_year=month_year).first()
        
        if not sla_metrics:
            return jsonify({
                'success': False,
                'error': f'No SLA metrics found for {month_year}'
            }), 404
        
        # 获取对应的性能日志统计
        year = month_year // 100
        month = month_year % 100
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        performance_logs = SystemPerformanceLog.query.filter(
            and_(
                SystemPerformanceLog.timestamp >= start_date,
                SystemPerformanceLog.timestamp < end_date
            )
        ).all()
        
        # 计算性能统计
        performance_stats = {}
        if performance_logs:
            performance_stats = {
                'total_logs': len(performance_logs),
                'avg_cpu_usage': sum(float(log.cpu_usage_percent) for log in performance_logs) / len(performance_logs),
                'avg_memory_usage': sum(float(log.memory_usage_percent) for log in performance_logs) / len(performance_logs),
                'avg_response_time': sum(log.network_latency_ms for log in performance_logs) / len(performance_logs),
                'max_connections': max((log.active_connections for log in performance_logs), default=0),
                'error_rate_avg': sum(float(log.error_rate) for log in performance_logs) / len(performance_logs)
            }
        
        response_data = sla_metrics.to_dict()
        response_data['performance_stats'] = performance_stats
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        logger.error(f"获取SLA指标失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取SLA指标失败'
        }), 500

# ============================================================================
# NFT验证API接口
# NFT Verification API Interface
# ============================================================================

@sla_nft_bp.route('/api/sla/verify/<certificate_id>', methods=['POST'])
@requires_admin_or_owner
@log_access_attempt('sla_verify_certificate_api')
def verify_certificate(certificate_id):
    """
    验证SLA证书NFT的真实性
    Verify the authenticity of an SLA certificate NFT
    """
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request data required'
            }), 400
        
        # 获取验证参数
        verification_note = data.get('verification_note', '')
        verified_result = data.get('verified', True)
        
        # 查询证书记录
        certificate = SLACertificateRecord.query.filter_by(id=certificate_id).first()
        
        if not certificate:
            return jsonify({
                'success': False,
                'error': 'Certificate not found'
            }), 404
        
        # 更新验证状态
        certificate.is_verified = verified_result
        certificate.verified_by = session.get('user_wallet_address', f'admin_{user_id}')
        certificate.verified_at = datetime.utcnow()
        certificate.verification_note = verification_note
        
        # 如果是首次验证且成功，更新NFT状态
        if verified_result and certificate.mint_status == NFTMintStatus.MINTED:
            certificate.mint_status = NFTMintStatus.VERIFIED
        
        db.session.commit()
        
        # 记录验证活动
        logger.info(f"Certificate {certificate_id} verified by user {user_id}: {verified_result}")
        
        return jsonify({
            'success': True,
            'data': {
                'certificate_id': certificate_id,
                'verified': verified_result,
                'verified_by': certificate.verified_by,
                'verified_at': certificate.verified_at.isoformat(),
                'verification_note': verification_note
            }
        })
        
    except Exception as e:
        logger.error(f"验证证书失败: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': '验证证书失败'
        }), 500

@sla_nft_bp.route('/api/sla/blockchain-verify/<certificate_id>', methods=['POST'])
@login_required
@log_access_attempt('sla_blockchain_verify_api')
def blockchain_verify_certificate(certificate_id):
    """
    通过区块链验证SLA证书NFT
    Verify SLA certificate NFT through blockchain
    """
    try:
        user_id = session.get('user_id')
        
        # 查询证书记录
        certificate = SLACertificateRecord.query.filter_by(id=certificate_id).first()
        
        if not certificate:
            return jsonify({
                'success': False,
                'error': 'Certificate not found'
            }), 404
        
        if not certificate.token_id or not certificate.contract_address:
            return jsonify({
                'success': False,
                'error': 'Certificate not yet minted on blockchain'
            }), 400
        
        # 获取区块链集成组件
        blockchain_integration = get_blockchain_integration()
        if not blockchain_integration:
            return jsonify({
                'success': False,
                'error': 'Blockchain integration not available'
            }), 503
        
        # 通过区块链验证NFT存在性和所有权
        try:
            verification_result = blockchain_integration.verify_nft(
                contract_address=certificate.contract_address,
                token_id=certificate.token_id,
                expected_owner=certificate.recipient_address
            )
            
            if verification_result['exists'] and verification_result['owner_match']:
                # 更新证书为区块链验证状态
                if certificate.sla_metrics:
                    certificate.sla_metrics.verified_by_blockchain = True
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'certificate_id': certificate_id,
                        'blockchain_verified': True,
                        'token_exists': verification_result['exists'],
                        'owner_verified': verification_result['owner_match'],
                        'current_owner': verification_result.get('current_owner'),
                        'verification_timestamp': datetime.utcnow().isoformat()
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Blockchain verification failed',
                    'data': verification_result
                }), 400
                
        except Exception as blockchain_error:
            logger.error(f"区块链验证错误: {blockchain_error}")
            return jsonify({
                'success': False,
                'error': f'Blockchain verification error: {str(blockchain_error)}'
            }), 500
        
    except Exception as e:
        logger.error(f"区块链验证证书失败: {e}")
        return jsonify({
            'success': False,
            'error': '区块链验证失败'
        }), 500

# ============================================================================
# 月度报告下载功能
# Monthly Report Download Functionality
# ============================================================================

@sla_nft_bp.route('/api/sla/reports/<int:month_year>', methods=['GET'])
@login_required
@log_access_attempt('sla_monthly_report_api')
def get_monthly_report(month_year):
    """
    获取月度SLA报告
    Get monthly SLA report
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # 查询月度报告
        monthly_report = MonthlyReport.query.filter_by(month_year=month_year).first()
        
        if not monthly_report:
            return jsonify({
                'success': False,
                'error': f'No monthly report found for {month_year}'
            }), 404
        
        # 构建报告数据
        report_data = {
            'month_year': monthly_report.month_year,
            'generated_at': monthly_report.generated_at.isoformat(),
            'summary': {
                'total_certificates_issued': monthly_report.total_certificates_issued,
                'average_sla_score': float(monthly_report.average_sla_score),
                'highest_sla_score': float(monthly_report.highest_sla_score),
                'lowest_sla_score': float(monthly_report.lowest_sla_score)
            },
            'performance': {
                'total_uptime_hours': monthly_report.total_uptime_hours,
                'total_downtime_minutes': monthly_report.total_downtime_minutes,
                'average_response_time_ms': monthly_report.average_response_time_ms,
                'uptime_percentage': round((monthly_report.total_uptime_hours / (30 * 24)) * 100, 2)
            },
            'errors': {
                'total_errors': monthly_report.total_errors,
                'critical_errors': monthly_report.critical_errors,
                'resolved_errors': monthly_report.resolved_errors,
                'resolution_rate': round((monthly_report.resolved_errors / max(monthly_report.total_errors, 1)) * 100, 2)
            },
            'transparency': {
                'blockchain_verifications': monthly_report.blockchain_verifications,
                'ipfs_uploads': monthly_report.ipfs_uploads,
                'transparency_audit_score': float(monthly_report.transparency_audit_score)
            },
            'blockchain_info': {
                'blockchain_recorded': monthly_report.blockchain_recorded,
                'blockchain_tx_hash': monthly_report.blockchain_tx_hash
            }
        }
        
        # 添加IPFS链接
        if monthly_report.report_ipfs_hash:
            report_data['ipfs_links'] = {
                'full_report': f"https://ipfs.io/ipfs/{monthly_report.report_ipfs_hash}",
                'summary': f"https://ipfs.io/ipfs/{monthly_report.summary_ipfs_hash}" if monthly_report.summary_ipfs_hash else None,
                'charts': f"https://ipfs.io/ipfs/{monthly_report.charts_ipfs_hash}" if monthly_report.charts_ipfs_hash else None
            }
        
        # 添加审计信息
        if monthly_report.audited_by:
            report_data['audit_info'] = {
                'audited_by': monthly_report.audited_by,
                'audit_timestamp': monthly_report.audit_timestamp.isoformat() if monthly_report.audit_timestamp else None,
                'audit_result': monthly_report.audit_result,
                'audit_notes': monthly_report.audit_notes
            }
        
        return jsonify({
            'success': True,
            'data': report_data
        })
        
    except Exception as e:
        logger.error(f"获取月度报告失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取月度报告失败'
        }), 500

@sla_nft_bp.route('/api/sla/reports', methods=['GET'])
@login_required
@log_access_attempt('sla_reports_list_api')
def get_reports_list():
    """
    获取可用的月度报告列表
    Get list of available monthly reports
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 12, type=int), 50)
        
        # 分页查询报告
        pagination = MonthlyReport.query.order_by(desc(MonthlyReport.month_year)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        reports = []
        
        # 如果没有数据，返回示例数据
        if pagination.total == 0:
            from datetime import datetime
            current_date = datetime.utcnow()
            
            # 创建最近3个月的示例报告
            for i in range(3):
                month_offset = i
                demo_month = current_date.month - month_offset
                demo_year = current_date.year
                if demo_month <= 0:
                    demo_month += 12
                    demo_year -= 1
                
                month_year = demo_year * 100 + demo_month
                month_names = {
                    1: 'January', 2: 'February', 3: 'March', 4: 'April',
                    5: 'May', 6: 'June', 7: 'July', 8: 'August',
                    9: 'September', 10: 'October', 11: 'November', 12: 'December'
                }
                
                reports.append({
                    'month_year': month_year,
                    'display_name': f"{month_names.get(demo_month, demo_month)} {demo_year}",
                    'generated_at': datetime.utcnow().isoformat(),
                    'average_sla_score': 99.5 - i * 0.2,
                    'total_certificates': 45 - i * 5,
                    'blockchain_recorded': True,
                    'has_ipfs_report': True,
                    'audit_status': 'audited',
                    'is_demo': True
                })
            
            return jsonify({
                'success': True,
                'data': {
                    'reports': reports,
                    'pagination': {
                        'page': 1,
                        'per_page': per_page,
                        'total': 3,
                        'pages': 1,
                        'has_prev': False,
                        'has_next': False
                    },
                    'demo_mode': True
                }
            })
        
        # 返回真实数据
        for report in pagination.items:
            year = report.month_year // 100
            month = report.month_year % 100
            month_names = {
                1: 'January', 2: 'February', 3: 'March', 4: 'April',
                5: 'May', 6: 'June', 7: 'July', 8: 'August',
                9: 'September', 10: 'October', 11: 'November', 12: 'December'
            }
            
            reports.append({
                'month_year': report.month_year,
                'display_name': f"{month_names.get(month, month)} {year}",
                'generated_at': report.generated_at.isoformat(),
                'average_sla_score': float(report.average_sla_score),
                'total_certificates': report.total_certificates_issued,
                'blockchain_recorded': report.blockchain_recorded,
                'has_ipfs_report': bool(report.report_ipfs_hash),
                'audit_status': 'audited' if report.audit_result is True else 'pending' if report.audit_result is None else 'failed'
            })
        
        return jsonify({
            'success': True,
            'data': {
                'reports': reports,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取报告列表失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取报告列表失败'
        }), 500

# ============================================================================
# SLA状态和统计API
# SLA Status and Statistics API
# ============================================================================

@sla_nft_bp.route('/api/sla/status', methods=['GET'])
@login_required
@log_access_attempt('sla_status_api')
def get_sla_status():
    """
    获取当前SLA系统状态
    Get current SLA system status
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # 获取最新的SLA指标
        latest_metrics = SLAMetrics.query.order_by(desc(SLAMetrics.recorded_at)).first()
        
        # 获取本月的证书统计
        current_date = datetime.utcnow()
        current_month_year = current_date.year * 100 + current_date.month
        
        # 证书统计
        total_certificates = SLACertificateRecord.query.count()
        current_month_certificates = SLACertificateRecord.query.filter_by(
            month_year=current_month_year
        ).count()
        
        # 铸造状态统计
        minting_stats = {}
        for status in NFTMintStatus:
            count = SLACertificateRecord.query.filter_by(mint_status=status).count()
            minting_stats[status.name.lower()] = count
        
        # SLA等级分布
        sla_distribution = {}
        if latest_metrics:
            for status in SLAStatus:
                count = SLAMetrics.query.filter_by(sla_status=status).count()
                sla_distribution[status.name.lower()] = count
        
        # 系统健康状态
        sla_collector = get_sla_collector()
        minting_system = get_sla_minting_system()
        
        system_health = {
            'sla_collector_running': sla_collector.is_running if sla_collector else False,
            'minting_system_running': minting_system.is_running if minting_system else False,
            'database_connected': True,  # 如果能执行查询说明数据库连接正常
            'blockchain_integration': get_blockchain_integration() is not None
        }
        
        response_data = {
            'current_status': {
                'latest_sla_score': float(latest_metrics.composite_sla_score) if latest_metrics else None,
                'latest_sla_status': latest_metrics.sla_status.value if latest_metrics else None,
                'last_recorded': latest_metrics.recorded_at.isoformat() if latest_metrics else None
            },
            'statistics': {
                'total_certificates': total_certificates,
                'current_month_certificates': current_month_certificates,
                'minting_status_distribution': minting_stats,
                'sla_level_distribution': sla_distribution
            },
            'system_health': system_health,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        logger.error(f"获取SLA状态失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取SLA状态失败'
        }), 500

# ============================================================================
# NFT铸造控制API
# NFT Minting Control API
# ============================================================================

@sla_nft_bp.route('/api/sla/mint-request', methods=['POST'])
@login_required
@log_access_attempt('sla_mint_request_api')
def request_nft_mint():
    """
    请求铸造新的SLA证书NFT
    Request minting of new SLA certificate NFT
    """
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request data required'
            }), 400
        
        # 获取请求参数
        month_year = data.get('month_year')
        recipient_address = data.get('recipient_address')
        
        if not month_year or not recipient_address:
            return jsonify({
                'success': False,
                'error': 'month_year and recipient_address are required'
            }), 400
        
        # 验证以太坊地址格式
        if not recipient_address.startswith('0x') or len(recipient_address) != 42:
            return jsonify({
                'success': False,
                'error': 'Invalid Ethereum address format'
            }), 400
        
        # 检查是否已存在证书记录
        existing_cert = SLACertificateRecord.query.filter_by(
            month_year=month_year,
            recipient_address=recipient_address
        ).first()
        
        if existing_cert:
            return jsonify({
                'success': False,
                'error': f'Certificate already exists for {month_year}',
                'data': {
                    'existing_certificate_id': existing_cert.id,
                    'status': existing_cert.mint_status.value
                }
            }), 409
        
        # 检查是否存在对应的SLA指标
        sla_metrics = SLAMetrics.query.filter_by(month_year=month_year).first()
        if not sla_metrics:
            return jsonify({
                'success': False,
                'error': f'No SLA metrics available for {month_year}'
            }), 404
        
        # 创建新的证书请求
        new_certificate = SLACertificateRecord(
            month_year=month_year,
            recipient_address=recipient_address,
            sla_metrics_id=sla_metrics.id,
            mint_status=NFTMintStatus.PENDING
        )
        
        db.session.add(new_certificate)
        db.session.commit()
        
        # 尝试启动铸造流程
        minting_system = get_sla_minting_system()
        if minting_system and minting_system.is_running:
            try:
                # 异步触发铸造
                minting_system.queue_mint_request(new_certificate.id)
                logger.info(f"Mint request queued for certificate {new_certificate.id}")
            except Exception as mint_error:
                logger.warning(f"Failed to queue mint request: {mint_error}")
        
        return jsonify({
            'success': True,
            'data': {
                'certificate_id': new_certificate.id,
                'month_year': month_year,
                'recipient_address': recipient_address,
                'status': NFTMintStatus.PENDING.value,
                'requested_at': new_certificate.requested_at.isoformat(),
                'sla_score': float(sla_metrics.composite_sla_score),
                'sla_status': sla_metrics.sla_status.value
            }
        })
        
    except Exception as e:
        logger.error(f"请求NFT铸造失败: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': '请求NFT铸造失败'
        }), 500

# ============================================================================
# 蓝图注册函数
# Blueprint Registration Function
# ============================================================================

def register_sla_nft_routes(app):
    """
    注册SLA NFT路由到Flask应用
    Register SLA NFT routes to Flask application
    """
    try:
        app.register_blueprint(sla_nft_bp)
        logger.info("✅ SLA NFT routes registered successfully")
    except Exception as e:
        logger.error(f"❌ Failed to register SLA NFT routes: {e}")

# 兼容性导出
__all__ = ['sla_nft_bp', 'register_sla_nft_routes']