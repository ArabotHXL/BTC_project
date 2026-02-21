"""
Usage Service v1 - HI Integration
Estimates power usage per tenant/site for billing.
"""
import logging
from datetime import datetime
from db import db
from models_hi import HiUsageRecord, HiTenant, HiAuditLog, HiGroup

logger = logging.getLogger(__name__)

class UsageService:
    """Estimates power consumption for billing purposes"""
    
    @staticmethod
    def generate_usage(org_id, site_id, tenant_id, period_start, period_end):
        """
        Generate usage record for a tenant at a site for a given period.
        
        Strategy:
        1. Try telemetry data (miner_telemetry_live) if available
        2. Fallback to miners.nominal_watts sum (via Miner model)
        3. Last resort: selector_json miner_count * watts_per_miner estimation
        
        Args:
            org_id: Organization ID
            site_id: Site (hosting_sites) ID
            tenant_id: Tenant ID
            period_start: datetime
            period_end: datetime
        
        Returns: dict with usage record data
        """
        duration = period_end - period_start
        duration_hours = duration.total_seconds() / 3600.0
        
        groups = HiGroup.query.filter_by(site_id=site_id, tenant_id=tenant_id).all()
        
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
        
        fallback_selector_watts = total_watts
        
        try:
            from sqlalchemy import text
            result = db.session.execute(text("""
                SELECT AVG(t.power_consumption) as avg_watts, COUNT(*) as sample_count
                FROM miner_telemetry_live t
                JOIN miners m ON t.miner_id = m.miner_id
                WHERE t.site_id = :site_id 
                AND m.hi_tenant_id = :tenant_id
                AND t.recorded_at BETWEEN :start AND :end
            """), {
                'site_id': str(site_id),
                'tenant_id': tenant_id,
                'start': period_start,
                'end': period_end
            }).fetchone()
            
            if result and result.avg_watts and result.sample_count > 0:
                total_watts = float(result.avg_watts) * total_miners
                method = 'telemetry_watts'
                logger.info(f"Using telemetry data: {result.sample_count} samples")
        except Exception as e:
            logger.warning(f"Telemetry query failed, trying nominal_watts: {e}")
        
        if method != 'telemetry_watts':
            try:
                from models import Miner
                from sqlalchemy import func, cast, Integer
                nominal_sum = db.session.query(
                    func.sum(Miner.nominal_watts),
                    func.count(Miner.id)
                ).filter(
                    cast(Miner.site_id, Integer) == int(site_id),
                    Miner.hi_tenant_id == tenant_id,
                    Miner.nominal_watts.isnot(None)
                ).first()
                
                if nominal_sum and nominal_sum[0] and nominal_sum[0] > 0:
                    total_watts = float(nominal_sum[0])
                    total_miners = int(nominal_sum[1]) if nominal_sum[1] else total_miners
                    method = 'nominal_watts'
                    logger.info(f"Using miners.nominal_watts: {total_watts}W from {total_miners} miners")
                else:
                    total_watts = fallback_selector_watts
                    method = 'nominal_watts'
                    logger.info("No nominal_watts data found, using selector_json fallback")
            except Exception as e:
                logger.warning(f"Miner nominal_watts query failed, using selector fallback: {e}")
                total_watts = fallback_selector_watts
                method = 'nominal_watts'
        
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
        
        existing = HiUsageRecord.query.filter_by(
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
            record = HiUsageRecord(
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
