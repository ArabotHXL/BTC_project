"""
AI Closed-Loop Service
AI 闭环服务

实现完整的闭环流程:
告警(Detect) → 诊断(Diagnose) → 建议(Recommend) → 审批(Approve) → 执行(Act) → 审计(Audit) → 复盘(Learn)
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from db import db
from models_ai_closedloop import (
    AIRecommendation, AIRecommendationFeedback, AutoApproveRule,
    RecommendationStatus, RiskLevel, ActionType
)
from models_control_plane import AuditEvent
from models_remote_control import RemoteCommand

logger = logging.getLogger(__name__)


class AIClosedLoopService:
    """AI Closed-Loop Service
    
    Manages the full lifecycle of AI recommendations:
    1. Detect - Receive alerts and anomalies
    2. Diagnose - AI analyzes root cause
    3. Recommend - Generate structured action recommendations
    4. Approve - Human or auto-approval workflow
    5. Act - Execute via Control Plane v1
    6. Audit - Track all actions
    7. Learn - Collect feedback for model improvement
    """
    
    @staticmethod
    def create_recommendation(
        site_id: int,
        trigger_type: str,
        trigger_id: Optional[str],
        trigger_data: Optional[Dict],
        diagnosis: Dict,
        action_type: str,
        action_params: Optional[Dict] = None,
        target_ids: Optional[List[str]] = None,
        risk_level: str = RiskLevel.MEDIUM,
        confidence_score: Optional[float] = None,
        priority: int = 5,
        expected_benefit: Optional[Dict] = None,
        expires_in_hours: int = 24,
    ) -> AIRecommendation:
        """Create a new AI recommendation
        
        Args:
            site_id: Target site
            trigger_type: What triggered this (alert, anomaly, schedule, user_request)
            trigger_id: ID of the triggering event
            trigger_data: Evidence/context data
            diagnosis: AI diagnosis output (root_cause, evidence, confidence)
            action_type: Recommended action type
            action_params: Action parameters
            target_ids: Target miner/device IDs
            risk_level: Risk assessment
            confidence_score: AI confidence (0-1)
            priority: Priority (1=highest, 10=lowest)
            expected_benefit: Expected outcome
            expires_in_hours: Recommendation validity window
        
        Returns:
            Created AIRecommendation object
        """
        rec_id = str(uuid.uuid4())
        
        auto_approve_rules = AutoApproveRule.query.filter_by(
            site_id=site_id,
            is_active=True
        ).all()
        
        auto_approve_conditions = None
        for rule in auto_approve_rules:
            conditions = rule.conditions or {}
            auto_approve_conditions = conditions
            break
        
        recommendation = AIRecommendation(
            id=rec_id,
            site_id=site_id,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            trigger_data=trigger_data,
            diagnosis=diagnosis,
            action_type=action_type,
            action_params=action_params,
            target_ids=target_ids,
            risk_level=risk_level,
            confidence_score=confidence_score,
            priority=priority,
            expected_benefit=expected_benefit,
            require_approval=True,
            auto_approve_conditions=auto_approve_conditions,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours),
        )
        
        if recommendation.should_auto_approve():
            recommendation.status = RecommendationStatus.APPROVED
            recommendation.approved_at = datetime.utcnow()
            recommendation.approval_reason = 'Auto-approved by rule'
            logger.info(f"AI recommendation {rec_id} auto-approved")
        
        db.session.add(recommendation)
        
        AIClosedLoopService._log_audit_event(
            event_type='ai.recommendation.created',
            site_id=site_id,
            ref_type='ai_recommendation',
            ref_id=rec_id,
            payload={
                'trigger_type': trigger_type,
                'action_type': action_type,
                'risk_level': risk_level,
                'auto_approved': recommendation.status == RecommendationStatus.APPROVED,
            }
        )
        
        db.session.commit()
        
        return recommendation
    
    @staticmethod
    def approve_recommendation(
        recommendation_id: str,
        user_id: int,
        reason: Optional[str] = None,
    ) -> AIRecommendation:
        """Approve a pending recommendation"""
        rec = AIRecommendation.query.get(recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        if not rec.can_approve():
            raise ValueError(f"Recommendation cannot be approved (status={rec.status})")
        
        rec.status = RecommendationStatus.APPROVED
        rec.approved_by_user_id = user_id
        rec.approved_at = datetime.utcnow()
        rec.approval_reason = reason
        rec.updated_at = datetime.utcnow()
        
        AIClosedLoopService._log_audit_event(
            event_type='ai.recommendation.approved',
            actor_id=user_id,
            site_id=rec.site_id,
            ref_type='ai_recommendation',
            ref_id=recommendation_id,
            payload={'reason': reason}
        )
        
        db.session.commit()
        
        return rec
    
    @staticmethod
    def reject_recommendation(
        recommendation_id: str,
        user_id: int,
        reason: str,
    ) -> AIRecommendation:
        """Reject a pending recommendation"""
        rec = AIRecommendation.query.get(recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        if not rec.can_reject():
            raise ValueError(f"Recommendation cannot be rejected (status={rec.status})")
        
        rec.status = RecommendationStatus.REJECTED
        rec.rejected_by_user_id = user_id
        rec.rejected_at = datetime.utcnow()
        rec.rejection_reason = reason
        rec.updated_at = datetime.utcnow()
        
        AIClosedLoopService._log_audit_event(
            event_type='ai.recommendation.rejected',
            actor_id=user_id,
            site_id=rec.site_id,
            ref_type='ai_recommendation',
            ref_id=recommendation_id,
            payload={'reason': reason}
        )
        
        db.session.commit()
        
        return rec
    
    @staticmethod
    def execute_recommendation(
        recommendation_id: str,
        operator_id: int,
    ) -> Dict:
        """Execute an approved recommendation via Control Plane v1
        
        Creates a RemoteCommand and dispatches it through the control plane.
        """
        rec = AIRecommendation.query.get(recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        if not rec.can_execute():
            raise ValueError(f"Recommendation cannot be executed (status={rec.status})")
        
        rec.status = RecommendationStatus.EXECUTING
        rec.execution_started_at = datetime.utcnow()
        rec.updated_at = datetime.utcnow()
        
        try:
            command = RemoteCommand(
                id=str(uuid.uuid4()),
                tenant_id=operator_id,
                site_id=rec.site_id,
                requested_by_user_id=operator_id,
                requested_by_role='system',
                command_type=AIClosedLoopService._map_action_to_command_type(rec.action_type),
                payload_json=rec.action_params or {},
                target_ids=rec.target_ids or [],
                status='QUEUED',
                require_approval=False,
                expires_at=datetime.utcnow() + timedelta(hours=24),
            )
            
            db.session.add(command)
            rec.command_id = command.id
            
            AIClosedLoopService._log_audit_event(
                event_type='ai.recommendation.executing',
                actor_id=operator_id,
                site_id=rec.site_id,
                ref_type='ai_recommendation',
                ref_id=recommendation_id,
                payload={
                    'command_id': command.id,
                    'action_type': rec.action_type,
                    'target_count': len(rec.target_ids) if rec.target_ids else 0,
                }
            )
            
            db.session.commit()
            
            return {
                'success': True,
                'recommendation_id': recommendation_id,
                'command_id': command.id,
                'status': 'executing',
            }
            
        except Exception as e:
            rec.status = RecommendationStatus.FAILED
            rec.execution_result = {'error': str(e)}
            rec.execution_completed_at = datetime.utcnow()
            db.session.commit()
            
            logger.error(f"Failed to execute recommendation {recommendation_id}: {e}")
            raise
    
    @staticmethod
    def complete_execution(
        recommendation_id: str,
        success: bool,
        result_data: Optional[Dict] = None,
    ) -> AIRecommendation:
        """Mark execution as complete"""
        rec = AIRecommendation.query.get(recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        rec.status = RecommendationStatus.COMPLETED if success else RecommendationStatus.FAILED
        rec.execution_completed_at = datetime.utcnow()
        rec.execution_result = result_data
        rec.updated_at = datetime.utcnow()
        
        AIClosedLoopService._log_audit_event(
            event_type='ai.recommendation.completed' if success else 'ai.recommendation.failed',
            site_id=rec.site_id,
            ref_type='ai_recommendation',
            ref_id=recommendation_id,
            payload={'success': success, 'result': result_data}
        )
        
        db.session.commit()
        
        return rec
    
    @staticmethod
    def add_feedback(
        recommendation_id: str,
        feedback_type: str,
        was_effective: Optional[bool] = None,
        outcome_metrics: Optional[Dict] = None,
        user_rating: Optional[int] = None,
        user_comment: Optional[str] = None,
        side_effects: Optional[Dict] = None,
        user_id: Optional[int] = None,
    ) -> AIRecommendationFeedback:
        """Add feedback for learning loop"""
        rec = AIRecommendation.query.get(recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        feedback = AIRecommendationFeedback(
            recommendation_id=recommendation_id,
            feedback_type=feedback_type,
            was_effective=was_effective,
            outcome_metrics=outcome_metrics,
            user_rating=user_rating,
            user_comment=user_comment,
            side_effects=side_effects,
            created_by_user_id=user_id,
        )
        
        db.session.add(feedback)
        
        if was_effective is not None:
            rec.effectiveness_score = 1.0 if was_effective else 0.0
            rec.feedback_data = {
                'feedback_type': feedback_type,
                'rating': user_rating,
                'comment': user_comment,
            }
            rec.learned_at = datetime.utcnow()
        
        AIClosedLoopService._log_audit_event(
            event_type='ai.recommendation.feedback',
            actor_id=user_id,
            site_id=rec.site_id,
            ref_type='ai_recommendation',
            ref_id=recommendation_id,
            payload={
                'feedback_type': feedback_type,
                'was_effective': was_effective,
                'rating': user_rating,
            }
        )
        
        db.session.commit()
        
        return feedback
    
    @staticmethod
    def get_pending_recommendations(
        site_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[AIRecommendation]:
        """Get pending recommendations for approval"""
        query = AIRecommendation.query.filter_by(status=RecommendationStatus.PENDING)
        
        if site_id:
            query = query.filter_by(site_id=site_id)
        
        return query.order_by(
            AIRecommendation.priority.asc(),
            AIRecommendation.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_recommendation_history(
        site_id: int,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[AIRecommendation]:
        """Get recommendation history for a site"""
        query = AIRecommendation.query.filter_by(site_id=site_id)
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(AIRecommendation.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_learning_stats(site_id: int) -> Dict:
        """Get learning statistics for a site"""
        from sqlalchemy import func
        
        total = AIRecommendation.query.filter_by(site_id=site_id).count()
        
        completed = AIRecommendation.query.filter_by(
            site_id=site_id,
            status=RecommendationStatus.COMPLETED
        ).count()
        
        with_feedback = AIRecommendation.query.filter(
            AIRecommendation.site_id == site_id,
            AIRecommendation.effectiveness_score.isnot(None)
        ).count()
        
        avg_effectiveness = db.session.query(
            func.avg(AIRecommendation.effectiveness_score)
        ).filter(
            AIRecommendation.site_id == site_id,
            AIRecommendation.effectiveness_score.isnot(None)
        ).scalar() or 0
        
        by_action = db.session.query(
            AIRecommendation.action_type,
            func.count(AIRecommendation.id),
            func.avg(AIRecommendation.effectiveness_score)
        ).filter(
            AIRecommendation.site_id == site_id
        ).group_by(AIRecommendation.action_type).all()
        
        return {
            'total_recommendations': total,
            'completed': completed,
            'with_feedback': with_feedback,
            'avg_effectiveness': round(avg_effectiveness, 2) if avg_effectiveness else None,
            'by_action_type': [
                {
                    'action': row[0],
                    'count': row[1],
                    'avg_effectiveness': round(row[2], 2) if row[2] else None,
                }
                for row in by_action
            ],
        }
    
    @staticmethod
    def _map_action_to_command_type(action_type: str) -> str:
        """Map AI action type to Control Plane command type"""
        mapping = {
            ActionType.REBOOT: 'REBOOT',
            ActionType.POWER_OFF: 'POWER_OFF',
            ActionType.POWER_ON: 'POWER_ON',
            ActionType.ADJUST_FREQUENCY: 'SET_FREQUENCY',
            ActionType.ADJUST_FAN: 'SET_FAN',
            ActionType.SWITCH_POOL: 'SWITCH_POOL',
            ActionType.CURTAIL: 'CURTAIL',
            ActionType.RESTORE: 'RESTORE',
        }
        return mapping.get(action_type, 'CUSTOM')
    
    @staticmethod
    def _log_audit_event(
        event_type: str,
        site_id: int,
        ref_type: str,
        ref_id: str,
        payload: Optional[Dict] = None,
        actor_id: Optional[int] = None,
    ):
        """Log audit event for AI actions"""
        try:
            import hashlib
            
            last_event = AuditEvent.query.order_by(AuditEvent.id.desc()).first()
            prev_hash = last_event.event_hash if last_event else '0' * 64
            
            event = AuditEvent(
                event_type=event_type,
                actor_type='user' if actor_id else 'system',
                actor_id=actor_id,
                site_id=site_id,
                ref_type=ref_type,
                ref_id=ref_id,
                payload=payload,
                prev_hash=prev_hash,
            )
            
            hash_input = f"{event.event_type}:{event.actor_id}:{event.ref_id}:{prev_hash}"
            event.event_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            db.session.add(event)
        except Exception as e:
            logger.warning(f"Failed to log audit event: {e}")


ai_closedloop_service = AIClosedLoopService()
