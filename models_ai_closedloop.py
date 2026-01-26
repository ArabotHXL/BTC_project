"""
AI Closed-Loop Models
AI 闭环流程模型

支持完整的闭环流程:
告警(Detect) → 诊断(Diagnose) → 建议(Recommend) → 审批(Approve) → 执行(Act) → 审计(Audit) → 复盘(Learn)
"""

from datetime import datetime
from db import db
import json


class RecommendationStatus:
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    EXECUTING = 'executing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    EXPIRED = 'expired'


class RiskLevel:
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class ActionType:
    REBOOT = 'reboot'
    POWER_OFF = 'power_off'
    POWER_ON = 'power_on'
    ADJUST_FREQUENCY = 'adjust_frequency'
    ADJUST_FAN = 'adjust_fan'
    SWITCH_POOL = 'switch_pool'
    CURTAIL = 'curtail'
    RESTORE = 'restore'
    ALERT_ONLY = 'alert_only'
    MANUAL_REVIEW = 'manual_review'


class AIRecommendation(db.Model):
    """AI 建议模型
    
    结构化输出，可直接转化为工单/命令
    """
    __tablename__ = 'ai_recommendations'
    
    id = db.Column(db.String(36), primary_key=True)
    
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    trigger_type = db.Column(db.String(50), nullable=False)
    trigger_id = db.Column(db.String(100), nullable=True)
    trigger_data = db.Column(db.JSON, nullable=True)
    
    diagnosis = db.Column(db.JSON, nullable=False)
    
    action_type = db.Column(db.String(50), nullable=False)
    action_params = db.Column(db.JSON, nullable=True)
    target_ids = db.Column(db.JSON, nullable=True)
    
    risk_level = db.Column(db.String(20), nullable=False, default=RiskLevel.MEDIUM)
    confidence_score = db.Column(db.Float, nullable=True)
    priority = db.Column(db.Integer, nullable=False, default=5)
    
    expected_benefit = db.Column(db.JSON, nullable=True)
    
    status = db.Column(db.String(20), nullable=False, default=RecommendationStatus.PENDING)
    
    require_approval = db.Column(db.Boolean, default=True)
    auto_approve_conditions = db.Column(db.JSON, nullable=True)
    
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_reason = db.Column(db.Text, nullable=True)
    
    rejected_by_user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    command_id = db.Column(db.String(36), nullable=True, index=True)
    execution_started_at = db.Column(db.DateTime, nullable=True)
    execution_completed_at = db.Column(db.DateTime, nullable=True)
    execution_result = db.Column(db.JSON, nullable=True)
    
    effectiveness_score = db.Column(db.Float, nullable=True)
    feedback_data = db.Column(db.JSON, nullable=True)
    learned_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (
        db.Index('idx_ai_rec_site_status', 'site_id', 'status'),
        db.Index('idx_ai_rec_created', 'created_at'),
        db.Index('idx_ai_rec_trigger', 'trigger_type', 'trigger_id'),
    )
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self, include_evidence=True):
        result = {
            'id': self.id,
            'site_id': self.site_id,
            'trigger': {
                'type': self.trigger_type,
                'id': self.trigger_id,
                'data': self.trigger_data if include_evidence else None,
            },
            'diagnosis': self.diagnosis,
            'action': {
                'type': self.action_type,
                'params': self.action_params,
                'target_ids': self.target_ids,
            },
            'risk': {
                'level': self.risk_level,
                'confidence': self.confidence_score,
                'priority': self.priority,
            },
            'expected_benefit': self.expected_benefit,
            'status': self.status,
            'approval': {
                'required': self.require_approval,
                'approved_by': self.approved_by_user_id,
                'approved_at': self.approved_at.isoformat() if self.approved_at else None,
                'reason': self.approval_reason,
            } if self.status in (RecommendationStatus.APPROVED, RecommendationStatus.EXECUTING, RecommendationStatus.COMPLETED) else None,
            'rejection': {
                'rejected_by': self.rejected_by_user_id,
                'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
                'reason': self.rejection_reason,
            } if self.status == RecommendationStatus.REJECTED else None,
            'execution': {
                'command_id': self.command_id,
                'started_at': self.execution_started_at.isoformat() if self.execution_started_at else None,
                'completed_at': self.execution_completed_at.isoformat() if self.execution_completed_at else None,
                'result': self.execution_result,
            } if self.command_id else None,
            'learning': {
                'effectiveness_score': self.effectiveness_score,
                'feedback': self.feedback_data,
                'learned_at': self.learned_at.isoformat() if self.learned_at else None,
            } if self.effectiveness_score is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
        return result
    
    def can_approve(self):
        return self.status == RecommendationStatus.PENDING
    
    def can_reject(self):
        return self.status == RecommendationStatus.PENDING
    
    def can_execute(self):
        return self.status == RecommendationStatus.APPROVED
    
    def should_auto_approve(self):
        """Check if recommendation meets auto-approve conditions"""
        if not self.auto_approve_conditions:
            return False
        
        conditions = self.auto_approve_conditions
        
        if conditions.get('max_risk_level'):
            risk_order = {RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4}
            max_level = risk_order.get(conditions['max_risk_level'], 2)
            current_level = risk_order.get(self.risk_level, 3)
            if current_level > max_level:
                return False
        
        if conditions.get('min_confidence') and self.confidence_score:
            if self.confidence_score < conditions['min_confidence']:
                return False
        
        if conditions.get('allowed_actions'):
            if self.action_type not in conditions['allowed_actions']:
                return False
        
        if conditions.get('max_targets') and self.target_ids:
            if len(self.target_ids) > conditions['max_targets']:
                return False
        
        return True


class AIRecommendationFeedback(db.Model):
    """AI 建议反馈模型
    
    用于记录建议的有效性反馈，支持模型迭代
    """
    __tablename__ = 'ai_recommendation_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.String(36), db.ForeignKey('ai_recommendations.id'), nullable=False, index=True)
    
    feedback_type = db.Column(db.String(50), nullable=False)
    
    was_effective = db.Column(db.Boolean, nullable=True)
    
    outcome_metrics = db.Column(db.JSON, nullable=True)
    
    user_rating = db.Column(db.Integer, nullable=True)
    user_comment = db.Column(db.Text, nullable=True)
    
    side_effects = db.Column(db.JSON, nullable=True)
    
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    recommendation = db.relationship('AIRecommendation', backref=db.backref('feedback_entries', lazy='dynamic'))
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'recommendation_id': self.recommendation_id,
            'feedback_type': self.feedback_type,
            'was_effective': self.was_effective,
            'outcome_metrics': self.outcome_metrics,
            'user_rating': self.user_rating,
            'user_comment': self.user_comment,
            'side_effects': self.side_effects,
            'created_by': self.created_by_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AutoApproveRule(db.Model):
    """自动审批规则
    
    定义哪些条件下 AI 建议可以自动执行
    """
    __tablename__ = 'auto_approve_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('hosting_sites.id'), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    is_active = db.Column(db.Boolean, default=True)
    
    conditions = db.Column(db.JSON, nullable=False)
    
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user_access.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'site_id': self.site_id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'conditions': self.conditions,
            'created_by': self.created_by_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
