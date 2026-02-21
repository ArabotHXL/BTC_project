"""
Billing Service v1 - AB Integration
Generates invoices from contracts, tariffs, and usage records.
"""
import logging
import csv
import io
from datetime import datetime
from db import db
from models_ab import (ABInvoice, ABContract, ABUsageRecord, Tariff,
                       ABCurtailmentResult, ABCurtailmentPlan, ABAuditLog)

logger = logging.getLogger(__name__)

class BillingService:
    """Generates invoices from contracts and usage data"""
    
    @staticmethod
    def generate_invoice(contract_id, period_start, period_end, actor_user_id=None):
        """
        Generate a draft invoice for a contract and period.
        
        Steps:
        1. Load contract + tariff
        2. Find usage records for the period
        3. Calculate line items (electricity, hosting fee, curtailment credit)
        4. Create invoice record
        
        Returns: dict with invoice data
        """
        contract = ABContract.query.get(contract_id)
        if not contract:
            return {'error': 'Contract not found'}
        
        tariff = Tariff.query.get(contract.tariff_id) if contract.tariff_id else None
        
        # Get usage records
        usage_records = ABUsageRecord.query.filter_by(
            org_id=contract.org_id,
            site_id=contract.site_id,
            tenant_id=contract.tenant_id
        ).filter(
            ABUsageRecord.period_start >= period_start,
            ABUsageRecord.period_end <= period_end
        ).all()
        
        total_kwh = sum(u.kwh_estimated for u in usage_records)
        avg_kw = sum(u.avg_kw_estimated for u in usage_records) / max(len(usage_records), 1)
        
        # Determine electricity rate
        if tariff:
            params = tariff.params_json or {}
            rate = params.get('flat_rate', 0.06)
        else:
            rate = 0.06
        
        line_items = []
        
        # 1. Electricity cost
        electricity_cost = round(total_kwh * rate, 2)
        line_items.append({
            'type': 'electricity',
            'description': f'Electricity ({total_kwh:.2f} kWh @ ${rate}/kWh)',
            'quantity': round(total_kwh, 2),
            'unit_price': rate,
            'amount': electricity_cost
        })
        
        # 2. Hosting fee
        fee_params = contract.hosting_fee_params_json or {}
        hosting_fee = 0.0
        if contract.hosting_fee_type == 'per_kw':
            per_kw_rate = fee_params.get('rate', 50.0)
            hosting_fee = round(avg_kw * per_kw_rate, 2)
            line_items.append({
                'type': 'hosting_fee',
                'description': f'Hosting fee ({avg_kw:.2f} kW avg @ ${per_kw_rate}/kW)',
                'quantity': round(avg_kw, 2),
                'unit_price': per_kw_rate,
                'amount': hosting_fee
            })
        elif contract.hosting_fee_type == 'per_miner':
            per_miner_rate = fee_params.get('rate', 100.0)
            miner_count = fee_params.get('miner_count', 0)
            # Try to get miner count from usage evidence
            for u in usage_records:
                ev = u.evidence_json or {}
                if ev.get('total_miners', 0) > miner_count:
                    miner_count = ev['total_miners']
            hosting_fee = round(miner_count * per_miner_rate, 2)
            line_items.append({
                'type': 'hosting_fee',
                'description': f'Hosting fee ({miner_count} miners @ ${per_miner_rate}/miner)',
                'quantity': miner_count,
                'unit_price': per_miner_rate,
                'amount': hosting_fee
            })
        elif contract.hosting_fee_type == 'flat':
            flat_fee = fee_params.get('flat_fee', 0.0)
            hosting_fee = flat_fee
            line_items.append({
                'type': 'hosting_fee',
                'description': f'Hosting fee (flat)',
                'quantity': 1,
                'unit_price': flat_fee,
                'amount': hosting_fee
            })
        
        # 3. Curtailment credit (if applicable)
        curtailment_credit = 0.0
        if contract.curtailment_split_pct > 0:
            # Find completed curtailment plans in this period
            plans = ABCurtailmentPlan.query.filter(
                ABCurtailmentPlan.org_id == contract.org_id,
                ABCurtailmentPlan.site_id == contract.site_id,
                ABCurtailmentPlan.status == 'completed',
                ABCurtailmentPlan.created_at >= period_start,
                ABCurtailmentPlan.created_at <= period_end
            ).all()
            
            for p in plans:
                expected = p.expected_json or {}
                saved = expected.get('expected_electricity_saved_usd', 0)
                curtailment_credit += saved * (contract.curtailment_split_pct / 100.0)
            
            if curtailment_credit > 0:
                curtailment_credit = round(curtailment_credit, 2)
                line_items.append({
                    'type': 'curtailment_credit',
                    'description': f'Curtailment savings credit ({contract.curtailment_split_pct}% split)',
                    'quantity': 1,
                    'unit_price': -curtailment_credit,
                    'amount': -curtailment_credit
                })
        
        subtotal = electricity_cost + hosting_fee
        total = subtotal - curtailment_credit
        
        evidence = {
            'usage_record_ids': [u.id for u in usage_records],
            'total_kwh': round(total_kwh, 2),
            'avg_kw': round(avg_kw, 2),
            'tariff_id': tariff.id if tariff else None,
            'tariff_type': tariff.tariff_type if tariff else 'none',
            'electricity_rate': rate,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Check for existing invoice
        existing = ABInvoice.query.filter_by(
            contract_id=contract.id,
            period_start=period_start,
            period_end=period_end
        ).first()
        
        if existing:
            existing.subtotal = subtotal
            existing.total = round(total, 2)
            existing.line_items_json = line_items
            existing.evidence_json = evidence
            invoice = existing
        else:
            invoice = ABInvoice(
                org_id=contract.org_id,
                tenant_id=contract.tenant_id,
                contract_id=contract.id,
                period_start=period_start,
                period_end=period_end,
                subtotal=subtotal,
                total=round(total, 2),
                line_items_json=line_items,
                evidence_json=evidence
            )
            db.session.add(invoice)
        
        # Audit
        if actor_user_id:
            audit = ABAuditLog(
                org_id=contract.org_id,
                tenant_id=contract.tenant_id,
                actor_user_id=actor_user_id,
                action_type='BILLING_GENERATE',
                entity_type='invoice',
                entity_id=str(invoice.id) if invoice.id else 'new',
                detail_json={
                    'contract_id': contract.id,
                    'period': f'{period_start.isoformat()} to {period_end.isoformat()}',
                    'total': round(total, 2)
                }
            )
            db.session.add(audit)
        
        db.session.commit()
        
        return invoice.to_dict()
    
    @staticmethod
    def export_invoice_csv(invoice_id):
        """
        Export an invoice as CSV string.
        Returns: CSV string
        """
        invoice = ABInvoice.query.get(invoice_id)
        if not invoice:
            return None
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Invoice Export'])
        writer.writerow(['Invoice ID', invoice.id])
        writer.writerow(['Tenant ID', invoice.tenant_id])
        writer.writerow(['Period', f'{invoice.period_start.strftime("%Y-%m-%d")} to {invoice.period_end.strftime("%Y-%m-%d")}'])
        writer.writerow(['Status', invoice.status])
        writer.writerow([])
        writer.writerow(['Type', 'Description', 'Quantity', 'Unit Price', 'Amount'])
        
        for item in (invoice.line_items_json or []):
            writer.writerow([
                item.get('type', ''),
                item.get('description', ''),
                item.get('quantity', ''),
                item.get('unit_price', ''),
                item.get('amount', '')
            ])
        
        writer.writerow([])
        writer.writerow(['', '', '', 'Subtotal', invoice.subtotal])
        writer.writerow(['', '', '', 'Total', invoice.total])
        
        return output.getvalue()
