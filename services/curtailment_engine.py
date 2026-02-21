"""
Curtailment Engine v1 - AB Integration
Provides simulate, execute, and verify functions for power curtailment plans.
"""
import logging
import uuid
from datetime import datetime
from db import db
from models_ab import (ABCurtailmentPlan, ABCurtailmentAction, ABCurtailmentResult, 
                       MinerGroup, ABAuditLog)

logger = logging.getLogger(__name__)

class CurtailmentEngine:
    """v1 curtailment strategy engine"""
    
    # BTC price proxy for revenue estimation (simplified)
    DEFAULT_BTC_PRICE = 65000  # USD
    DEFAULT_HASHPRICE = 0.05   # USD per TH/s per day (simplified proxy)
    DEFAULT_WATTS_PER_TH = 30  # typical J/TH for modern ASICs
    
    @staticmethod
    def simulate(plan_id):
        """
        Simulate a curtailment plan: generate expected actions and savings estimate.
        Returns dict with 'actions' and 'expected' fields.
        Does NOT write to DB - only returns simulation result.
        """
        plan = ABCurtailmentPlan.query.get(plan_id)
        if not plan:
            return {'error': 'Plan not found'}
        if plan.status not in ('draft', 'ready'):
            return {'error': f'Plan status {plan.status} cannot be simulated'}
        
        inputs = plan.inputs_json or {}
        electricity_rate = inputs.get('electricity_rate', 0.06)  # $/kWh default
        min_online_pct = inputs.get('min_online_pct', 0.0)
        protected_groups = inputs.get('protected_groups', [])
        max_offline_groups = inputs.get('max_offline_groups', 999)
        duration_hours = inputs.get('duration_hours', 4)
        
        # Get groups for this plan's scope
        query = MinerGroup.query.filter_by(site_id=plan.site_id)
        if plan.tenant_scope == 'tenant_only' and plan.tenant_id:
            query = query.filter_by(tenant_id=plan.tenant_id)
        groups = query.order_by(MinerGroup.priority.asc()).all()
        
        actions = []
        total_watts = 0
        total_hashrate_th = 0
        groups_offline = 0
        
        for g in groups:
            if g.id in protected_groups:
                continue
            if groups_offline >= max_offline_groups:
                break
                
            selector = g.selector_json or {}
            # Estimate watts and hashrate from selector or defaults
            miner_count = selector.get('miner_count', 10)
            watts_per_miner = selector.get('watts_per_miner', 3000)
            hashrate_per_miner_th = selector.get('hashrate_per_miner_th', 100)
            
            group_watts = miner_count * watts_per_miner
            group_hashrate = miner_count * hashrate_per_miner_th
            
            cmd = 'power_off' if plan.objective != 'thermal_protect' else 'throttle'
            actions.append({
                'target_type': 'group',
                'target_id': g.id,
                'group_name': g.name,
                'command_type': cmd,
                'miner_count': miner_count,
                'watts': group_watts,
                'hashrate_th': group_hashrate
            })
            total_watts += group_watts
            total_hashrate_th += group_hashrate
            groups_offline += 1
        
        # Calculate expected savings
        kwh_saved = (total_watts / 1000.0) * duration_hours
        electricity_saved = kwh_saved * electricity_rate
        # Revenue lost: simplified hashrate * hashprice * duration_days
        duration_days = duration_hours / 24.0
        revenue_lost = total_hashrate_th * CurtailmentEngine.DEFAULT_HASHPRICE * duration_days
        
        expected = {
            'total_watts_reduced': total_watts,
            'total_hashrate_th_reduced': total_hashrate_th,
            'duration_hours': duration_hours,
            'expected_kwh_saved': round(kwh_saved, 2),
            'expected_electricity_saved_usd': round(electricity_saved, 2),
            'expected_revenue_lost_usd': round(revenue_lost, 2),
            'net_benefit_usd': round(electricity_saved - revenue_lost, 2),
            'groups_affected': len(actions),
            'note': 'Simplified estimation using hashprice proxy'
        }
        
        return {'actions': actions, 'expected': expected}
    
    @staticmethod
    def execute(plan_id, actor_user_id=None):
        """
        Execute a curtailment plan:
        1. Run simulation to get actions
        2. Create ABCurtailmentAction records  
        3. Create before_snapshot
        4. Update plan status to 'executing'
        5. Write audit log
        Returns dict with execution results.
        """
        plan = ABCurtailmentPlan.query.get(plan_id)
        if not plan:
            return {'error': 'Plan not found'}
        if plan.status not in ('draft', 'ready'):
            return {'error': f'Plan status {plan.status} cannot be executed'}
        
        # Run simulation
        sim = CurtailmentEngine.simulate(plan_id)
        if 'error' in sim:
            return sim
        
        request_id = str(uuid.uuid4())
        
        # Save expected to plan
        plan.expected_json = sim['expected']
        plan.status = 'executing'
        
        # Create before snapshot
        before_snapshot = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_site_watts': sum(a['watts'] for a in sim['actions']),
            'total_site_hashrate_th': sum(a['hashrate_th'] for a in sim['actions']),
            'groups': [{
                'group_id': a['target_id'],
                'group_name': a['group_name'],
                'watts': a['watts'],
                'hashrate_th': a['hashrate_th']
            } for a in sim['actions']]
        }
        
        # Create actions
        action_records = []
        for a in sim['actions']:
            action = ABCurtailmentAction(
                plan_id=plan.id,
                target_type=a['target_type'],
                target_id=a['target_id'],
                command_type=a['command_type'],
                command_payload_json={'miner_count': a.get('miner_count', 0)},
                status='sent'  # In real system would be 'queued' then 'sent'
            )
            db.session.add(action)
            action_records.append(action)
        
        # Create result with before snapshot
        result = ABCurtailmentResult(
            plan_id=plan.id,
            before_snapshot_json=before_snapshot
        )
        db.session.add(result)
        
        # Audit log
        audit = ABAuditLog(
            org_id=plan.org_id,
            tenant_id=plan.tenant_id,
            actor_user_id=actor_user_id,
            action_type='CURTAILMENT_EXECUTE',
            entity_type='curtailment_plan',
            entity_id=str(plan.id),
            request_id=request_id,
            detail_json={
                'plan_name': plan.name,
                'actions_count': len(sim['actions']),
                'expected': sim['expected']
            }
        )
        db.session.add(audit)
        
        db.session.commit()
        
        return {
            'plan_id': plan.id,
            'request_id': request_id,
            'status': 'executing',
            'actions_created': len(action_records),
            'expected': sim['expected'],
            'before_snapshot': before_snapshot
        }
    
    @staticmethod
    def verify(plan_id, actor_user_id=None):
        """
        Verify a curtailment plan execution:
        1. Check plan is in 'executing' status
        2. Generate after_snapshot (simulated: assume reduction achieved)
        3. Calculate actual delta
        4. Write curtailment_results
        5. Mark plan 'completed'
        6. Audit log
        """
        plan = ABCurtailmentPlan.query.get(plan_id)
        if not plan:
            return {'error': 'Plan not found'}
        if plan.status != 'executing':
            return {'error': f'Plan status {plan.status} cannot be verified'}
        
        result = ABCurtailmentResult.query.filter_by(plan_id=plan.id).first()
        if not result:
            return {'error': 'No execution result found'}
        
        before = result.before_snapshot_json or {}
        expected = plan.expected_json or {}
        
        # Simulate after snapshot (in real system, would query telemetry)
        after_snapshot = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_site_watts': 0,  # All targeted groups powered off
            'total_site_hashrate_th': 0,
            'groups': [{
                'group_id': g['group_id'],
                'group_name': g['group_name'],
                'watts': 0,
                'hashrate_th': 0
            } for g in before.get('groups', [])]
        }
        
        # Calculate actual
        actual_watts_reduced = before.get('total_site_watts', 0) - after_snapshot.get('total_site_watts', 0)
        actual_hashrate_reduced = before.get('total_site_hashrate_th', 0) - after_snapshot.get('total_site_hashrate_th', 0)
        
        actual = {
            'actual_watts_reduced': actual_watts_reduced,
            'actual_hashrate_th_reduced': actual_hashrate_reduced,
            'actual_kwh_saved': expected.get('expected_kwh_saved', 0),
            'target_met': actual_watts_reduced >= expected.get('total_watts_reduced', 0),
            'duration_hours': expected.get('duration_hours', 0),
            'verified_at': datetime.utcnow().isoformat()
        }
        
        result.after_snapshot_json = after_snapshot
        result.actual_json = actual
        
        # Update action statuses
        actions = ABCurtailmentAction.query.filter_by(plan_id=plan.id).all()
        for a in actions:
            a.status = 'acked'
            a.ack_json = {'verified': True, 'verified_at': datetime.utcnow().isoformat()}
        
        plan.status = 'completed'
        
        # Audit
        audit = ABAuditLog(
            org_id=plan.org_id,
            tenant_id=plan.tenant_id,
            actor_user_id=actor_user_id,
            action_type='CURTAILMENT_VERIFY',
            entity_type='curtailment_plan',
            entity_id=str(plan.id),
            detail_json={'actual': actual}
        )
        db.session.add(audit)
        
        db.session.commit()
        
        return {
            'plan_id': plan.id,
            'status': 'completed',
            'before_snapshot': before,
            'after_snapshot': after_snapshot,
            'actual': actual
        }
