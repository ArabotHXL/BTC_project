"""
托管证据包服务 (Hosting Evidence Package Service)
生成停机归因 + 时间线 + 审计链校验结果的证据包

功能:
- 停机分钟统计
- 事件时间线
- 指标快照
- 审计链校验结果
- CSV/JSON 导出
"""

import os
import json
import csv
import io
import zipfile
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class EvidencePackageService:
    """证据包生成服务"""
    
    VERSION = "1.0.0"
    
    def __init__(self):
        self.generated_at = None
    
    def generate_package(
        self,
        site_id: int,
        start_date: datetime,
        end_date: datetime,
        include_audit_verification: bool = True
    ) -> Dict[str, Any]:
        """
        生成证据包
        
        Args:
            site_id: 站点ID
            start_date: 开始日期
            end_date: 结束日期
            include_audit_verification: 是否包含审计链验证
        
        Returns:
            dict: 证据包数据
        """
        from db import db
        from models import HostingSite, HostingMiner, HostingEvent
        from models_control_plane import AuditEvent
        
        self.generated_at = datetime.utcnow()
        
        site = HostingSite.query.get(site_id)
        if not site:
            raise ValueError(f"Site {site_id} not found")
        
        package = {
            'metadata': {
                'version': self.VERSION,
                'generated_at': self.generated_at.isoformat(),
                'site_id': site_id,
                'site_name': site.name,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'generator': 'HashInsight Evidence Package Service'
            },
            'data_integrity': {
                'package_hash': None,
                'audit_chain_verified': None,
                'verification_details': None
            },
            'summary': {},
            'downtime_analysis': {},
            'event_timeline': [],
            'metrics_snapshot': {},
            'audit_events': []
        }
        
        package['summary'] = self._generate_summary(site_id, start_date, end_date)
        package['downtime_analysis'] = self._analyze_downtime(site_id, start_date, end_date)
        package['event_timeline'] = self._build_event_timeline(site_id, start_date, end_date)
        package['metrics_snapshot'] = self._capture_metrics_snapshot(site_id, start_date, end_date)
        
        if include_audit_verification:
            audit_result = self._verify_audit_chain(site_id, start_date, end_date)
            package['data_integrity']['audit_chain_verified'] = audit_result['passed']
            package['data_integrity']['verification_details'] = audit_result
            package['audit_events'] = self._get_audit_events(site_id, start_date, end_date)
        
        package_json = json.dumps(package, sort_keys=True, default=str)
        package['data_integrity']['package_hash'] = hashlib.sha256(package_json.encode()).hexdigest()
        
        return package
    
    def _generate_summary(self, site_id: int, start_date: datetime, end_date: datetime) -> Dict:
        """生成摘要统计"""
        from models import HostingMiner, HostingEvent
        
        total_miners = HostingMiner.query.filter_by(site_id=site_id).count()
        
        events = HostingEvent.query.filter(
            HostingEvent.site_id == site_id,
            HostingEvent.created_at >= start_date,
            HostingEvent.created_at <= end_date
        ).all()
        
        downtime_events = [e for e in events if e.event_type in ('OFFLINE', 'SHUTDOWN', 'ERROR')]
        
        period_hours = (end_date - start_date).total_seconds() / 3600
        
        return {
            'total_miners': total_miners,
            'period_hours': round(period_hours, 2),
            'total_events': len(events),
            'downtime_events': len(downtime_events),
            'event_breakdown': self._count_events_by_type(events)
        }
    
    def _count_events_by_type(self, events: List) -> Dict[str, int]:
        """按类型统计事件"""
        breakdown = {}
        for event in events:
            event_type = event.event_type or 'UNKNOWN'
            breakdown[event_type] = breakdown.get(event_type, 0) + 1
        return breakdown
    
    def _analyze_downtime(self, site_id: int, start_date: datetime, end_date: datetime) -> Dict:
        """分析停机时间"""
        from models import HostingEvent
        
        events = HostingEvent.query.filter(
            HostingEvent.site_id == site_id,
            HostingEvent.created_at >= start_date,
            HostingEvent.created_at <= end_date,
            HostingEvent.event_type.in_(['OFFLINE', 'SHUTDOWN', 'ERROR', 'ONLINE', 'STARTUP'])
        ).order_by(HostingEvent.created_at).all()
        
        downtime_periods = []
        miner_states = {}
        total_downtime_minutes = 0
        
        for event in events:
            miner_id = event.miner_id or event.miner_serial
            if not miner_id:
                continue
            
            if event.event_type in ('OFFLINE', 'SHUTDOWN', 'ERROR'):
                if miner_id not in miner_states or miner_states[miner_id]['status'] != 'offline':
                    miner_states[miner_id] = {
                        'status': 'offline',
                        'start_time': event.created_at,
                        'reason': event.event_type
                    }
            elif event.event_type in ('ONLINE', 'STARTUP'):
                if miner_id in miner_states and miner_states[miner_id]['status'] == 'offline':
                    start_time = miner_states[miner_id]['start_time']
                    duration_minutes = (event.created_at - start_time).total_seconds() / 60
                    total_downtime_minutes += duration_minutes
                    
                    downtime_periods.append({
                        'miner_id': str(miner_id),
                        'start_time': start_time.isoformat(),
                        'end_time': event.created_at.isoformat(),
                        'duration_minutes': round(duration_minutes, 2),
                        'reason': miner_states[miner_id]['reason']
                    })
                    
                    miner_states[miner_id] = {'status': 'online'}
        
        for miner_id, state in miner_states.items():
            if state.get('status') == 'offline':
                duration_minutes = (end_date - state['start_time']).total_seconds() / 60
                total_downtime_minutes += duration_minutes
                downtime_periods.append({
                    'miner_id': str(miner_id),
                    'start_time': state['start_time'].isoformat(),
                    'end_time': end_date.isoformat(),
                    'duration_minutes': round(duration_minutes, 2),
                    'reason': state['reason'],
                    'ongoing': True
                })
        
        downtime_by_reason = {}
        for period in downtime_periods:
            reason = period['reason']
            if reason not in downtime_by_reason:
                downtime_by_reason[reason] = {'count': 0, 'total_minutes': 0}
            downtime_by_reason[reason]['count'] += 1
            downtime_by_reason[reason]['total_minutes'] += period['duration_minutes']
        
        return {
            'total_downtime_minutes': round(total_downtime_minutes, 2),
            'total_downtime_hours': round(total_downtime_minutes / 60, 2),
            'downtime_periods_count': len(downtime_periods),
            'downtime_by_reason': downtime_by_reason,
            'downtime_periods': downtime_periods[:100]
        }
    
    def _build_event_timeline(self, site_id: int, start_date: datetime, end_date: datetime) -> List[Dict]:
        """构建事件时间线"""
        from models import HostingEvent
        
        events = HostingEvent.query.filter(
            HostingEvent.site_id == site_id,
            HostingEvent.created_at >= start_date,
            HostingEvent.created_at <= end_date
        ).order_by(HostingEvent.created_at).limit(1000).all()
        
        timeline = []
        for event in events:
            timeline.append({
                'timestamp': event.created_at.isoformat(),
                'event_type': event.event_type,
                'miner_id': event.miner_id or event.miner_serial,
                'description': event.description or '',
                'severity': getattr(event, 'severity', 'INFO'),
                'source': getattr(event, 'source', 'system')
            })
        
        return timeline
    
    def _capture_metrics_snapshot(self, site_id: int, start_date: datetime, end_date: datetime) -> Dict:
        """捕获指标快照"""
        from db import db
        from sqlalchemy import func, text
        
        try:
            from api.collector_api import MinerTelemetryLive
            
            live_stats = db.session.query(
                func.count(MinerTelemetryLive.id).label('miner_count'),
                func.avg(MinerTelemetryLive.hashrate_avg).label('avg_hashrate'),
                func.avg(MinerTelemetryLive.temperature_avg).label('avg_temperature'),
                func.sum(MinerTelemetryLive.power_avg).label('total_power')
            ).filter(MinerTelemetryLive.site_id == site_id).first()
            
            return {
                'capture_time': datetime.utcnow().isoformat(),
                'active_miners': live_stats.miner_count or 0,
                'average_hashrate_th': round(float(live_stats.avg_hashrate or 0), 2),
                'average_temperature_c': round(float(live_stats.avg_temperature or 0), 1),
                'total_power_kw': round(float(live_stats.total_power or 0) / 1000, 2)
            }
        except Exception as e:
            logger.warning(f"Failed to capture metrics snapshot: {e}")
            return {
                'capture_time': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def _verify_audit_chain(self, site_id: int, start_date: datetime, end_date: datetime) -> Dict:
        """验证审计链"""
        from models_control_plane import AuditEvent
        import hashlib
        import json
        
        events = AuditEvent.query.filter(
            AuditEvent.site_id == site_id,
            AuditEvent.created_at >= start_date,
            AuditEvent.created_at <= end_date
        ).order_by(AuditEvent.id.asc()).all()
        
        result = {
            'passed': True,
            'total_events': len(events),
            'verified_events': 0,
            'broken_links': [],
            'verification_time': datetime.utcnow().isoformat()
        }
        
        if len(events) == 0:
            result['message'] = 'No audit events in specified range'
            return result
        
        prev_hash = None
        for i, event in enumerate(events):
            if i > 0 and prev_hash and event.prev_hash != prev_hash:
                result['passed'] = False
                result['broken_links'].append({
                    'event_id': event.event_id,
                    'position': i,
                    'expected_prev_hash': prev_hash[:16] + '...',
                    'actual_prev_hash': (event.prev_hash[:16] + '...') if event.prev_hash else 'NULL'
                })
            
            prev_hash = event.event_hash
            result['verified_events'] += 1
        
        if result['passed']:
            result['message'] = f"All {result['verified_events']} events verified"
        else:
            result['message'] = f"Chain broken at {len(result['broken_links'])} points"
        
        return result
    
    def _get_audit_events(self, site_id: int, start_date: datetime, end_date: datetime) -> List[Dict]:
        """获取审计事件列表"""
        from models_control_plane import AuditEvent
        
        events = AuditEvent.query.filter(
            AuditEvent.site_id == site_id,
            AuditEvent.created_at >= start_date,
            AuditEvent.created_at <= end_date
        ).order_by(AuditEvent.created_at).limit(500).all()
        
        return [
            {
                'event_id': e.event_id,
                'timestamp': e.created_at.isoformat(),
                'event_type': e.event_type,
                'actor_type': e.actor_type,
                'actor_id': e.actor_id,
                'ref_type': e.ref_type,
                'ref_id': e.ref_id,
                'event_hash': e.event_hash[:16] + '...' if e.event_hash else None
            }
            for e in events
        ]
    
    def export_to_zip(self, package: Dict) -> bytes:
        """
        导出为 ZIP 文件
        
        Returns:
            bytes: ZIP 文件内容
        """
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('evidence_package.json', json.dumps(package, indent=2, default=str))
            
            zf.writestr('README.txt', self._generate_readme(package))
            
            if package.get('event_timeline'):
                csv_content = self._timeline_to_csv(package['event_timeline'])
                zf.writestr('event_timeline.csv', csv_content)
            
            if package.get('downtime_analysis', {}).get('downtime_periods'):
                csv_content = self._downtime_to_csv(package['downtime_analysis']['downtime_periods'])
                zf.writestr('downtime_periods.csv', csv_content)
            
            if package.get('audit_events'):
                csv_content = self._audit_to_csv(package['audit_events'])
                zf.writestr('audit_events.csv', csv_content)
            
            zf.writestr('data_integrity.json', json.dumps(package['data_integrity'], indent=2))
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    def _generate_readme(self, package: Dict) -> str:
        """生成 README 文件"""
        meta = package.get('metadata', {})
        integrity = package.get('data_integrity', {})
        summary = package.get('summary', {})
        downtime = package.get('downtime_analysis', {})
        
        return f"""HashInsight Evidence Package
============================

Site: {meta.get('site_name', 'Unknown')} (ID: {meta.get('site_id')})
Period: {meta.get('period_start')} to {meta.get('period_end')}
Generated: {meta.get('generated_at')}
Version: {meta.get('version')}

Summary
-------
Total Miners: {summary.get('total_miners', 0)}
Period Hours: {summary.get('period_hours', 0)}
Total Events: {summary.get('total_events', 0)}
Downtime Events: {summary.get('downtime_events', 0)}

Downtime Analysis
-----------------
Total Downtime: {downtime.get('total_downtime_minutes', 0)} minutes ({downtime.get('total_downtime_hours', 0)} hours)
Downtime Periods: {downtime.get('downtime_periods_count', 0)}

Data Integrity
--------------
Audit Chain Verified: {'PASS' if integrity.get('audit_chain_verified') else 'FAIL'}
Package Hash: {integrity.get('package_hash', 'N/A')}

Files Included
--------------
- evidence_package.json: Complete evidence data
- event_timeline.csv: Chronological event list
- downtime_periods.csv: Downtime period details
- audit_events.csv: Audit trail
- data_integrity.json: Verification results
- README.txt: This file

Verification
------------
To verify this package:
1. Recalculate SHA256 of evidence_package.json
2. Compare with package_hash in data_integrity.json
3. Run audit chain verification on audit_events

Note: This evidence package is for SLA reconciliation and dispute resolution.
"""
    
    def _timeline_to_csv(self, timeline: List[Dict]) -> str:
        """转换时间线为 CSV"""
        output = io.StringIO()
        if not timeline:
            return "No events"
        
        fieldnames = ['timestamp', 'event_type', 'miner_id', 'description', 'severity', 'source']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for event in timeline:
            writer.writerow({k: event.get(k, '') for k in fieldnames})
        
        return output.getvalue()
    
    def _downtime_to_csv(self, periods: List[Dict]) -> str:
        """转换停机周期为 CSV"""
        output = io.StringIO()
        if not periods:
            return "No downtime periods"
        
        fieldnames = ['miner_id', 'start_time', 'end_time', 'duration_minutes', 'reason', 'ongoing']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for period in periods:
            writer.writerow({k: period.get(k, '') for k in fieldnames})
        
        return output.getvalue()
    
    def _audit_to_csv(self, events: List[Dict]) -> str:
        """转换审计事件为 CSV"""
        output = io.StringIO()
        if not events:
            return "No audit events"
        
        fieldnames = ['event_id', 'timestamp', 'event_type', 'actor_type', 'actor_id', 'ref_type', 'ref_id', 'event_hash']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for event in events:
            writer.writerow({k: event.get(k, '') for k in fieldnames})
        
        return output.getvalue()


evidence_package_service = EvidencePackageService()
