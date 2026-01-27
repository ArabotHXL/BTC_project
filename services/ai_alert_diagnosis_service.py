"""
AI Alert Diagnosis Service
AI 告警诊断服务

功能:
- 接入 telemetry_service 获取 live/history 数据
- 接入最近命令/重启记录
- 输出 Top3 根因假设 + 证据 + 建议验证动作

应用场景:
- 告警解释（离线/算力下降）
- 减少值班人员"看图猜原因"的时间
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from db import db
from services.telemetry_service import TelemetryService

logger = logging.getLogger(__name__)


@dataclass
class Evidence:
    """证据项"""
    metric: str
    description: str
    description_zh: str
    value: Any
    threshold: Optional[Any] = None
    deviation_pct: Optional[float] = None
    timestamp: Optional[str] = None


@dataclass
class SuggestedAction:
    """建议验证动作"""
    action: str
    action_zh: str
    priority: int
    reason: str
    reason_zh: str
    command_type: Optional[str] = None
    parameters: Optional[Dict] = None


@dataclass
class RootCauseHypothesis:
    """根因假设"""
    hypothesis_id: str
    cause: str
    cause_zh: str
    confidence: float
    evidence: List[Evidence]
    suggested_actions: List[SuggestedAction]
    risk_level: str = "medium"


@dataclass
class DiagnosisResult:
    """诊断结果"""
    alert_id: Optional[str]
    miner_id: str
    site_id: int
    alert_type: str
    diagnosed_at: str
    hypotheses: List[RootCauseHypothesis]
    summary: str
    summary_zh: str
    data_sources: List[str]
    

class AIAlertDiagnosisService:
    """AI 告警诊断服务
    
    输入：live + history（hashrate/temps/fans/reject/pool latency）+ 最近命令/重启记录
    输出：Top3 根因假设 + 每个假设的证据 + 建议验证动作
    """
    
    HASHRATE_DROP_THRESHOLD = 0.2
    TEMPERATURE_HIGH_THRESHOLD = 75
    TEMPERATURE_CRITICAL_THRESHOLD = 85
    REJECT_RATE_HIGH_THRESHOLD = 0.02
    POOL_LATENCY_HIGH_THRESHOLD = 200
    FAN_SPEED_LOW_THRESHOLD = 2000
    OFFLINE_MINUTES_THRESHOLD = 5
    
    def __init__(self):
        self.telemetry_service = TelemetryService()
    
    def diagnose_alert(
        self,
        site_id: int,
        miner_id: str,
        alert_type: str,
        alert_id: Optional[str] = None,
    ) -> DiagnosisResult:
        """诊断单个告警
        
        Args:
            site_id: 站点ID
            miner_id: 矿机ID
            alert_type: 告警类型 (offline, hashrate_low, temperature_high, etc.)
            alert_id: 告警ID（可选）
        
        Returns:
            DiagnosisResult 包含 Top3 根因假设
        """
        now = datetime.utcnow()
        
        live_data = self._get_live_data(site_id, miner_id)
        history_data = self._get_history_data(site_id, miner_id, hours=24)
        recent_commands = self._get_recent_commands(site_id, miner_id, hours=24)
        
        data_sources = ['miner_telemetry_live', 'telemetry_history_5min']
        if recent_commands:
            data_sources.append('remote_commands')
        
        hypotheses = self._generate_hypotheses(
            alert_type=alert_type,
            live_data=live_data,
            history_data=history_data,
            recent_commands=recent_commands,
        )
        
        hypotheses = sorted(hypotheses, key=lambda h: h.confidence, reverse=True)[:3]
        
        if hypotheses:
            main_cause = hypotheses[0].cause_zh
            confidence_pct = int(hypotheses[0].confidence * 100)
            summary = f"Most likely cause: {hypotheses[0].cause} ({confidence_pct}% confidence)"
            summary_zh = f"最可能原因：{main_cause}（置信度 {confidence_pct}%）"
        else:
            summary = "Unable to determine root cause with available data"
            summary_zh = "无法根据现有数据确定根因，建议人工排查"
        
        return DiagnosisResult(
            alert_id=alert_id,
            miner_id=miner_id,
            site_id=site_id,
            alert_type=alert_type,
            diagnosed_at=now.isoformat(),
            hypotheses=hypotheses,
            summary=summary,
            summary_zh=summary_zh,
            data_sources=data_sources,
        )
    
    def diagnose_batch(
        self,
        site_id: int,
        alert_type: str,
        miner_ids: Optional[List[str]] = None,
    ) -> Dict[str, DiagnosisResult]:
        """批量诊断多台矿机
        
        适用于批量离线等场景
        """
        results = {}
        
        if miner_ids:
            for miner_id in miner_ids:
                results[miner_id] = self.diagnose_alert(
                    site_id=site_id,
                    miner_id=miner_id,
                    alert_type=alert_type,
                )
        
        return results
    
    def _get_live_data(self, site_id: int, miner_id: str) -> Optional[Dict]:
        """获取实时数据"""
        try:
            miners = self.telemetry_service.get_live(site_id=site_id, miner_id=miner_id)
            return miners[0] if miners else None
        except Exception as e:
            logger.warning(f"Failed to get live data: {e}")
            return None
    
    def _get_history_data(self, site_id: int, miner_id: str, hours: int = 24) -> Dict:
        """获取历史数据"""
        try:
            end = datetime.utcnow()
            start = end - timedelta(hours=hours)
            return self.telemetry_service.get_history(
                site_id=site_id,
                start=start,
                end=end,
                miner_id=miner_id,
                resolution='5min',
            )
        except Exception as e:
            logger.warning(f"Failed to get history data: {e}")
            return {'series': []}
    
    def _get_recent_commands(self, site_id: int, miner_id: str, hours: int = 24) -> List[Dict]:
        """获取最近命令记录"""
        try:
            from models_remote_control import RemoteCommand
            
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            commands = RemoteCommand.query.filter(
                RemoteCommand.site_id == site_id,
                RemoteCommand.created_at >= cutoff,
            ).order_by(RemoteCommand.created_at.desc()).limit(20).all()
            
            return [
                {
                    'id': cmd.id,
                    'type': cmd.command_type,
                    'status': cmd.status,
                    'created_at': cmd.created_at.isoformat() if cmd.created_at else None,
                    'completed_at': cmd.completed_at.isoformat() if cmd.completed_at else None,
                }
                for cmd in commands
                if not miner_id or (cmd.target_ids and miner_id in cmd.target_ids)
            ]
        except Exception as e:
            logger.warning(f"Failed to get recent commands: {e}")
            return []
    
    def _generate_hypotheses(
        self,
        alert_type: str,
        live_data: Optional[Dict],
        history_data: Dict,
        recent_commands: List[Dict],
    ) -> List[RootCauseHypothesis]:
        """生成根因假设"""
        hypotheses = []
        
        if alert_type in ('miner_offline', 'offline'):
            hypotheses.extend(self._diagnose_offline(live_data, history_data, recent_commands))
        
        elif alert_type in ('hashrate_low', 'hashrate_drop'):
            hypotheses.extend(self._diagnose_hashrate_issue(live_data, history_data, recent_commands))
        
        elif alert_type in ('temperature_high', 'temperature_critical'):
            hypotheses.extend(self._diagnose_temperature_issue(live_data, history_data))
        
        elif alert_type == 'hardware_error':
            hypotheses.extend(self._diagnose_hardware_issue(live_data, history_data))
        
        else:
            hypotheses.extend(self._diagnose_generic(alert_type, live_data, history_data))
        
        return hypotheses
    
    def _diagnose_offline(
        self,
        live_data: Optional[Dict],
        history_data: Dict,
        recent_commands: List[Dict],
    ) -> List[RootCauseHypothesis]:
        """诊断离线问题"""
        hypotheses = []
        
        reboot_commands = [c for c in recent_commands if c['type'] in ('REBOOT', 'POWER_OFF', 'reboot', 'power_off')]
        if reboot_commands:
            last_reboot = reboot_commands[0]
            hypotheses.append(RootCauseHypothesis(
                hypothesis_id='recent_command',
                cause='Recent reboot/power command still in progress',
                cause_zh='最近执行了重启/关机命令，矿机正在恢复中',
                confidence=0.85,
                risk_level='low',
                evidence=[
                    Evidence(
                        metric='recent_command',
                        description=f"Command {last_reboot['type']} executed",
                        description_zh=f"执行了 {last_reboot['type']} 命令",
                        value=last_reboot['type'],
                        timestamp=last_reboot['created_at'],
                    ),
                ],
                suggested_actions=[
                    SuggestedAction(
                        action='Wait for miner to complete boot sequence (3-5 minutes)',
                        action_zh='等待矿机完成启动流程（3-5分钟）',
                        priority=1,
                        reason='Miner may still be booting after command',
                        reason_zh='矿机可能仍在启动中',
                    ),
                    SuggestedAction(
                        action='Check command execution status',
                        action_zh='检查命令执行状态',
                        priority=2,
                        reason='Verify command completed successfully',
                        reason_zh='确认命令是否成功执行',
                    ),
                ],
            ))
        
        if history_data.get('series'):
            series = history_data['series'][0]['data'] if history_data['series'] else []
            if len(series) >= 2:
                recent_temps = [p['temp_c'] for p in series[-12:] if p.get('temp_c')]
                if recent_temps and max(recent_temps) > self.TEMPERATURE_CRITICAL_THRESHOLD:
                    hypotheses.append(RootCauseHypothesis(
                        hypothesis_id='thermal_shutdown',
                        cause='Thermal protection shutdown triggered',
                        cause_zh='触发温度保护自动关机',
                        confidence=0.75,
                        risk_level='high',
                        evidence=[
                            Evidence(
                                metric='temperature',
                                description=f"Temperature reached {max(recent_temps)}°C before offline",
                                description_zh=f"离线前温度达到 {max(recent_temps)}°C",
                                value=max(recent_temps),
                                threshold=self.TEMPERATURE_CRITICAL_THRESHOLD,
                            ),
                        ],
                        suggested_actions=[
                            SuggestedAction(
                                action='Check cooling system and ambient temperature',
                                action_zh='检查散热系统和环境温度',
                                priority=1,
                                reason='High temperature indicates cooling issue',
                                reason_zh='高温说明散热存在问题',
                            ),
                            SuggestedAction(
                                action='Wait for temperature to normalize, then power on',
                                action_zh='等待温度正常后再开机',
                                priority=2,
                                reason='Allow time for thermal recovery',
                                reason_zh='让设备充分冷却',
                                command_type='POWER_ON',
                            ),
                        ],
                    ))
        
        hypotheses.append(RootCauseHypothesis(
            hypothesis_id='network_issue',
            cause='Network connectivity issue',
            cause_zh='网络连接问题',
            confidence=0.60,
            risk_level='medium',
            evidence=[
                Evidence(
                    metric='connectivity',
                    description='Miner not responding to telemetry requests',
                    description_zh='矿机未响应遥测请求',
                    value='no_response',
                ),
            ],
            suggested_actions=[
                SuggestedAction(
                    action='Ping miner IP address',
                    action_zh='Ping 矿机 IP 地址',
                    priority=1,
                    reason='Verify basic network connectivity',
                    reason_zh='验证基本网络连通性',
                ),
                SuggestedAction(
                    action='Check switch port status and cable connection',
                    action_zh='检查交换机端口状态和网线连接',
                    priority=2,
                    reason='Physical network issues are common',
                    reason_zh='物理网络问题较为常见',
                ),
                SuggestedAction(
                    action='Check if PSU indicator lights are on',
                    action_zh='检查电源指示灯是否亮起',
                    priority=3,
                    reason='Rule out power supply failure',
                    reason_zh='排除电源故障可能',
                ),
            ],
        ))
        
        hypotheses.append(RootCauseHypothesis(
            hypothesis_id='power_failure',
            cause='Power supply or PDU issue',
            cause_zh='电源或配电问题',
            confidence=0.50,
            risk_level='high',
            evidence=[
                Evidence(
                    metric='power_status',
                    description='Miner unresponsive - possible power issue',
                    description_zh='矿机无响应 - 可能是电源问题',
                    value='unknown',
                ),
            ],
            suggested_actions=[
                SuggestedAction(
                    action='Check PDU/breaker status for this row',
                    action_zh='检查该排 PDU/断路器状态',
                    priority=1,
                    reason='Power distribution issues affect multiple miners',
                    reason_zh='配电问题通常影响多台矿机',
                ),
                SuggestedAction(
                    action='Verify PSU LED indicators',
                    action_zh='检查电源 LED 指示灯',
                    priority=2,
                    reason='PSU failure is a common cause',
                    reason_zh='电源故障是常见原因',
                ),
            ],
        ))
        
        return hypotheses
    
    def _diagnose_hashrate_issue(
        self,
        live_data: Optional[Dict],
        history_data: Dict,
        recent_commands: List[Dict],
    ) -> List[RootCauseHypothesis]:
        """诊断算力问题"""
        hypotheses = []
        
        if live_data:
            current_hashrate = live_data.get('hashrate', {}).get('value', 0)
            expected_hashrate = live_data.get('hashrate', {}).get('expected_ths', 0)
            temperature = live_data.get('temperature', {}).get('max', 0)
            reject_rate = live_data.get('shares', {}).get('reject_rate', 0)
            pool_latency = live_data.get('pool', {}).get('latency_ms', 0)
            
            if temperature and temperature > self.TEMPERATURE_HIGH_THRESHOLD:
                drop_pct = (expected_hashrate - current_hashrate) / expected_hashrate * 100 if expected_hashrate > 0 else 0
                hypotheses.append(RootCauseHypothesis(
                    hypothesis_id='thermal_throttling',
                    cause='Thermal throttling due to high temperature',
                    cause_zh='高温导致降频保护',
                    confidence=0.85,
                    risk_level='high',
                    evidence=[
                        Evidence(
                            metric='temperature',
                            description=f"Max temperature {temperature}°C exceeds threshold",
                            description_zh=f"最高温度 {temperature}°C 超过阈值",
                            value=temperature,
                            threshold=self.TEMPERATURE_HIGH_THRESHOLD,
                        ),
                        Evidence(
                            metric='hashrate_drop',
                            description=f"Hashrate dropped {drop_pct:.1f}% from expected",
                            description_zh=f"算力比预期下降 {drop_pct:.1f}%",
                            value=current_hashrate,
                            threshold=expected_hashrate,
                            deviation_pct=drop_pct,
                        ),
                    ],
                    suggested_actions=[
                        SuggestedAction(
                            action='Check fan speeds and replace failed fans',
                            action_zh='检查风扇转速，更换故障风扇',
                            priority=1,
                            reason='Fan failure often causes thermal throttling',
                            reason_zh='风扇故障常导致降频',
                        ),
                        SuggestedAction(
                            action='Clean dust filters and heatsinks',
                            action_zh='清洁防尘网和散热片',
                            priority=2,
                            reason='Dust accumulation reduces cooling efficiency',
                            reason_zh='积灰会降低散热效率',
                        ),
                        SuggestedAction(
                            action='Check ambient temperature and ventilation',
                            action_zh='检查环境温度和通风情况',
                            priority=3,
                            reason='Environmental factors affect cooling',
                            reason_zh='环境因素影响散热',
                        ),
                    ],
                ))
            
            if reject_rate and reject_rate > self.REJECT_RATE_HIGH_THRESHOLD:
                hypotheses.append(RootCauseHypothesis(
                    hypothesis_id='high_reject_rate',
                    cause='High share rejection rate from pool',
                    cause_zh='矿池拒绝率过高',
                    confidence=0.80,
                    risk_level='medium',
                    evidence=[
                        Evidence(
                            metric='reject_rate',
                            description=f"Reject rate {reject_rate*100:.2f}% exceeds normal",
                            description_zh=f"拒绝率 {reject_rate*100:.2f}% 超过正常值",
                            value=reject_rate,
                            threshold=self.REJECT_RATE_HIGH_THRESHOLD,
                        ),
                    ],
                    suggested_actions=[
                        SuggestedAction(
                            action='Check network latency to pool',
                            action_zh='检查到矿池的网络延迟',
                            priority=1,
                            reason='High latency causes stale shares',
                            reason_zh='高延迟导致过期份额',
                        ),
                        SuggestedAction(
                            action='Switch to backup pool if latency is high',
                            action_zh='如延迟高则切换备用矿池',
                            priority=2,
                            reason='Alternative pool may have better connectivity',
                            reason_zh='备用矿池可能连接更好',
                            command_type='SWITCH_POOL',
                        ),
                    ],
                ))
            
            if pool_latency and pool_latency > self.POOL_LATENCY_HIGH_THRESHOLD:
                hypotheses.append(RootCauseHypothesis(
                    hypothesis_id='pool_connectivity',
                    cause='Pool connectivity issue causing efficiency loss',
                    cause_zh='矿池连接问题导致效率下降',
                    confidence=0.75,
                    risk_level='medium',
                    evidence=[
                        Evidence(
                            metric='pool_latency',
                            description=f"Pool latency {pool_latency}ms is high",
                            description_zh=f"矿池延迟 {pool_latency}ms 偏高",
                            value=pool_latency,
                            threshold=self.POOL_LATENCY_HIGH_THRESHOLD,
                        ),
                    ],
                    suggested_actions=[
                        SuggestedAction(
                            action='Test connectivity to current pool',
                            action_zh='测试当前矿池连通性',
                            priority=1,
                            reason='Verify pool is reachable',
                            reason_zh='确认矿池可达',
                        ),
                        SuggestedAction(
                            action='Consider switching to geographically closer pool',
                            action_zh='考虑切换到距离更近的矿池',
                            priority=2,
                            reason='Geographic proximity reduces latency',
                            reason_zh='更近的矿池延迟更低',
                            command_type='SWITCH_POOL',
                        ),
                    ],
                ))
            
            boards_healthy = live_data.get('hardware', {}).get('boards_healthy', 0)
            boards_total = live_data.get('hardware', {}).get('boards_total', 0)
            if boards_total > 0 and boards_healthy < boards_total:
                failed_boards = boards_total - boards_healthy
                hypotheses.append(RootCauseHypothesis(
                    hypothesis_id='board_failure',
                    cause=f'{failed_boards} hash board(s) not working',
                    cause_zh=f'{failed_boards} 个算力板故障',
                    confidence=0.90,
                    risk_level='high',
                    evidence=[
                        Evidence(
                            metric='board_status',
                            description=f"Only {boards_healthy}/{boards_total} boards active",
                            description_zh=f"仅 {boards_healthy}/{boards_total} 个算力板正常",
                            value=boards_healthy,
                            threshold=boards_total,
                        ),
                    ],
                    suggested_actions=[
                        SuggestedAction(
                            action='Check board status in miner web interface',
                            action_zh='在矿机管理界面查看算力板状态',
                            priority=1,
                            reason='Identify which board has failed',
                            reason_zh='确认是哪个算力板故障',
                        ),
                        SuggestedAction(
                            action='Try reboot to reset board initialization',
                            action_zh='尝试重启以重新初始化算力板',
                            priority=2,
                            reason='Sometimes boards recover after reboot',
                            reason_zh='有时重启可以恢复算力板',
                            command_type='REBOOT',
                        ),
                        SuggestedAction(
                            action='Schedule maintenance to replace faulty board',
                            action_zh='安排维修更换故障算力板',
                            priority=3,
                            reason='Hardware replacement may be needed',
                            reason_zh='可能需要更换硬件',
                        ),
                    ],
                ))
        
        if not hypotheses:
            hypotheses.append(RootCauseHypothesis(
                hypothesis_id='general_performance',
                cause='General performance degradation - needs investigation',
                cause_zh='性能下降原因不明 - 需进一步排查',
                confidence=0.40,
                risk_level='medium',
                evidence=[
                    Evidence(
                        metric='hashrate',
                        description='Hashrate below expected level',
                        description_zh='算力低于预期水平',
                        value='low',
                    ),
                ],
                suggested_actions=[
                    SuggestedAction(
                        action='Check miner logs for errors',
                        action_zh='检查矿机日志是否有错误',
                        priority=1,
                        reason='Logs may reveal specific issues',
                        reason_zh='日志可能显示具体问题',
                    ),
                    SuggestedAction(
                        action='Try reboot to clear potential software issues',
                        action_zh='尝试重启清除潜在软件问题',
                        priority=2,
                        reason='Reboot often resolves transient issues',
                        reason_zh='重启常能解决临时问题',
                        command_type='REBOOT',
                    ),
                ],
            ))
        
        return hypotheses
    
    def _diagnose_temperature_issue(
        self,
        live_data: Optional[Dict],
        history_data: Dict,
    ) -> List[RootCauseHypothesis]:
        """诊断温度问题"""
        hypotheses = []
        
        if live_data:
            temp_max = live_data.get('temperature', {}).get('max', 0)
            
            hypotheses.append(RootCauseHypothesis(
                hypothesis_id='fan_failure',
                cause='Fan failure or reduced fan speed',
                cause_zh='风扇故障或转速下降',
                confidence=0.80,
                risk_level='high',
                evidence=[
                    Evidence(
                        metric='temperature',
                        description=f"Temperature {temp_max}°C is elevated",
                        description_zh=f"温度 {temp_max}°C 偏高",
                        value=temp_max,
                        threshold=self.TEMPERATURE_HIGH_THRESHOLD,
                    ),
                ],
                suggested_actions=[
                    SuggestedAction(
                        action='Check all fan speeds in miner dashboard',
                        action_zh='在矿机仪表板检查所有风扇转速',
                        priority=1,
                        reason='Identify failed or slow fans',
                        reason_zh='找出故障或慢转风扇',
                    ),
                    SuggestedAction(
                        action='Replace failed fans immediately',
                        action_zh='立即更换故障风扇',
                        priority=2,
                        reason='Prevent thermal damage to chips',
                        reason_zh='防止芯片热损坏',
                    ),
                ],
            ))
            
            hypotheses.append(RootCauseHypothesis(
                hypothesis_id='environmental',
                cause='High ambient temperature or poor ventilation',
                cause_zh='环境温度高或通风不良',
                confidence=0.65,
                risk_level='medium',
                evidence=[
                    Evidence(
                        metric='temperature',
                        description='Elevated chip temperature detected',
                        description_zh='检测到芯片温度升高',
                        value=temp_max,
                    ),
                ],
                suggested_actions=[
                    SuggestedAction(
                        action='Check room ambient temperature',
                        action_zh='检查机房环境温度',
                        priority=1,
                        reason='High ambient affects all miners',
                        reason_zh='高环境温度影响所有矿机',
                    ),
                    SuggestedAction(
                        action='Improve air circulation in the area',
                        action_zh='改善该区域空气流通',
                        priority=2,
                        reason='Better airflow reduces operating temp',
                        reason_zh='更好的气流降低运行温度',
                    ),
                ],
            ))
            
            hypotheses.append(RootCauseHypothesis(
                hypothesis_id='dust_accumulation',
                cause='Dust accumulation blocking airflow',
                cause_zh='积灰堵塞气流',
                confidence=0.55,
                risk_level='medium',
                evidence=[
                    Evidence(
                        metric='maintenance',
                        description='Gradual temperature increase suggests dust',
                        description_zh='温度逐渐升高表明可能积灰',
                        value='suspected',
                    ),
                ],
                suggested_actions=[
                    SuggestedAction(
                        action='Schedule cleaning of dust filters',
                        action_zh='安排清洁防尘网',
                        priority=1,
                        reason='Regular cleaning prevents buildup',
                        reason_zh='定期清洁防止积灰',
                    ),
                    SuggestedAction(
                        action='Blow out heatsinks with compressed air',
                        action_zh='用压缩空气清理散热片',
                        priority=2,
                        reason='Clean heatsinks improve heat dissipation',
                        reason_zh='干净的散热片散热更好',
                    ),
                ],
            ))
        
        return hypotheses
    
    def _diagnose_hardware_issue(
        self,
        live_data: Optional[Dict],
        history_data: Dict,
    ) -> List[RootCauseHypothesis]:
        """诊断硬件问题"""
        hypotheses = []
        
        if live_data:
            hw_errors = live_data.get('hardware', {}).get('errors', 0)
            boards_healthy = live_data.get('hardware', {}).get('boards_healthy', 0)
            boards_total = live_data.get('hardware', {}).get('boards_total', 0)
            
            if hw_errors and hw_errors > 100:
                hypotheses.append(RootCauseHypothesis(
                    hypothesis_id='chip_degradation',
                    cause='ASIC chip degradation or failure',
                    cause_zh='ASIC 芯片老化或故障',
                    confidence=0.75,
                    risk_level='high',
                    evidence=[
                        Evidence(
                            metric='hardware_errors',
                            description=f"High hardware error count: {hw_errors}",
                            description_zh=f"硬件错误计数高: {hw_errors}",
                            value=hw_errors,
                        ),
                    ],
                    suggested_actions=[
                        SuggestedAction(
                            action='Identify which chips have high error rates',
                            action_zh='确认哪些芯片错误率高',
                            priority=1,
                            reason='Locate failing components',
                            reason_zh='定位故障组件',
                        ),
                        SuggestedAction(
                            action='Consider lowering frequency to reduce errors',
                            action_zh='考虑降频以减少错误',
                            priority=2,
                            reason='Lower frequency may stabilize operation',
                            reason_zh='降频可能稳定运行',
                            command_type='ADJUST_FREQUENCY',
                            parameters={'direction': 'decrease'},
                        ),
                    ],
                ))
            
            if boards_total > 0 and boards_healthy < boards_total:
                hypotheses.append(RootCauseHypothesis(
                    hypothesis_id='board_connection',
                    cause='Hash board connection or cable issue',
                    cause_zh='算力板连接或线缆问题',
                    confidence=0.70,
                    risk_level='medium',
                    evidence=[
                        Evidence(
                            metric='board_status',
                            description=f"{boards_total - boards_healthy} board(s) not detected",
                            description_zh=f"{boards_total - boards_healthy} 个算力板未检测到",
                            value=boards_healthy,
                            threshold=boards_total,
                        ),
                    ],
                    suggested_actions=[
                        SuggestedAction(
                            action='Check data cable connections to control board',
                            action_zh='检查连接控制板的数据线',
                            priority=1,
                            reason='Loose cables cause board detection issues',
                            reason_zh='松动的线缆导致检测问题',
                        ),
                        SuggestedAction(
                            action='Reseat hash board connectors',
                            action_zh='重新插拔算力板接口',
                            priority=2,
                            reason='Reseating often fixes connection issues',
                            reason_zh='重新插拔常能修复连接问题',
                        ),
                    ],
                ))
        
        return hypotheses
    
    def _diagnose_generic(
        self,
        alert_type: str,
        live_data: Optional[Dict],
        history_data: Dict,
    ) -> List[RootCauseHypothesis]:
        """通用诊断"""
        return [
            RootCauseHypothesis(
                hypothesis_id='generic_issue',
                cause=f'Alert type {alert_type} requires manual investigation',
                cause_zh=f'告警类型 {alert_type} 需要人工排查',
                confidence=0.30,
                risk_level='medium',
                evidence=[
                    Evidence(
                        metric='alert_type',
                        description=f"Alert triggered: {alert_type}",
                        description_zh=f"触发告警: {alert_type}",
                        value=alert_type,
                    ),
                ],
                suggested_actions=[
                    SuggestedAction(
                        action='Review miner logs and status',
                        action_zh='查看矿机日志和状态',
                        priority=1,
                        reason='Manual investigation needed',
                        reason_zh='需要人工排查',
                    ),
                ],
            ),
        ]
    
    def to_dict(self, result: DiagnosisResult) -> Dict:
        """Convert DiagnosisResult to dict for API response"""
        return {
            'alert_id': result.alert_id,
            'miner_id': result.miner_id,
            'site_id': result.site_id,
            'alert_type': result.alert_type,
            'diagnosed_at': result.diagnosed_at,
            'summary': result.summary,
            'summary_zh': result.summary_zh,
            'data_sources': result.data_sources,
            'hypotheses': [
                {
                    'hypothesis_id': h.hypothesis_id,
                    'cause': h.cause,
                    'cause_zh': h.cause_zh,
                    'confidence': h.confidence,
                    'risk_level': h.risk_level,
                    'evidence': [
                        {
                            'metric': e.metric,
                            'description': e.description,
                            'description_zh': e.description_zh,
                            'value': e.value,
                            'threshold': e.threshold,
                            'deviation_pct': e.deviation_pct,
                            'timestamp': e.timestamp,
                        }
                        for e in h.evidence
                    ],
                    'suggested_actions': [
                        {
                            'action': a.action,
                            'action_zh': a.action_zh,
                            'priority': a.priority,
                            'reason': a.reason,
                            'reason_zh': a.reason_zh,
                            'command_type': a.command_type,
                            'parameters': a.parameters,
                        }
                        for a in h.suggested_actions
                    ],
                }
                for h in result.hypotheses
            ],
        }


alert_diagnosis_service = AIAlertDiagnosisService()
