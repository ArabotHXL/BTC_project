#!/usr/bin/env python3
"""
SLA NFT自动铸造系统
SLA NFT Automated Minting System

为BTC Mining Calculator平台提供月度SLA证明NFT自动铸造功能
Provides automated monthly SLA proof NFT minting functionality for BTC Mining Calculator platform
"""

import logging
import json
import time
import schedule
import threading
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
import os
import hashlib
import base64

# Flask和数据库导入
from flask import current_app

# 项目模块导入
from models import (
    SLAMetrics, SLACertificateRecord, MonthlyReport, 
    SLAStatus, NFTMintStatus, db
)

# SLA系统组件导入
from sla_collector_engine import get_sla_collector
from nft_metadata_generator import get_nft_generator

# 区块链集成导入
from blockchain_integration import get_blockchain_integration

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SLANFTMintingSystem:
    """SLA NFT自动铸造系统主类"""
    
    def __init__(self):
        """初始化铸造系统"""
        self.is_running = False
        self.minting_thread = None
        
        # 系统组件
        self.sla_collector = None
        self.nft_generator = None
        self.blockchain_integration = None
        
        # SLA NFT合约配置（需要部署后更新）
        self.sla_nft_contract_address = os.environ.get('SLA_NFT_CONTRACT_ADDRESS')
        self.sla_nft_contract_abi = self._load_sla_nft_contract_abi()
        
        # 铸造配置
        self.minting_config = {
            'auto_mint_enabled': os.environ.get('SLA_AUTO_MINT_ENABLED', 'true').lower() == 'true',
            'mint_day': int(os.environ.get('SLA_MINT_DAY', '3')),  # 每月3号铸造
            'mint_hour': int(os.environ.get('SLA_MINT_HOUR', '8')),  # 上午8点铸造
            'retry_attempts': int(os.environ.get('SLA_MINT_RETRY_ATTEMPTS', '3')),
            'retry_interval': int(os.environ.get('SLA_MINT_RETRY_INTERVAL', '3600')),  # 1小时
            'batch_size': int(os.environ.get('SLA_MINT_BATCH_SIZE', '10')),  # 批量铸造大小
            'gas_price_multiplier': float(os.environ.get('SLA_GAS_PRICE_MULTIPLIER', '1.2'))
        }
        
        # 铸造统计
        self.minting_stats = {
            'total_minted': 0,
            'successful_mints': 0,
            'failed_mints': 0,
            'last_mint_time': None,
            'current_month_mints': 0,
            'start_time': datetime.utcnow()
        }
        
        logger.info("SLA NFT Minting System initialized")
    
    def start_minting_service(self):
        """启动NFT铸造服务"""
        if self.is_running:
            logger.warning("SLA NFT minting service already running")
            return
        
        try:
            # 初始化组件
            self._initialize_components()
            
            # 启动铸造服务
            self.is_running = True
            
            # 设置调度任务
            self._setup_minting_schedule()
            
            # 启动监控线程
            self.minting_thread = threading.Thread(
                target=self._minting_service_loop,
                daemon=True
            )
            self.minting_thread.start()
            
            logger.info("SLA NFT minting service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start SLA NFT minting service: {e}")
            self.is_running = False
    
    def stop_minting_service(self):
        """停止NFT铸造服务"""
        self.is_running = False
        if self.minting_thread:
            self.minting_thread.join(timeout=10)
        
        # 清除调度任务
        schedule.clear()
        
        logger.info("SLA NFT minting service stopped")
    
    def _initialize_components(self):
        """初始化系统组件"""
        try:
            # 初始化SLA收集器
            self.sla_collector = get_sla_collector()
            
            # 初始化NFT元数据生成器
            self.nft_generator = get_nft_generator()
            
            # 初始化区块链集成
            self.blockchain_integration = get_blockchain_integration()
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _setup_minting_schedule(self):
        """设置铸造调度任务"""
        if not self.minting_config['auto_mint_enabled']:
            logger.info("Auto-minting is disabled")
            return
        
        # 每月定期铸造任务
        mint_time = f"{self.minting_config['mint_hour']:02d}:00"
        schedule.every().month.at(mint_time).do(self._scheduled_monthly_mint)
        
        # 每日检查未完成的铸造任务
        schedule.every().day.at("09:00").do(self._check_pending_mints)
        
        # 每小时检查失败的铸造并重试
        schedule.every().hour.do(self._retry_failed_mints)
        
        # 每天更新铸造统计
        schedule.every().day.at("23:55").do(self._update_minting_stats)
        
        logger.info(f"Minting schedule configured: monthly mint at {mint_time}")
    
    def _minting_service_loop(self):
        """铸造服务主循环"""
        while self.is_running:
            try:
                # 运行调度任务
                schedule.run_pending()
                
                # 检查是否需要紧急铸造
                self._check_emergency_minting()
                
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"Error in minting service loop: {e}")
                time.sleep(300)  # 出错后等待5分钟
    
    def _scheduled_monthly_mint(self):
        """计划的月度铸造任务"""
        logger.info("Starting scheduled monthly SLA NFT minting...")
        
        try:
            # 获取上个月的SLA数据
            last_month_data = self._get_last_month_sla_data()
            
            if not last_month_data:
                logger.warning("No SLA data found for monthly minting")
                return
            
            # 获取需要铸造的用户列表
            recipients = self._get_eligible_recipients(last_month_data['month_year'])
            
            if not recipients:
                logger.info("No eligible recipients for monthly minting")
                return
            
            # 批量铸造NFT
            minting_results = self._batch_mint_nfts(last_month_data, recipients)
            
            logger.info(f"Monthly minting completed: {minting_results}")
            
        except Exception as e:
            logger.error(f"Scheduled monthly mint failed: {e}")
    
    def _get_last_month_sla_data(self) -> Optional[Dict]:
        """获取上个月的SLA数据"""
        try:
            from flask import current_app
            with current_app.app_context():
                # 计算上个月的月年值
                today = date.today()
                if today.month == 1:
                    last_month = 12
                    year = today.year - 1
                else:
                    last_month = today.month - 1
                    year = today.year
                
                month_year = year * 100 + last_month
                
                # 查询SLA指标数据
                sla_metrics = SLAMetrics.query.filter_by(month_year=month_year).first()
                
                if not sla_metrics:
                    logger.warning(f"No SLA metrics found for {month_year}")
                    return None
                
                # 查询月度报告
                monthly_report = MonthlyReport.query.filter_by(month_year=month_year).first()
                
                return {
                    'month_year': month_year,
                    'sla_metrics': sla_metrics,
                    'monthly_report': monthly_report,
                    'year': year,
                    'month': last_month
                }
                
        except Exception as e:
            logger.error(f"Failed to get last month SLA data: {e}")
            return None
    
    def _get_eligible_recipients(self, month_year: int) -> List[Dict]:
        """获取符合条件的NFT接收者"""
        try:
            from flask import current_app
            with current_app.app_context():
                # 获取所有活跃用户（这里需要根据实际用户管理系统调整）
                # 暂时使用模拟用户列表
                recipients = [
                    {
                        'address': os.environ.get('SLA_DEFAULT_RECIPIENT_ADDRESS', '0x1234567890123456789012345678901234567890'),
                        'user_id': 1,
                        'username': 'default_user'
                    }
                ]
                
                # 检查是否已经铸造过
                existing_certificates = SLACertificateRecord.query.filter_by(
                    month_year=month_year
                ).all()
                
                existing_addresses = {cert.recipient_address for cert in existing_certificates}
                
                # 过滤已经铸造过的用户
                eligible_recipients = [
                    recipient for recipient in recipients 
                    if recipient['address'] not in existing_addresses
                ]
                
                logger.info(f"Found {len(eligible_recipients)} eligible recipients for {month_year}")
                
                return eligible_recipients
                
        except Exception as e:
            logger.error(f"Failed to get eligible recipients: {e}")
            return []
    
    def _batch_mint_nfts(self, sla_data: Dict, recipients: List[Dict]) -> Dict:
        """批量铸造NFT"""
        results = {
            'successful': 0,
            'failed': 0,
            'total': len(recipients),
            'details': []
        }
        
        try:
            from flask import current_app
            with current_app.app_context():
                for recipient in recipients:
                    try:
                        # 单个NFT铸造
                        mint_result = self._mint_single_nft(
                            sla_data['sla_metrics'],
                            sla_data['month_year'],
                            recipient['address'],
                            recipient
                        )
                        
                        if mint_result['success']:
                            results['successful'] += 1
                        else:
                            results['failed'] += 1
                        
                        results['details'].append({
                            'recipient': recipient['address'],
                            'success': mint_result['success'],
                            'message': mint_result.get('message', ''),
                            'transaction_hash': mint_result.get('transaction_hash'),
                            'token_id': mint_result.get('token_id')
                        })
                        
                        # 避免连续请求过快
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Failed to mint NFT for {recipient['address']}: {e}")
                        results['failed'] += 1
                        results['details'].append({
                            'recipient': recipient['address'],
                            'success': False,
                            'message': f"Exception: {str(e)}"
                        })
                
                # 更新统计
                self.minting_stats['successful_mints'] += results['successful']
                self.minting_stats['failed_mints'] += results['failed']
                self.minting_stats['total_minted'] += results['total']
                self.minting_stats['last_mint_time'] = datetime.utcnow()
                
                return results
                
        except Exception as e:
            logger.error(f"Batch minting failed: {e}")
            return results
    
    def _mint_single_nft(self, sla_metrics: SLAMetrics, month_year: int, 
                        recipient_address: str, recipient_info: Dict) -> Dict:
        """铸造单个NFT"""
        try:
            from flask import current_app
            with current_app.app_context():
                # 生成证书ID
                certificate_id = self._generate_certificate_id(month_year, recipient_address)
                
                # 生成NFT元数据
                metadata = self.nft_generator.generate_metadata(
                    sla_metrics, month_year, recipient_address, certificate_id
                )
                
                # 上传元数据到IPFS
                metadata_ipfs_result = self._upload_metadata_to_ipfs(metadata)
                
                if not metadata_ipfs_result['success']:
                    return {
                        'success': False,
                        'message': f"Failed to upload metadata to IPFS: {metadata_ipfs_result['error']}"
                    }
                
                # 创建证书记录
                certificate_record = SLACertificateRecord(
                    month_year=month_year,
                    recipient_address=recipient_address,
                    sla_metrics_id=sla_metrics.id,
                    metadata_ipfs_hash=metadata_ipfs_result['ipfs_hash'],
                    mint_status=NFTMintStatus.PENDING
                )
                
                db.session.add(certificate_record)
                db.session.flush()  # 获取ID
                
                # 调用智能合约铸造NFT
                mint_result = self._mint_nft_on_blockchain(
                    certificate_record.id,
                    recipient_address,
                    metadata_ipfs_result['ipfs_hash'],
                    sla_metrics
                )
                
                if mint_result['success']:
                    # 更新证书记录
                    certificate_record.update_mint_status(
                        NFTMintStatus.MINTED,
                        token_id=mint_result['token_id'],
                        transaction_hash=mint_result['transaction_hash'],
                        contract_address=self.sla_nft_contract_address,
                        block_number=mint_result.get('block_number')
                    )
                    
                    db.session.commit()
                    
                    logger.info(f"Successfully minted SLA NFT for {recipient_address}: "
                               f"Token ID {mint_result['token_id']}")
                    
                    return {
                        'success': True,
                        'message': 'NFT minted successfully',
                        'token_id': mint_result['token_id'],
                        'transaction_hash': mint_result['transaction_hash'],
                        'certificate_id': certificate_record.id
                    }
                else:
                    # 更新失败状态
                    certificate_record.update_mint_status(
                        NFTMintStatus.FAILED,
                        error_message=mint_result['error']
                    )
                    
                    db.session.commit()
                    
                    return {
                        'success': False,
                        'message': f"Blockchain minting failed: {mint_result['error']}"
                    }
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Single NFT mint failed: {e}")
            return {
                'success': False,
                'message': f"Exception during minting: {str(e)}"
            }
    
    def _upload_metadata_to_ipfs(self, metadata: Dict) -> Dict:
        """上传元数据到IPFS"""
        try:
            if not self.blockchain_integration:
                return {'success': False, 'error': 'Blockchain integration not initialized'}
            
            # 将元数据转换为JSON字符串
            metadata_json = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))
            
            # 上传到IPFS
            ipfs_result = self.blockchain_integration.upload_to_ipfs(
                metadata_json.encode('utf-8'),
                f"sla_certificate_metadata_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            if ipfs_result and 'IpfsHash' in ipfs_result:
                return {
                    'success': True,
                    'ipfs_hash': ipfs_result['IpfsHash'],
                    'ipfs_url': f"https://gateway.pinata.cloud/ipfs/{ipfs_result['IpfsHash']}"
                }
            else:
                return {
                    'success': False,
                    'error': 'IPFS upload failed - no hash returned'
                }
                
        except Exception as e:
            logger.error(f"IPFS upload failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _mint_nft_on_blockchain(self, certificate_id: int, recipient_address: str, 
                              metadata_ipfs_hash: str, sla_metrics: SLAMetrics) -> Dict:
        """在区块链上铸造NFT"""
        try:
            if not self.blockchain_integration or not self.blockchain_integration.w3:
                return {'success': False, 'error': 'Web3 connection not available'}
            
            if not self.sla_nft_contract_address:
                return {'success': False, 'error': 'SLA NFT contract address not configured'}
            
            # 创建合约实例
            contract = self.blockchain_integration.w3.eth.contract(
                address=self.sla_nft_contract_address,
                abi=self.sla_nft_contract_abi
            )
            
            # 准备铸造参数
            token_uri = f"https://gateway.pinata.cloud/ipfs/{metadata_ipfs_hash}"
            
            # 构建SLA指标结构
            sla_data = [
                int(float(sla_metrics.composite_sla_score) * 100),  # 评分 * 100（避免小数）
                int(float(sla_metrics.uptime_percentage) * 100),
                int(float(sla_metrics.availability_percentage) * 100),
                sla_metrics.avg_response_time_ms,
                int(float(sla_metrics.data_accuracy_percentage) * 100),
                int(float(sla_metrics.api_success_rate) * 100),
                int(float(sla_metrics.transparency_score) * 100),
                sla_metrics.blockchain_verifications,
                sla_metrics.ipfs_uploads,
                sla_metrics.error_count,
                sla_metrics.downtime_minutes
            ]
            
            # 构建交易
            transaction = contract.functions.mintSLACertificate(
                recipient_address,
                sla_metrics.month_year,
                sla_data,
                token_uri
            ).build_transaction({
                'from': self.blockchain_integration.account.address,
                'gas': 500000,  # 预估gas限制
                'gasPrice': int(self.blockchain_integration.w3.eth.gas_price * 
                              self.minting_config['gas_price_multiplier']),
                'nonce': self.blockchain_integration.w3.eth.get_transaction_count(
                    self.blockchain_integration.account.address
                )
            })
            
            # 签名交易
            signed_txn = self.blockchain_integration.w3.eth.account.sign_transaction(
                transaction, 
                private_key=self.blockchain_integration.account.key
            )
            
            # 发送交易
            tx_hash = self.blockchain_integration.w3.eth.send_raw_transaction(
                signed_txn.rawTransaction
            )
            
            # 等待交易确认
            tx_receipt = self.blockchain_integration.w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=300
            )
            
            # 解析事件获取Token ID
            token_id = None
            try:
                # 查找SLACertificateMinted事件
                certificate_events = contract.events.SLACertificateMinted().process_receipt(tx_receipt)
                if certificate_events:
                    token_id = certificate_events[0]['args']['tokenId']
            except:
                # 如果事件解析失败，使用合约调用获取最新token ID
                token_id = contract.functions.totalSupply().call()
            
            return {
                'success': True,
                'transaction_hash': tx_hash.hex(),
                'block_number': tx_receipt['blockNumber'],
                'token_id': str(token_id) if token_id else str(certificate_id),
                'gas_used': tx_receipt['gasUsed']
            }
            
        except Exception as e:
            logger.error(f"Blockchain NFT minting failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _load_sla_nft_contract_abi(self) -> List:
        """加载SLA NFT合约ABI"""
        # SLA NFT合约ABI（基于我们之前创建的合约）
        return [
            {
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "monthYear", "type": "uint256"},
                    {"name": "slaData", "type": "uint256[11]"},
                    {"name": "tokenURI", "type": "string"}
                ],
                "name": "mintSLACertificate",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "to", "type": "address"},
                    {"indexed": True, "name": "tokenId", "type": "uint256"},
                    {"indexed": True, "name": "monthYear", "type": "uint256"},
                    {"indexed": False, "name": "slaScore", "type": "uint256"},
                    {"indexed": False, "name": "tokenURI", "type": "string"}
                ],
                "name": "SLACertificateMinted",
                "type": "event"
            },
            {
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            # 标准ERC-721函数
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "tokenURI",
                "outputs": [{"name": "", "type": "string"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "ownerOf",
                "outputs": [{"name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def _generate_certificate_id(self, month_year: int, recipient_address: str) -> str:
        """生成证书ID"""
        # 使用月年和接收者地址生成唯一ID
        data = f"{month_year}_{recipient_address}_{datetime.utcnow().timestamp()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _check_pending_mints(self):
        """检查待处理的铸造任务"""
        try:
            from flask import current_app
            with current_app.app_context():
                # 查找状态为PENDING超过24小时的记录
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                pending_certificates = SLACertificateRecord.query.filter(
                    SLACertificateRecord.mint_status == NFTMintStatus.PENDING,
                    SLACertificateRecord.requested_at < cutoff_time
                ).all()
                
                if pending_certificates:
                    logger.warning(f"Found {len(pending_certificates)} pending certificates older than 24h")
                    
                    # 尝试重新处理
                    for cert in pending_certificates[:5]:  # 限制每次处理5个
                        self._retry_certificate_minting(cert)
                
        except Exception as e:
            logger.error(f"Failed to check pending mints: {e}")
    
    def _retry_failed_mints(self):
        """重试失败的铸造"""
        try:
            from flask import current_app
            with current_app.app_context():
                # 查找失败的铸造记录
                failed_certificates = SLACertificateRecord.query.filter(
                    SLACertificateRecord.mint_status == NFTMintStatus.FAILED,
                    SLACertificateRecord.retry_count < self.minting_config['retry_attempts']
                ).limit(3).all()  # 每次最多重试3个
                
                for cert in failed_certificates:
                    self._retry_certificate_minting(cert)
                
        except Exception as e:
            logger.error(f"Failed to retry failed mints: {e}")
    
    def _retry_certificate_minting(self, certificate: SLACertificateRecord):
        """重试证书铸造"""
        try:
            from flask import current_app
            with current_app.app_context():
                # 增加重试计数
                certificate.retry_count += 1
                certificate.mint_status = NFTMintStatus.MINTING
                
                db.session.commit()
                
                # 重新获取SLA数据
                if not certificate.sla_metrics:
                    logger.error(f"No SLA metrics found for certificate {certificate.id}")
                    return
                
                # 重新铸造
                mint_result = self._mint_single_nft(
                    certificate.sla_metrics,
                    certificate.month_year,
                    certificate.recipient_address,
                    {'address': certificate.recipient_address}
                )
                
                if mint_result['success']:
                    logger.info(f"Successfully retried minting for certificate {certificate.id}")
                else:
                    logger.warning(f"Retry failed for certificate {certificate.id}: {mint_result['message']}")
                
        except Exception as e:
            logger.error(f"Failed to retry certificate minting: {e}")
    
    def _check_emergency_minting(self):
        """检查是否需要紧急铸造"""
        try:
            # 检查是否有紧急铸造请求（可以通过环境变量或数据库标志控制）
            emergency_mint = os.environ.get('SLA_EMERGENCY_MINT', 'false').lower() == 'true'
            
            if emergency_mint:
                logger.info("Emergency minting requested")
                # 清除环境变量标志
                os.environ['SLA_EMERGENCY_MINT'] = 'false'
                
                # 执行紧急铸造
                self._emergency_mint_current_month()
                
        except Exception as e:
            logger.error(f"Emergency minting check failed: {e}")
    
    def _emergency_mint_current_month(self):
        """紧急铸造当前月份"""
        try:
            from flask import current_app
            with current_app.app_context():
                # 获取当前月份的SLA数据
                today = date.today()
                month_year = today.year * 100 + today.month
                
                sla_metrics = SLAMetrics.query.filter_by(month_year=month_year).first()
                
                if not sla_metrics:
                    # 生成当前月的SLA数据
                    current_status = self.sla_collector.get_current_sla_status()
                    
                    # 创建临时SLA指标（基于当前状态）
                    sla_metrics = SLAMetrics(
                        month_year=month_year,
                        uptime_percentage=current_status.get('current_uptime', 99.0),
                        availability_percentage=current_status.get('current_availability', 98.0),
                        avg_response_time_ms=current_status.get('current_response_time', 200),
                        max_response_time_ms=500,
                        min_response_time_ms=50,
                        data_accuracy_percentage=95.0,
                        api_success_rate=96.0,
                        transparency_score=95.0,
                        blockchain_verifications=10,
                        ipfs_uploads=5,
                        error_count=1,
                        critical_error_count=0,
                        downtime_minutes=10,
                        feature_completion_rate=98.0
                    )
                    
                    db.session.add(sla_metrics)
                    db.session.commit()
                
                # 获取接收者并铸造
                recipients = self._get_eligible_recipients(month_year)
                
                if recipients:
                    sla_data = {
                        'month_year': month_year,
                        'sla_metrics': sla_metrics,
                        'monthly_report': None,
                        'year': today.year,
                        'month': today.month
                    }
                    
                    results = self._batch_mint_nfts(sla_data, recipients)
                    logger.info(f"Emergency minting completed: {results}")
                
        except Exception as e:
            logger.error(f"Emergency minting failed: {e}")
    
    def _update_minting_stats(self):
        """更新铸造统计"""
        try:
            from flask import current_app
            with current_app.app_context():
                # 查询数据库中的统计信息
                today = date.today()
                month_year = today.year * 100 + today.month
                
                current_month_mints = SLACertificateRecord.query.filter_by(
                    month_year=month_year
                ).count()
                
                total_minted = SLACertificateRecord.query.filter(
                    SLACertificateRecord.mint_status == NFTMintStatus.MINTED
                ).count()
                
                total_failed = SLACertificateRecord.query.filter(
                    SLACertificateRecord.mint_status == NFTMintStatus.FAILED
                ).count()
                
                # 更新统计
                self.minting_stats.update({
                    'current_month_mints': current_month_mints,
                    'total_minted': total_minted,
                    'failed_mints': total_failed
                })
                
                logger.info(f"Updated minting stats: {self.minting_stats}")
                
        except Exception as e:
            logger.error(f"Failed to update minting stats: {e}")
    
    def get_minting_status(self) -> Dict:
        """获取铸造系统状态"""
        return {
            'is_running': self.is_running,
            'auto_mint_enabled': self.minting_config['auto_mint_enabled'],
            'contract_address': self.sla_nft_contract_address,
            'stats': self.minting_stats.copy(),
            'config': self.minting_config.copy(),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def force_mint_for_address(self, recipient_address: str, month_year: int = None) -> Dict:
        """强制为指定地址铸造NFT"""
        try:
            from flask import current_app
            with current_app.app_context():
                if not month_year:
                    # 使用上个月
                    today = date.today()
                    if today.month == 1:
                        month_year = (today.year - 1) * 100 + 12
                    else:
                        month_year = today.year * 100 + (today.month - 1)
                
                # 获取SLA数据
                sla_metrics = SLAMetrics.query.filter_by(month_year=month_year).first()
                
                if not sla_metrics:
                    return {
                        'success': False,
                        'message': f'No SLA metrics found for {month_year}'
                    }
                
                # 检查是否已经铸造
                existing_cert = SLACertificateRecord.query.filter_by(
                    month_year=month_year,
                    recipient_address=recipient_address
                ).first()
                
                if existing_cert and existing_cert.mint_status == NFTMintStatus.MINTED:
                    return {
                        'success': False,
                        'message': 'NFT already minted for this address and month'
                    }
                
                # 铸造NFT
                recipient_info = {'address': recipient_address}
                result = self._mint_single_nft(sla_metrics, month_year, recipient_address, recipient_info)
                
                return result
                
        except Exception as e:
            logger.error(f"Force mint failed: {e}")
            return {
                'success': False,
                'message': f'Exception: {str(e)}'
            }

# 全局铸造系统实例
sla_minting_system = None

def initialize_sla_minting_system():
    """初始化全局SLA铸造系统"""
    global sla_minting_system
    if sla_minting_system is None:
        sla_minting_system = SLANFTMintingSystem()
        sla_minting_system.start_minting_service()
        logger.info("Global SLA NFT minting system initialized and started")
    return sla_minting_system

def get_sla_minting_system() -> SLANFTMintingSystem:
    """获取SLA铸造系统实例"""
    # Note: sla_minting_system is a module-level global that may be assigned by initialize_sla_minting_system
    if sla_minting_system is None:
        return initialize_sla_minting_system()
    return sla_minting_system

if __name__ == "__main__":
    # 测试运行
    minting_system = SLANFTMintingSystem()
    minting_system.start_minting_service()
    
    try:
        while True:
            time.sleep(30)
            status = minting_system.get_minting_status()
            print(f"Minting System Status: {status}")
    except KeyboardInterrupt:
        minting_system.stop_minting_service()
        print("SLA NFT Minting System stopped")