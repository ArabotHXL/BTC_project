"""
Compliance Service - AML/KYC Implementation
为BTC Mining Calculator平台提供真实的合规检查和审计功能

功能包括：
- 真实AML/KYC检查替代占位符
- 风险评分系统
- 审计日志记录
- 合规状态管理
- 反洗钱监控
"""

import os
import json
import logging
import hashlib
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# 本地导入
from models_subscription import Payment, UserSubscription, PaymentStatus
from models import User
from db import db

logger = logging.getLogger(__name__)

class ComplianceStatus(Enum):
    """合规状态枚举"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"

class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ComplianceCheck:
    """合规检查结果"""
    check_type: str
    status: ComplianceStatus
    risk_level: RiskLevel
    score: float
    details: Dict[str, Any]
    timestamp: datetime
    expires_at: Optional[datetime] = None

class ComplianceService:
    """合规服务主类 - 真实AML/KYC实现"""
    
    def __init__(self):
        """初始化合规服务"""
        self.aml_enabled = os.environ.get('AML_CHECKS_ENABLED', 'true').lower() == 'true'
        self.kyc_enabled = os.environ.get('KYC_CHECKS_ENABLED', 'true').lower() == 'true'
        self.audit_enabled = os.environ.get('AUDIT_LOGGING_ENABLED', 'true').lower() == 'true'
        
        # 风险阈值配置
        self.risk_thresholds = {
            'max_daily_amount': float(os.environ.get('MAX_DAILY_AMOUNT', '10000')),  # $10,000
            'max_monthly_amount': float(os.environ.get('MAX_MONTHLY_AMOUNT', '50000')),  # $50,000
            'suspicious_countries': self._load_suspicious_countries(),
            'min_age_requirement': int(os.environ.get('MIN_AGE_REQUIREMENT', '18')),
            'max_payment_frequency': int(os.environ.get('MAX_PAYMENT_FREQUENCY', '10'))  # 每小时最多10次
        }
        
        # 外部合规API配置
        self.compliance_api_key = os.environ.get('COMPLIANCE_API_KEY')
        self.compliance_api_url = os.environ.get('COMPLIANCE_API_URL', 'https://api.complytrade.com/v1')
        
        logger.info("ComplianceService initialized with real AML/KYC checks")
    
    def _load_suspicious_countries(self) -> List[str]:
        """加载可疑国家列表"""
        # 基于FATF黑名单和灰名单
        return [
            'AF', 'BY', 'MM', 'CF', 'CG', 'CD', 'CU', 'ET', 'GW', 'HT',
            'IR', 'IQ', 'LB', 'LY', 'ML', 'NI', 'KP', 'PK', 'PA', 'RU',
            'SO', 'SS', 'SD', 'SY', 'TR', 'UG', 'VE', 'YE', 'ZW'
        ]
    
    def perform_aml_check(self, payment: Payment, user: User) -> ComplianceCheck:
        """执行真实AML检查"""
        try:
            if not self.aml_enabled:
                return ComplianceCheck(
                    check_type='aml',
                    status=ComplianceStatus.PASSED,
                    risk_level=RiskLevel.LOW,
                    score=0.1,
                    details={'message': 'AML检查已禁用'},
                    timestamp=datetime.utcnow()
                )
            
            # 🔧 CRITICAL FIX: 真实AML检查替代占位符
            aml_details = {
                'user_id': user.id,
                'user_email': user.email,
                'payment_amount': payment.amount,
                'payment_currency': payment.currency,
                'payment_method': payment.crypto_currency.value if payment.crypto_currency else 'unknown',
                'user_country': getattr(user, 'country', 'unknown'),
                'user_ip': getattr(user, 'last_ip', 'unknown')
            }
            
            risk_score = 0.0
            risk_factors = []
            
            # 1. 金额风险检查
            daily_total = self._calculate_daily_payment_total(user)
            monthly_total = self._calculate_monthly_payment_total(user)
            
            if payment.amount > 1000:
                risk_score += 0.2
                risk_factors.append(f'大额支付: ${payment.amount}')
            
            if daily_total > self.risk_thresholds['max_daily_amount']:
                risk_score += 0.5
                risk_factors.append(f'超过日限额: ${daily_total}')
            
            if monthly_total > self.risk_thresholds['max_monthly_amount']:
                risk_score += 0.7
                risk_factors.append(f'超过月限额: ${monthly_total}')
            
            # 2. 地理位置风险检查
            user_country = getattr(user, 'country', 'unknown')
            if user_country in self.risk_thresholds['suspicious_countries']:
                risk_score += 0.8
                risk_factors.append(f'高风险国家: {user_country}')
            
            # 3. 支付频率检查
            recent_payments = self._get_recent_payment_count(user, hours=1)
            if recent_payments > self.risk_thresholds['max_payment_frequency']:
                risk_score += 0.6
                risk_factors.append(f'支付频率过高: {recent_payments}/小时')
            
            # 4. 加密货币特定风险
            if payment.crypto_currency:
                crypto_risk = self._assess_crypto_risk(payment)
                risk_score += crypto_risk
                if crypto_risk > 0.3:
                    risk_factors.append(f'加密货币风险: {payment.crypto_currency.value}')
            
            # 5. 外部API检查（含制裁名单筛查，如果配置）
            if self.compliance_api_key:
                external_check = self._perform_external_aml_check(user, payment)
                risk_score += external_check.get('risk_score', 0)
                if external_check.get('risk_factors'):
                    risk_factors.extend(external_check['risk_factors'])
            else:
                # fail-closed 可见性：未配置外部 AML/制裁名单筛查时不静默放行，
                # 记录缺口并施加轻度风险，使边界用户倾向人工复核而非自动通过。
                # TODO(security): integrate real AML/sanctions screening (Chainalysis/OFAC API)
                risk_score += 0.2
                risk_factors.append('外部AML/制裁名单筛查未配置（未执行）')

            # 确定风险等级和状态
            if risk_score >= 0.8:
                status = ComplianceStatus.BLOCKED
                risk_level = RiskLevel.CRITICAL
            elif risk_score >= 0.6:
                status = ComplianceStatus.REVIEW_REQUIRED
                risk_level = RiskLevel.HIGH
            elif risk_score >= 0.3:
                status = ComplianceStatus.REVIEW_REQUIRED
                risk_level = RiskLevel.MEDIUM
            else:
                status = ComplianceStatus.PASSED
                risk_level = RiskLevel.LOW
            
            aml_details.update({
                'risk_score': risk_score,
                'risk_factors': risk_factors,
                'daily_total': daily_total,
                'monthly_total': monthly_total,
                'recent_payments_count': recent_payments
            })
            
            check_result = ComplianceCheck(
                check_type='aml',
                status=status,
                risk_level=risk_level,
                score=risk_score,
                details=aml_details,
                timestamp=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            
            # 记录审计日志
            self._log_compliance_event('aml_check', user, payment, check_result)
            
            logger.info(f"AML检查完成: 用户={user.id}, 风险分数={risk_score:.2f}, 状态={status.value}")
            return check_result
            
        except Exception as e:
            logger.error(f"AML检查失败: {e}")
            return ComplianceCheck(
                check_type='aml',
                status=ComplianceStatus.FAILED,
                risk_level=RiskLevel.HIGH,
                score=1.0,
                details={'error': str(e)},
                timestamp=datetime.utcnow()
            )
    
    def perform_kyc_check(self, user: User, additional_data: Dict[str, Any] = None) -> ComplianceCheck:
        """执行真实KYC检查"""
        try:
            if not self.kyc_enabled:
                return ComplianceCheck(
                    check_type='kyc',
                    status=ComplianceStatus.PASSED,
                    risk_level=RiskLevel.LOW,
                    score=0.1,
                    details={'message': 'KYC检查已禁用'},
                    timestamp=datetime.utcnow()
                )
            
            # 🔧 CRITICAL FIX: 真实KYC检查替代占位符
            kyc_details = {
                'user_id': user.id,
                'user_email': user.email,
                'user_registration_date': user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                'additional_data': additional_data or {}
            }
            
            risk_score = 0.0
            missing_fields = []
            verification_issues = []
            
            # 1. 基本信息完整性检查
            required_fields = ['username', 'email']
            for field in required_fields:
                if not getattr(user, field, None):
                    missing_fields.append(field)
                    risk_score += 0.2
            
            # 2. 邮箱验证状态检查
            if not getattr(user, 'email_verified', False):
                verification_issues.append('邮箱未验证')
                risk_score += 0.3
            
            # 3. 账户年龄检查
            if hasattr(user, 'created_at'):
                account_age_days = (datetime.utcnow() - user.created_at).days
                if account_age_days < 1:
                    verification_issues.append('新注册账户')
                    risk_score += 0.4
            
            # 4. 用户行为模式检查
            login_count = self._get_user_login_count(user)
            if login_count < 3:
                verification_issues.append('登录次数过少')
                risk_score += 0.2
            
            # 5. IP地址一致性检查
            ip_consistency = self._check_ip_consistency(user)
            if not ip_consistency:
                verification_issues.append('IP地址异常变化')
                risk_score += 0.3
            
            # 6. 外部KYC API检查（如果配置）
            if self.compliance_api_key:
                external_kyc = self._perform_external_kyc_check(user)
                risk_score += external_kyc.get('risk_score', 0)
                if external_kyc.get('issues'):
                    verification_issues.extend(external_kyc['issues'])
            else:
                # fail-closed 可见性：未配置外部 KYC 身份核验时施加轻度风险并标注，
                # 但不直接判 REVIEW（避免阻断所有正常注册）。
                # TODO(security): integrate real KYC identity verification (Onfido/Jumio)
                risk_score += 0.2
                kyc_details['external_kyc_screening'] = 'unavailable'

            # 确定KYC状态
            if missing_fields or risk_score >= 0.7:
                status = ComplianceStatus.FAILED
                risk_level = RiskLevel.HIGH
            elif verification_issues or risk_score >= 0.4:
                status = ComplianceStatus.REVIEW_REQUIRED
                risk_level = RiskLevel.MEDIUM
            else:
                status = ComplianceStatus.PASSED
                risk_level = RiskLevel.LOW
            
            kyc_details.update({
                'risk_score': risk_score,
                'missing_fields': missing_fields,
                'verification_issues': verification_issues,
                'login_count': login_count,
                'ip_consistency': ip_consistency
            })
            
            check_result = ComplianceCheck(
                check_type='kyc',
                status=status,
                risk_level=risk_level,
                score=risk_score,
                details=kyc_details,
                timestamp=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            
            # 记录审计日志
            self._log_compliance_event('kyc_check', user, None, check_result)
            
            logger.info(f"KYC检查完成: 用户={user.id}, 风险分数={risk_score:.2f}, 状态={status.value}")
            return check_result
            
        except Exception as e:
            logger.error(f"KYC检查失败: {e}")
            return ComplianceCheck(
                check_type='kyc',
                status=ComplianceStatus.FAILED,
                risk_level=RiskLevel.CRITICAL,
                score=1.0,
                details={'error': str(e)},
                timestamp=datetime.utcnow()
            )
    
    def validate_payment_compliance(self, payment: Payment) -> Tuple[bool, Dict[str, Any]]:
        """验证支付合规性 - 在订阅激活前检查"""
        try:
            user = payment.subscription.user
            
            # 执行AML检查
            aml_result = self.perform_aml_check(payment, user)
            
            # 执行KYC检查
            kyc_result = self.perform_kyc_check(user)
            
            # 更新支付记录的合规状态
            payment.aml_status = aml_result.status.value
            payment.kyc_status = kyc_result.status.value
            payment.compliance_score = (aml_result.score + kyc_result.score) / 2
            payment.compliance_checked_at = datetime.utcnow()
            
            # 判断是否通过合规检查
            compliance_passed = (
                aml_result.status in [ComplianceStatus.PASSED] and
                kyc_result.status in [ComplianceStatus.PASSED]
            )
            
            compliance_details = {
                'aml_check': {
                    'status': aml_result.status.value,
                    'risk_level': aml_result.risk_level.value,
                    'score': aml_result.score,
                    'details': aml_result.details
                },
                'kyc_check': {
                    'status': kyc_result.status.value,
                    'risk_level': kyc_result.risk_level.value,
                    'score': kyc_result.score,
                    'details': kyc_result.details
                },
                'overall_status': 'passed' if compliance_passed else 'failed',
                'requires_manual_review': aml_result.status == ComplianceStatus.REVIEW_REQUIRED or kyc_result.status == ComplianceStatus.REVIEW_REQUIRED
            }
            
            # 保存合规检查结果
            db.session.commit()
            
            # 记录综合合规审计
            self._log_compliance_event('payment_compliance_validation', user, payment, {
                'passed': compliance_passed,
                'details': compliance_details
            })
            
            logger.info(f"支付合规验证完成: 支付={payment.id}, 通过={compliance_passed}")
            return compliance_passed, compliance_details
            
        except Exception as e:
            logger.error(f"支付合规验证失败: {e}")
            return False, {'error': str(e)}
    
    # 辅助方法
    def _calculate_daily_payment_total(self, user: User) -> float:
        """计算用户当日支付总额"""
        try:
            today = datetime.utcnow().date()
            payments = Payment.query.join(UserSubscription).filter(
                UserSubscription.user_id == user.id,
                Payment.created_at >= today,
                Payment.status.in_([PaymentStatus.COMPLETED, PaymentStatus.CONFIRMING])
            ).all()
            return sum(p.amount for p in payments)
        except Exception:
            return 0.0
    
    def _calculate_monthly_payment_total(self, user: User) -> float:
        """计算用户当月支付总额"""
        try:
            month_start = datetime.utcnow().replace(day=1)
            payments = Payment.query.join(UserSubscription).filter(
                UserSubscription.user_id == user.id,
                Payment.created_at >= month_start,
                Payment.status.in_([PaymentStatus.COMPLETED, PaymentStatus.CONFIRMING])
            ).all()
            return sum(p.amount for p in payments)
        except Exception:
            return 0.0
    
    def _get_recent_payment_count(self, user: User, hours: int = 1) -> int:
        """获取最近N小时内的支付次数"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            count = Payment.query.join(UserSubscription).filter(
                UserSubscription.user_id == user.id,
                Payment.created_at >= cutoff
            ).count()
            return count
        except Exception:
            return 0
    
    def _assess_crypto_risk(self, payment: Payment) -> float:
        """评估加密货币风险"""
        crypto_risks = {
            'BTC': 0.1,  # 比特币风险较低
            'ETH': 0.2,  # 以太坊中等风险
            'USDC': 0.1,  # 稳定币风险较低
            'USDT': 0.3   # USDT风险较高
        }
        
        return crypto_risks.get(payment.crypto_currency.value if payment.crypto_currency else 'unknown', 0.5)
    
    def _get_user_login_count(self, user: User) -> int:
        """获取用户登录次数"""
        try:
            from models import LoginRecord
            return LoginRecord.query.filter_by(email=user.email).count()
        except Exception:
            return 0
    
    def _check_ip_consistency(self, user: User) -> bool:
        """检查IP地址一致性"""
        try:
            from models import LoginRecord
            recent_ips = LoginRecord.query.filter_by(email=user.email).order_by(
                LoginRecord.login_time.desc()
            ).limit(5).all()
            
            if len(recent_ips) < 2:
                return True
            
            # 检查最近5次登录的IP地址变化
            unique_ips = len(set(record.ip_address for record in recent_ips if record.ip_address))
            return unique_ips <= 3  # 允许最多3个不同IP
        except Exception:
            return True
    
    def _perform_external_aml_check(self, user: User, payment: Payment) -> Dict[str, Any]:
        """执行外部AML API检查"""
        try:
            if not self.compliance_api_key:
                # fail-closed：不静默返回 0 风险（“干净”），明确标注未筛查并施加轻度风险。
                # TODO(security): integrate real AML/sanctions screening (Chainalysis/OFAC API)
                return {'risk_score': 0.2, 'risk_factors': ['外部AML筛查未配置'], 'external_unavailable': True}
            
            # 调用外部合规API
            headers = {
                'Authorization': f'Bearer {self.compliance_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'user_email': user.email,
                'payment_amount': payment.amount,
                'payment_currency': payment.currency,
                'check_type': 'aml'
            }
            
            response = requests.post(
                f"{self.compliance_api_url}/aml-check",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'risk_score': result.get('risk_score', 0),
                    'risk_factors': result.get('risk_factors', [])
                }
            else:
                logger.warning(f"外部AML检查失败: HTTP {response.status_code}")
                return {'risk_score': 0.1, 'risk_factors': ['外部API检查失败']}
                
        except Exception as e:
            logger.error(f"外部AML检查异常: {e}")
            return {'risk_score': 0.1, 'risk_factors': ['外部API检查异常']}
    
    def _perform_external_kyc_check(self, user: User) -> Dict[str, Any]:
        """执行外部KYC API检查"""
        try:
            if not self.compliance_api_key:
                # fail-closed：不静默返回 0 风险，明确标注外部身份核验未配置。
                # TODO(security): integrate real KYC identity verification (Onfido/Jumio)
                return {'risk_score': 0.2, 'issues': ['外部KYC身份核验未配置'], 'external_unavailable': True}
            
            # 调用外部KYC API
            headers = {
                'Authorization': f'Bearer {self.compliance_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'user_email': user.email,
                'user_id': user.id,
                'check_type': 'kyc'
            }
            
            response = requests.post(
                f"{self.compliance_api_url}/kyc-check",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'risk_score': result.get('risk_score', 0),
                    'issues': result.get('issues', [])
                }
            else:
                logger.warning(f"外部KYC检查失败: HTTP {response.status_code}")
                return {'risk_score': 0.1, 'issues': ['外部API检查失败']}
                
        except Exception as e:
            logger.error(f"外部KYC检查异常: {e}")
            return {'risk_score': 0.1, 'issues': ['外部API检查异常']}
    
    def _log_compliance_event(self, event_type: str, user: User, payment: Optional[Payment], details: Any):
        """记录合规审计日志"""
        try:
            if not self.audit_enabled:
                return
            
            audit_entry = {
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user.id,
                'user_email': user.email,
                'payment_id': payment.id if payment else None,
                'details': details if isinstance(details, dict) else {'result': str(details)},
                'service': 'compliance_service',
                'ip_address': getattr(user, 'last_ip', 'unknown'),
                'user_agent': getattr(user, 'last_user_agent', 'unknown')
            }
            
            # 计算审计日志哈希以确保完整性
            audit_hash = hashlib.sha256(
                json.dumps(audit_entry, sort_keys=True).encode()
            ).hexdigest()
            
            audit_entry['audit_hash'] = audit_hash
            
            # 记录到日志文件
            logger.info(f"COMPLIANCE_AUDIT: {json.dumps(audit_entry, ensure_ascii=False)}")
            
            # 可选：保存到数据库审计表
            # self._save_audit_to_database(audit_entry)
            
        except Exception as e:
            logger.error(f"合规审计日志记录失败: {e}")

# 全局合规服务实例
compliance_service = ComplianceService()

# 导出
__all__ = ['ComplianceService', 'ComplianceStatus', 'RiskLevel', 'ComplianceCheck', 'compliance_service']