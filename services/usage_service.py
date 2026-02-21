"""
Usage Service v1 - AB Integration
Estimates power usage per tenant/site for billing.
"""
import logging
from datetime import datetime
from db import db
from models_ab import ABUsageRecord, Tenant, ABAuditLog

logger = logging.getLogger(__name__)

class UsageService:
    """Estimates power consumption for billing purposes"""
    
    @staticmethod
    def generate_usage(org_id, site_id, tenant_id, period_start, period_end):
        """
        Generate usage record for a tenant at a site for a given period.
        
        Strategy:
        1. Try telemetry data (miner_telemetry_live) if available
        2. Fallback to nominal_watts * online_hours estimation
        
        Args:
            org_id: Organization ID
            site_id: Site (hosting_sites) ID
            tenant_id: Tenant ID
            period_start: datetime
            period_end: datetime
        
        Returns: dict with usage record data
        """
        from models_ab import MinerGroup
        
        # Calculate period duration
        duration = period_end - period_start
        duration_hours = duration.total_seconds() / 3600.0
        
        # Get groups for this tenant at this site
        groups = MinerGroup.query.filter_by(site_id=site_id, tenant_id=tenant_id).all()
        
        total_watts = 0
        total_miners = 0
        evidence_groups = []
        method = 'nominal_watts'
        
        for g in groups:
            selector = g.selector_json or {}
            miner_count = selector.get('miner_count', 0)
            watts_per_miner = selector.get('watts_per_miner', 3000)
            
            group_watts = miner_count * watts_per_miner
            total_watts += group_watts
            total_miners += miner_count
            
            evidence_groups.append({
                'group_id': g.id,
                'group_name': g.name,
                'miner_count': miner_count,
                'watts_per_miner': watts_per_miner,
                'total_watts': group_watts
            })
        
        # Try to get telemetry data
        try:
            from sqlalchemy import text
            result = db.session.execute(text("""
                SELECT AVG(power_consumption) as avg_watts, COUNT(*) as sample_count
                FROM miner_telemetry_live 
                WHERE site_id = :site_id 
                AND recorded_at BETWEEN :start AND :end
            """), {
                'site_id': str(site_id),
                'start': period_start,
                'end': period_end
            }).fetchone()
            
            if result and result.avg_watts and result.sample_count > 0:
                total_watts = float(result.avg_watts) * total_miners
                method = 'telemetry_watts'
                logger.info(f"Using telemetry data: {result.sample_count} samples")
        except Exception as e:
            logger.warning(f"Telemetry query failed, using nominal: {e}")
        
        # Calculate kWh
        avg_kw = total_watts / 1000.0
        kwh = avg_kw * duration_hours
        
        evidence = {
            'method': method,
            'duration_hours': round(duration_hours, 2),
            'total_miners': total_miners,
            'total_watts': total_watts,
            'groups': evidence_groups,
            'missing_rate': 0.0 if method == 'telemetry_watts' else 1.0,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Check for existing record
        existing = ABUsageRecord.query.filter_by(
            org_id=org_id, site_id=site_id, tenant_id=tenant_id,
            period_start=period_start, period_end=period_end
        ).first()
        
        if existing:
            existing.kwh_estimated = round(kwh, 2)
            existing.avg_kw_estimated = round(avg_kw, 2)
            existing.method = method
            existing.evidence_json = evidence
            record = existing
        else:
            record = ABUsageRecord(
                org_id=org_id,
                site_id=site_id,
                tenant_id=tenant_id,
                period_start=period_start,
                period_end=period_end,
                kwh_estimated=round(kwh, 2),
                avg_kw_estimated=round(avg_kw, 2),
                method=method,
                evidence_json=evidence
            )
            db.session.add(record)
        
        db.session.commit()
        
        return record.to_dict()
