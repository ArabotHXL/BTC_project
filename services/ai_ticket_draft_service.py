"""
AI Ticket Draft Service
AI 工单草稿服务

功能:
- 接入告警证据包 + 站点/机型信息 + 最近变更
- 输出结构化工单字段（问题描述、影响范围、排查步骤、需要客户确认项）
- 把"写工单"从 10–20 分钟压到 1–2 分钟

验收口径：AI 不需要 100% 正确，但要做到：可复核、有证据、能节省时间
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TicketField:
    """工单字段"""
    key: str
    label: str
    label_zh: str
    value: Any
    editable: bool = True
    required: bool = True


@dataclass
class ChecklistItem:
    """检查清单项"""
    item: str
    item_zh: str
    checked: bool = False
    required: bool = False


@dataclass
class TicketDraft:
    """工单草稿"""
    ticket_id: Optional[str]
    site_id: int
    miner_ids: List[str]
    
    title: str
    title_zh: str
    
    category: str
    priority: str
    
    problem_description: str
    problem_description_zh: str
    
    impact_scope: str
    impact_scope_zh: str
    
    root_cause_analysis: str
    root_cause_analysis_zh: str
    
    troubleshooting_steps: List[str]
    troubleshooting_steps_zh: List[str]
    
    recommended_actions: List[str]
    recommended_actions_zh: List[str]
    
    customer_confirmation_items: List[ChecklistItem]
    
    evidence_summary: str
    evidence_summary_zh: str
    
    estimated_resolution_time: str
    estimated_resolution_time_zh: str
    
    generated_at: str
    data_sources: List[str]


class AITicketDraftService:
    """AI 工单草稿服务
    
    输入：告警证据包 + 站点/机型信息 + 最近变更
    输出：结构化工单字段
    """
    
    CATEGORY_MAP = {
        'miner_offline': ('Hardware', '硬件'),
        'offline': ('Hardware', '硬件'),
        'hashrate_low': ('Performance', '性能'),
        'hashrate_drop': ('Performance', '性能'),
        'temperature_high': ('Environment', '环境'),
        'temperature_critical': ('Environment', '环境'),
        'hardware_error': ('Hardware', '硬件'),
        'fan_failure': ('Hardware', '硬件'),
        'network': ('Network', '网络'),
    }
    
    PRIORITY_MAP = {
        'critical': ('P1 - Critical', 'P1 - 紧急'),
        'high': ('P2 - High', 'P2 - 高'),
        'medium': ('P3 - Medium', 'P3 - 中'),
        'low': ('P4 - Low', 'P4 - 低'),
    }
    
    def generate_ticket_draft(
        self,
        site_id: int,
        miner_ids: List[str],
        alert_type: str,
        diagnosis_result: Dict,
        site_info: Optional[Dict] = None,
        miner_info: Optional[Dict] = None,
    ) -> TicketDraft:
        """生成工单草稿
        
        Args:
            site_id: 站点ID
            miner_ids: 受影响的矿机ID列表
            alert_type: 告警类型
            diagnosis_result: 来自 AlertDiagnosisService 的诊断结果
            site_info: 站点信息（名称、位置等）
            miner_info: 矿机信息（型号、固件等）
        
        Returns:
            TicketDraft 结构化工单草稿
        """
        now = datetime.utcnow()
        
        category = self.CATEGORY_MAP.get(alert_type, ('General', '一般'))
        
        risk_level = 'medium'
        if diagnosis_result.get('hypotheses'):
            risk_level = diagnosis_result['hypotheses'][0].get('risk_level', 'medium')
        priority = self.PRIORITY_MAP.get(risk_level, self.PRIORITY_MAP['medium'])
        
        title, title_zh = self._generate_title(alert_type, miner_ids, diagnosis_result)
        
        problem_desc, problem_desc_zh = self._generate_problem_description(
            alert_type, miner_ids, diagnosis_result, site_info
        )
        
        impact, impact_zh = self._generate_impact_scope(miner_ids, miner_info, site_info)
        
        rca, rca_zh = self._generate_root_cause_analysis(diagnosis_result)
        
        steps, steps_zh = self._generate_troubleshooting_steps(diagnosis_result)
        
        actions, actions_zh = self._generate_recommended_actions(diagnosis_result)
        
        confirmations = self._generate_customer_confirmations(alert_type, diagnosis_result)
        
        evidence, evidence_zh = self._generate_evidence_summary(diagnosis_result)
        
        resolution_time, resolution_time_zh = self._estimate_resolution_time(alert_type, risk_level)
        
        return TicketDraft(
            ticket_id=None,
            site_id=site_id,
            miner_ids=miner_ids,
            title=title,
            title_zh=title_zh,
            category=category[0],
            priority=priority[0],
            problem_description=problem_desc,
            problem_description_zh=problem_desc_zh,
            impact_scope=impact,
            impact_scope_zh=impact_zh,
            root_cause_analysis=rca,
            root_cause_analysis_zh=rca_zh,
            troubleshooting_steps=steps,
            troubleshooting_steps_zh=steps_zh,
            recommended_actions=actions,
            recommended_actions_zh=actions_zh,
            customer_confirmation_items=confirmations,
            evidence_summary=evidence,
            evidence_summary_zh=evidence_zh,
            estimated_resolution_time=resolution_time,
            estimated_resolution_time_zh=resolution_time_zh,
            generated_at=now.isoformat(),
            data_sources=diagnosis_result.get('data_sources', []),
        )
    
    def _generate_title(
        self,
        alert_type: str,
        miner_ids: List[str],
        diagnosis_result: Dict,
    ) -> tuple:
        """生成工单标题"""
        miner_count = len(miner_ids)
        
        if diagnosis_result.get('hypotheses'):
            main_cause = diagnosis_result['hypotheses'][0].get('cause', alert_type)
            main_cause_zh = diagnosis_result['hypotheses'][0].get('cause_zh', alert_type)
        else:
            main_cause = alert_type.replace('_', ' ').title()
            main_cause_zh = alert_type
        
        if miner_count == 1:
            title = f"[{miner_ids[0]}] {main_cause}"
            title_zh = f"[{miner_ids[0]}] {main_cause_zh}"
        else:
            title = f"[{miner_count} Miners] {main_cause}"
            title_zh = f"[{miner_count} 台矿机] {main_cause_zh}"
        
        return title, title_zh
    
    def _generate_problem_description(
        self,
        alert_type: str,
        miner_ids: List[str],
        diagnosis_result: Dict,
        site_info: Optional[Dict],
    ) -> tuple:
        """生成问题描述"""
        miner_count = len(miner_ids)
        site_name = site_info.get('name', f'Site {diagnosis_result.get("site_id", "")}') if site_info else f'Site {diagnosis_result.get("site_id", "")}'
        
        alert_descriptions = {
            'miner_offline': ('went offline and is not responding to telemetry requests', '离线，无法响应遥测请求'),
            'offline': ('went offline and is not responding to telemetry requests', '离线，无法响应遥测请求'),
            'hashrate_low': ('is experiencing below-normal hashrate', '算力低于正常水平'),
            'hashrate_drop': ('experienced a significant hashrate drop', '算力出现明显下降'),
            'temperature_high': ('is running at elevated temperatures', '运行温度偏高'),
            'temperature_critical': ('reached critical temperature levels', '达到临界温度'),
            'hardware_error': ('is reporting hardware errors', '报告硬件错误'),
        }
        
        desc = alert_descriptions.get(alert_type, ('requires attention', '需要关注'))
        
        if miner_count == 1:
            problem = f"Miner {miner_ids[0]} at {site_name} {desc[0]}."
            problem_zh = f"站点 {site_name} 的矿机 {miner_ids[0]} {desc[1]}。"
        else:
            miner_list = ', '.join(miner_ids[:5])
            if miner_count > 5:
                miner_list += f' and {miner_count - 5} more'
            problem = f"{miner_count} miners at {site_name} ({miner_list}) {desc[0]}."
            problem_zh = f"站点 {site_name} 的 {miner_count} 台矿机（{miner_list}）{desc[1]}。"
        
        if diagnosis_result.get('summary'):
            problem += f"\n\nAI Analysis: {diagnosis_result['summary']}"
            problem_zh += f"\n\nAI 分析：{diagnosis_result.get('summary_zh', diagnosis_result['summary'])}"
        
        return problem, problem_zh
    
    def _generate_impact_scope(
        self,
        miner_ids: List[str],
        miner_info: Optional[Dict],
        site_info: Optional[Dict],
    ) -> tuple:
        """生成影响范围"""
        miner_count = len(miner_ids)
        
        if miner_info:
            total_hashrate = miner_info.get('expected_hashrate_ths', 0) * miner_count
            total_power = miner_info.get('power_w', 0) * miner_count
            impact = f"Affected: {miner_count} miner(s)\nEstimated hashrate loss: {total_hashrate:.1f} TH/s\nPower allocation affected: {total_power/1000:.1f} kW"
            impact_zh = f"受影响矿机：{miner_count} 台\n预计算力损失：{total_hashrate:.1f} TH/s\n涉及电力：{total_power/1000:.1f} kW"
        else:
            impact = f"Affected: {miner_count} miner(s)"
            impact_zh = f"受影响矿机：{miner_count} 台"
        
        return impact, impact_zh
    
    def _generate_root_cause_analysis(self, diagnosis_result: Dict) -> tuple:
        """生成根因分析"""
        hypotheses = diagnosis_result.get('hypotheses', [])
        
        if not hypotheses:
            return (
                "Root cause analysis pending - insufficient data available.",
                "根因分析待定 - 数据不足。"
            )
        
        rca_parts = []
        rca_parts_zh = []
        
        for i, h in enumerate(hypotheses[:3], 1):
            confidence = h.get('confidence', 0) * 100
            rca_parts.append(f"{i}. {h.get('cause', 'Unknown')} (Confidence: {confidence:.0f}%)")
            rca_parts_zh.append(f"{i}. {h.get('cause_zh', h.get('cause', '未知'))}（置信度：{confidence:.0f}%）")
            
            for evidence in h.get('evidence', []):
                rca_parts.append(f"   - Evidence: {evidence.get('description', '')}")
                rca_parts_zh.append(f"   - 证据：{evidence.get('description_zh', evidence.get('description', ''))}")
        
        return '\n'.join(rca_parts), '\n'.join(rca_parts_zh)
    
    def _generate_troubleshooting_steps(self, diagnosis_result: Dict) -> tuple:
        """生成排查步骤"""
        hypotheses = diagnosis_result.get('hypotheses', [])
        
        steps = []
        steps_zh = []
        
        for h in hypotheses[:2]:
            for action in h.get('suggested_actions', []):
                if action.get('action') not in steps:
                    steps.append(action.get('action', ''))
                    steps_zh.append(action.get('action_zh', action.get('action', '')))
        
        if not steps:
            steps = ['Check miner status and connectivity', 'Review recent logs', 'Contact on-site technician if needed']
            steps_zh = ['检查矿机状态和连通性', '查看最近日志', '如需要联系现场技术人员']
        
        return steps, steps_zh
    
    def _generate_recommended_actions(self, diagnosis_result: Dict) -> tuple:
        """生成建议操作"""
        hypotheses = diagnosis_result.get('hypotheses', [])
        
        actions = []
        actions_zh = []
        
        for h in hypotheses:
            for action in h.get('suggested_actions', []):
                if action.get('command_type'):
                    cmd = action.get('command_type')
                    actions.append(f"[Remote Command] {action.get('action', '')} (Command: {cmd})")
                    actions_zh.append(f"[远程命令] {action.get('action_zh', '')}（命令：{cmd}）")
        
        if not actions:
            actions = ['Monitor situation and wait for auto-recovery', 'Escalate to on-site team if no improvement']
            actions_zh = ['监控情况等待自动恢复', '如无改善则上报现场团队']
        
        return actions, actions_zh
    
    def _generate_customer_confirmations(
        self,
        alert_type: str,
        diagnosis_result: Dict,
    ) -> List[ChecklistItem]:
        """生成需客户确认的事项"""
        confirmations = []
        
        confirmations.append(ChecklistItem(
            item='Customer aware of the issue',
            item_zh='客户已知晓此问题',
            required=True,
        ))
        
        if alert_type in ('miner_offline', 'offline'):
            confirmations.append(ChecklistItem(
                item='Customer confirmed no on-site power/network maintenance',
                item_zh='客户确认现场无电力/网络维护',
                required=True,
            ))
        
        hypotheses = diagnosis_result.get('hypotheses', [])
        has_remote_command = any(
            action.get('command_type')
            for h in hypotheses
            for action in h.get('suggested_actions', [])
        )
        
        if has_remote_command:
            confirmations.append(ChecklistItem(
                item='Customer approved remote command execution',
                item_zh='客户批准执行远程命令',
                required=True,
            ))
        
        confirmations.append(ChecklistItem(
            item='Customer confirmed preferred contact method for updates',
            item_zh='客户确认了更新通知的联系方式',
            required=False,
        ))
        
        return confirmations
    
    def _generate_evidence_summary(self, diagnosis_result: Dict) -> tuple:
        """生成证据摘要"""
        hypotheses = diagnosis_result.get('hypotheses', [])
        
        evidence_items = []
        evidence_items_zh = []
        
        for h in hypotheses:
            for e in h.get('evidence', []):
                value = e.get('value', '')
                threshold = e.get('threshold', '')
                
                if threshold:
                    item = f"{e.get('metric', '')}: {value} (threshold: {threshold})"
                    item_zh = f"{e.get('metric', '')}：{value}（阈值：{threshold}）"
                else:
                    item = f"{e.get('metric', '')}: {value}"
                    item_zh = f"{e.get('metric', '')}：{value}"
                
                if item not in evidence_items:
                    evidence_items.append(item)
                    evidence_items_zh.append(item_zh)
        
        sources = diagnosis_result.get('data_sources', [])
        source_str = ', '.join(sources) if sources else 'Unknown'
        
        evidence = '\n'.join(evidence_items) if evidence_items else 'No specific evidence collected'
        evidence += f"\n\nData sources: {source_str}"
        
        evidence_zh = '\n'.join(evidence_items_zh) if evidence_items_zh else '未收集到具体证据'
        evidence_zh += f"\n\n数据来源：{source_str}"
        
        return evidence, evidence_zh
    
    def _estimate_resolution_time(self, alert_type: str, risk_level: str) -> tuple:
        """估计解决时间"""
        time_estimates = {
            ('miner_offline', 'high'): ('1-4 hours', '1-4 小时'),
            ('miner_offline', 'medium'): ('30 min - 2 hours', '30 分钟 - 2 小时'),
            ('miner_offline', 'low'): ('15-30 minutes', '15-30 分钟'),
            ('hashrate_low', 'high'): ('2-8 hours', '2-8 小时'),
            ('hashrate_low', 'medium'): ('1-4 hours', '1-4 小时'),
            ('temperature_high', 'high'): ('1-4 hours', '1-4 小时'),
            ('temperature_high', 'medium'): ('30 min - 2 hours', '30 分钟 - 2 小时'),
            ('hardware_error', 'high'): ('4-24 hours (may require parts)', '4-24 小时（可能需要配件）'),
        }
        
        key = (alert_type, risk_level)
        if key in time_estimates:
            return time_estimates[key]
        
        return ('1-4 hours (estimated)', '1-4 小时（预估）')
    
    def to_dict(self, draft: TicketDraft) -> Dict:
        """Convert TicketDraft to dict for API response"""
        return {
            'ticket_id': draft.ticket_id,
            'site_id': draft.site_id,
            'miner_ids': draft.miner_ids,
            'title': draft.title,
            'title_zh': draft.title_zh,
            'category': draft.category,
            'priority': draft.priority,
            'problem_description': draft.problem_description,
            'problem_description_zh': draft.problem_description_zh,
            'impact_scope': draft.impact_scope,
            'impact_scope_zh': draft.impact_scope_zh,
            'root_cause_analysis': draft.root_cause_analysis,
            'root_cause_analysis_zh': draft.root_cause_analysis_zh,
            'troubleshooting_steps': draft.troubleshooting_steps,
            'troubleshooting_steps_zh': draft.troubleshooting_steps_zh,
            'recommended_actions': draft.recommended_actions,
            'recommended_actions_zh': draft.recommended_actions_zh,
            'customer_confirmation_items': [
                {
                    'item': c.item,
                    'item_zh': c.item_zh,
                    'checked': c.checked,
                    'required': c.required,
                }
                for c in draft.customer_confirmation_items
            ],
            'evidence_summary': draft.evidence_summary,
            'evidence_summary_zh': draft.evidence_summary_zh,
            'estimated_resolution_time': draft.estimated_resolution_time,
            'estimated_resolution_time_zh': draft.estimated_resolution_time_zh,
            'generated_at': draft.generated_at,
            'data_sources': draft.data_sources,
        }


ticket_draft_service = AITicketDraftService()
