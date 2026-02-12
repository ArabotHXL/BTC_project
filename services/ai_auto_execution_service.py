"""
AI Auto Execution Service
AI 自动执行服务

Phase 3: 将 AI 建议转换为自动执行的建议，带安全边界

功能:
1. 将限电建议、诊断建议转换为 AIRecommendation
2. 根据风险评估决定是否需要人工审批
3. 低风险操作自动执行
4. 所有操作记录审计日志
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

from db import db
from models_ai_closedloop import (
    AIRecommendation, AutoApproveRule,
    RecommendationStatus, RiskLevel, ActionType
)
from models_hosting import HostingSite
from services.ai_closedloop_service import AIClosedLoopService

logger = logging.getLogger(__name__)


class RiskAssessment:
    """风险评估结果"""
    def __init__(
        self,
        level: str,
        score: float,
        factors: List[Dict],
        can_auto_execute: bool,
        require_approval: bool,
        approval_level: str = 'operator',
    ):
        self.level = level
        self.score = score
        self.factors = factors
        self.can_auto_execute = can_auto_execute
        self.require_approval = require_approval
        self.approval_level = approval_level
    
    def to_dict(self):
        return {
            'level': self.level,
            'score': self.score,
            'factors': self.factors,
            'can_auto_execute': self.can_auto_execute,
            'require_approval': self.require_approval,
            'approval_level': self.approval_level,
        }


class AIAutoExecutionService:
    """AI Auto Execution Service
    
    Connects Phase 1/2 AI advice with the Closed-Loop execution system.
    """
    
    RISK_WEIGHTS = {
        'action_type': {
            ActionType.POWER_OFF: 0.8,
            ActionType.POWER_ON: 0.2,
            ActionType.REBOOT: 0.5,
            ActionType.CURTAIL: 0.6,
            ActionType.RESTORE: 0.3,
            ActionType.ADJUST_FREQUENCY: 0.4,
            ActionType.ADJUST_FAN: 0.2,
            ActionType.SWITCH_POOL: 0.5,
            ActionType.ALERT_ONLY: 0.0,
            ActionType.MANUAL_REVIEW: 0.0,
        },
        'target_count': {
            (0, 5): 0.1,
            (5, 20): 0.3,
            (20, 50): 0.5,
            (50, 100): 0.7,
            (100, float('inf')): 1.0,
        },
        'power_impact_kw': {
            (0, 100): 0.1,
            (100, 500): 0.3,
            (500, 1000): 0.5,
            (1000, 5000): 0.8,
            (5000, float('inf')): 1.0,
        },
        'revenue_impact_pct': {
            (0, 5): 0.1,
            (5, 10): 0.3,
            (10, 20): 0.5,
            (20, 50): 0.8,
            (50, 100): 1.0,
        },
    }
    
    RISK_THRESHOLDS = {
        RiskLevel.LOW: 0.25,
        RiskLevel.MEDIUM: 0.5,
        RiskLevel.HIGH: 0.75,
        RiskLevel.CRITICAL: 1.0,
    }
    
    def assess_risk(
        self,
        action_type: str,
        target_ids: Optional[List[str]] = None,
        power_impact_kw: float = 0,
        revenue_impact_pct: float = 0,
        confidence_score: float = 0.5,
        historical_success_rate: float = 0.9,
        time_of_day_risk: float = 0.0,
    ) -> RiskAssessment:
        """Assess risk of an AI-recommended action
        
        Returns RiskAssessment with level, factors, and auto-execute eligibility.
        
        Risk Scoring Model:
        - Each factor has a severity weight (0.0-1.0)
        - Factor multipliers distribute importance across dimensions
        - Worst-case total can reach ~0.92 (CRITICAL level)
        - Thresholds: LOW <0.25, MEDIUM <0.5, HIGH <0.75, CRITICAL >=0.75
        """
        factors = []
        total_score = 0.0
        
        action_weight = self.RISK_WEIGHTS['action_type'].get(action_type, 0.3)
        factors.append({
            'factor': 'action_type',
            'value': action_type,
            'weight': action_weight,
            'description_en': f"Action type '{action_type}' risk weight",
            'description_zh': f"操作类型 '{action_type}' 风险权重",
        })
        total_score += action_weight * 0.30
        
        target_count = len(target_ids) if target_ids else 0
        target_weight = 0.1
        for (low, high), weight in self.RISK_WEIGHTS['target_count'].items():
            if low <= target_count < high:
                target_weight = weight
                break
        factors.append({
            'factor': 'target_count',
            'value': target_count,
            'weight': target_weight,
            'description_en': f"{target_count} devices affected",
            'description_zh': f"影响 {target_count} 台设备",
        })
        total_score += target_weight * 0.25
        
        power_weight = 0.1
        for (low, high), weight in self.RISK_WEIGHTS['power_impact_kw'].items():
            if low <= power_impact_kw < high:
                power_weight = weight
                break
        factors.append({
            'factor': 'power_impact',
            'value': power_impact_kw,
            'weight': power_weight,
            'description_en': f"{power_impact_kw:.0f} kW power impact",
            'description_zh': f"功率影响 {power_impact_kw:.0f} kW",
        })
        total_score += power_weight * 0.20
        
        revenue_weight = 0.1
        for (low, high), weight in self.RISK_WEIGHTS['revenue_impact_pct'].items():
            if low <= revenue_impact_pct < high:
                revenue_weight = weight
                break
        factors.append({
            'factor': 'revenue_impact',
            'value': revenue_impact_pct,
            'weight': revenue_weight,
            'description_en': f"{revenue_impact_pct:.1f}% revenue impact",
            'description_zh': f"收益影响 {revenue_impact_pct:.1f}%",
        })
        total_score += revenue_weight * 0.15
        
        confidence_factor = (1 - confidence_score)
        factors.append({
            'factor': 'ai_confidence',
            'value': confidence_score,
            'weight': confidence_factor,
            'description_en': f"AI confidence {confidence_score*100:.0f}%",
            'description_zh': f"AI 置信度 {confidence_score*100:.0f}%",
        })
        total_score += confidence_factor * 0.05
        
        history_factor = (1 - historical_success_rate)
        factors.append({
            'factor': 'historical_success',
            'value': historical_success_rate,
            'weight': history_factor,
            'description_en': f"Historical success rate {historical_success_rate*100:.0f}%",
            'description_zh': f"历史成功率 {historical_success_rate*100:.0f}%",
        })
        total_score += history_factor * 0.03
        
        if time_of_day_risk > 0:
            factors.append({
                'factor': 'time_of_day',
                'value': time_of_day_risk,
                'weight': time_of_day_risk,
                'description_en': "High-risk time period",
                'description_zh': "高风险时段",
            })
            total_score += time_of_day_risk * 0.05
        
        total_score = min(total_score, 1.0)
        
        if total_score <= self.RISK_THRESHOLDS[RiskLevel.LOW]:
            level = RiskLevel.LOW
        elif total_score <= self.RISK_THRESHOLDS[RiskLevel.MEDIUM]:
            level = RiskLevel.MEDIUM
        elif total_score <= self.RISK_THRESHOLDS[RiskLevel.HIGH]:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.CRITICAL
        
        can_auto_execute = level == RiskLevel.LOW and confidence_score >= 0.7
        require_approval = level in (RiskLevel.HIGH, RiskLevel.CRITICAL) or not can_auto_execute
        
        if level == RiskLevel.CRITICAL:
            approval_level = 'admin'
        elif level == RiskLevel.HIGH:
            approval_level = 'manager'
        else:
            approval_level = 'operator'
        
        return RiskAssessment(
            level=level,
            score=total_score,
            factors=factors,
            can_auto_execute=can_auto_execute,
            require_approval=require_approval,
            approval_level=approval_level,
        )
    
    def create_curtailment_recommendation(
        self,
        site_id: int,
        curtailment_plan: Dict,
        trigger_type: str = 'ai_advisor',
        trigger_id: Optional[str] = None,
        operator_id: Optional[int] = None,
    ) -> AIRecommendation:
        """Create an AIRecommendation from a curtailment plan
        
        Converts Phase 1/2 CurtailmentAdvisor output into executable recommendation.
        """
        shutdown_order = curtailment_plan.get('shutdown_order', [])
        target_ids = [m.get('miner_id') for m in shutdown_order if m.get('miner_id')]
        
        power_impact = curtailment_plan.get('actual_reduction_kw', 0)
        economic_impact = curtailment_plan.get('economic_impact', {})
        revenue_loss = economic_impact.get('revenue_lost_hourly', 0)
        total_revenue = economic_impact.get('revenue_lost_hourly', 0) + economic_impact.get('cost_saved_hourly', 0)
        revenue_impact_pct = (revenue_loss / total_revenue * 100) if total_revenue > 0 else 0
        
        risk_assessment = self.assess_risk(
            action_type=ActionType.CURTAIL,
            target_ids=target_ids,
            power_impact_kw=power_impact,
            revenue_impact_pct=revenue_impact_pct,
            confidence_score=0.8,
        )
        
        expected_benefit = {
            'power_saved_kw': power_impact,
            'cost_saved_hourly': economic_impact.get('cost_saved_hourly', 0),
            'revenue_lost_hourly': economic_impact.get('revenue_lost_hourly', 0),
            'net_benefit_hourly': economic_impact.get('net_hourly_impact', 0),
            'recovery_time_minutes': curtailment_plan.get('recovery_time_minutes', 15),
        }
        
        diagnosis = {
            'trigger': trigger_type,
            'strategy': curtailment_plan.get('strategy', 'efficiency_first'),
            'strategy_zh': curtailment_plan.get('strategy_zh', '效率优先'),
            'risk_points': curtailment_plan.get('risk_points', []),
            'data_sources': curtailment_plan.get('data_sources', []),
        }
        
        recommendation = AIClosedLoopService.create_recommendation(
            site_id=site_id,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            trigger_data={'curtailment_plan': curtailment_plan},
            diagnosis=diagnosis,
            action_type=ActionType.CURTAIL,
            action_params={
                'shutdown_order': shutdown_order,
                'target_reduction_kw': curtailment_plan.get('target_reduction_kw', 0),
                'actual_reduction_kw': power_impact,
            },
            target_ids=target_ids,
            risk_level=risk_assessment.level,
            confidence_score=0.8,
            priority=3 if risk_assessment.level == RiskLevel.LOW else 5,
            expected_benefit=expected_benefit,
        )
        
        logger.info(f"Created curtailment recommendation {recommendation.id} with risk={risk_assessment.level}")
        
        auto_executed = False
        is_auto_approved = (
            recommendation.status == RecommendationStatus.APPROVED and
            recommendation.risk_level == RiskLevel.LOW
        )
        # Check site-level AI auto-execute toggle
        if is_auto_approved and operator_id:
            site = HostingSite.query.get(recommendation.site_id) if recommendation.site_id else None
            if site and not site.ai_auto_execute_enabled:
                logger.info(f"AI auto-execute disabled for site {site.id} ({site.name}), skipping auto-execution for recommendation {recommendation.id}")
                is_auto_approved = False
        if is_auto_approved and operator_id:
            try:
                result = AIClosedLoopService.execute_recommendation(
                    recommendation_id=recommendation.id,
                    operator_id=operator_id,
                )
                auto_executed = result.get('success', False)
                if auto_executed:
                    logger.info(f"Auto-executed recommendation {recommendation.id}")
                else:
                    logger.warning(f"Auto-execution failed for {recommendation.id}: {result.get('error')}")
            except Exception as e:
                logger.error(f"Auto-execution error for {recommendation.id}: {e}")
        
        recommendation._auto_executed = auto_executed
        return recommendation
    
    def create_alert_action_recommendation(
        self,
        site_id: int,
        miner_id: str,
        alert_type: str,
        diagnosis: Dict,
        suggested_action: Dict,
        trigger_id: Optional[str] = None,
    ) -> AIRecommendation:
        """Create an AIRecommendation from an alert diagnosis suggested action"""
        action_type_mapping = {
            'reboot': ActionType.REBOOT,
            'power_off': ActionType.POWER_OFF,
            'power_on': ActionType.POWER_ON,
            'adjust_fan': ActionType.ADJUST_FAN,
            'switch_pool': ActionType.SWITCH_POOL,
        }
        
        command_type = suggested_action.get('command_type', 'manual_review')
        action_type = action_type_mapping.get(command_type, ActionType.MANUAL_REVIEW)
        
        risk_assessment = self.assess_risk(
            action_type=action_type,
            target_ids=[miner_id],
            confidence_score=suggested_action.get('confidence', 0.6),
        )
        
        recommendation = AIClosedLoopService.create_recommendation(
            site_id=site_id,
            trigger_type='alert',
            trigger_id=trigger_id or f"{alert_type}_{miner_id}",
            trigger_data={'alert_type': alert_type, 'miner_id': miner_id},
            diagnosis=diagnosis,
            action_type=action_type,
            action_params=suggested_action.get('parameters', {}),
            target_ids=[miner_id],
            risk_level=risk_assessment.level,
            confidence_score=suggested_action.get('confidence', 0.6),
            priority=suggested_action.get('priority', 5),
        )
        
        logger.info(f"Created alert action recommendation {recommendation.id}")
        
        return recommendation
    
    def get_pending_recommendations(
        self,
        site_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[AIRecommendation]:
        """Get pending recommendations awaiting approval"""
        query = AIRecommendation.query.filter_by(status=RecommendationStatus.PENDING)
        if site_id:
            query = query.filter_by(site_id=site_id)
        return query.order_by(AIRecommendation.priority, AIRecommendation.created_at).limit(limit).all()
    
    def get_auto_approve_rules(self, site_id: int) -> List[AutoApproveRule]:
        """Get active auto-approve rules for a site"""
        return AutoApproveRule.query.filter_by(site_id=site_id, is_active=True).all()
    
    def create_auto_approve_rule(
        self,
        site_id: int,
        name: str,
        conditions: Dict,
        description: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
    ) -> AutoApproveRule:
        """Create a new auto-approve rule"""
        rule = AutoApproveRule(
            site_id=site_id,
            name=name,
            description=description,
            conditions=conditions,
            created_by_user_id=created_by_user_id,
            is_active=True,
        )
        db.session.add(rule)
        db.session.commit()
        
        logger.info(f"Created auto-approve rule {rule.id} for site {site_id}")
        return rule
    
    def update_auto_approve_rule(
        self,
        rule_id: int,
        conditions: Optional[Dict] = None,
        is_active: Optional[bool] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AutoApproveRule:
        """Update an auto-approve rule"""
        rule = AutoApproveRule.query.get(rule_id)
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")
        
        if conditions is not None:
            rule.conditions = conditions
        if is_active is not None:
            rule.is_active = is_active
        if name is not None:
            rule.name = name
        if description is not None:
            rule.description = description
        
        rule.updated_at = datetime.utcnow()
        db.session.commit()
        
        return rule
    
    def execute_auto_approved(
        self,
        site_id: Optional[int] = None,
        operator_id: Optional[int] = None,
    ) -> List[Dict]:
        """Find and execute all auto-approved recommendations
        
        Returns list of execution results.
        Requires valid operator_id for audit trail.
        """
        if not operator_id:
            raise ValueError("operator_id is required for audit trail")
        query = AIRecommendation.query.filter_by(status=RecommendationStatus.APPROVED)
        if site_id:
            query = query.filter_by(site_id=site_id)
        
        approved_recs = query.filter(
            AIRecommendation.approval_reason.like('%Auto-approved%')
        ).all()
        
        results = []
        for rec in approved_recs:
            # Check site-level AI auto-execute toggle
            if rec.site_id:
                site = HostingSite.query.get(rec.site_id)
                if site and not site.ai_auto_execute_enabled:
                    logger.info(f"AI auto-execute disabled for site {site.id} ({site.name}), skipping auto-execution for recommendation {rec.id}")
                    results.append({
                        'success': False,
                        'recommendation_id': rec.id,
                        'error': f"AI auto-execute disabled for site {rec.site_id}",
                    })
                    continue
            try:
                result = AIClosedLoopService.execute_recommendation(rec.id, operator_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to execute recommendation {rec.id}: {e}")
                results.append({
                    'success': False,
                    'recommendation_id': rec.id,
                    'error': str(e),
                })
        
        return results


ai_auto_execution_service = AIAutoExecutionService()
