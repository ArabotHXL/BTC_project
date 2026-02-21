#!/usr/bin/env python3
"""
AB Integration - Database Initialization
Creates tables, default org/tenant, and operator admin user.
Idempotent: safe to run multiple times.
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def init_db():
    from app import app
    from db import db
    import models_ab  # ensure models are registered
    
    with app.app_context():
        # Create all new tables
        from models_ab import (Org, Tenant, MinerGroup, ABAuditLog, 
                               ABCurtailmentPlan, ABCurtailmentAction, ABCurtailmentResult,
                               Tariff, ABContract, ABUsageRecord, ABInvoice)
        
        # Only create tables that don't exist yet
        db.create_all()
        logger.info("All AB tables created/verified")
        
        # Check if self org exists
        self_org = Org.query.filter_by(org_type='self').first()
        if not self_org:
            self_org = Org(name='HashInsight Self-Mining', org_type='self')
            db.session.add(self_org)
            db.session.flush()
            logger.info(f"Created self org: {self_org.name} (id={self_org.id})")
        else:
            logger.info(f"Self org already exists: {self_org.name} (id={self_org.id})")
        
        # Check if self tenant exists
        self_tenant = Tenant.query.filter_by(org_id=self_org.id, tenant_type='self').first()
        if not self_tenant:
            self_tenant = Tenant(
                org_id=self_org.id,
                name='Self-Mining Operations',
                tenant_type='self',
                status='active'
            )
            db.session.add(self_tenant)
            db.session.flush()
            logger.info(f"Created self tenant: {self_tenant.name} (id={self_tenant.id})")
        else:
            logger.info(f"Self tenant already exists: {self_tenant.name} (id={self_tenant.id})")
        
        # Create operator admin user
        from models import UserAccess
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@local')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        admin = UserAccess.query.filter_by(email=admin_email).first()
        if not admin:
            admin = UserAccess(
                name='Operator Admin',
                email=admin_email,
                role='owner',
                username='operator_admin'
            )
            admin.set_password(admin_password)
            admin.is_active = True
            admin.is_email_verified = True
            db.session.add(admin)
            db.session.flush()
            logger.info(f"Created operator admin: {admin_email} (id={admin.id})")
        else:
            logger.info(f"Admin user already exists: {admin_email} (id={admin.id})")
        
        # Write audit log
        audit = ABAuditLog(
            org_id=self_org.id,
            actor_user_id=admin.id if admin else None,
            action_type='SYSTEM_INIT',
            entity_type='system',
            entity_id='init_db',
            detail_json={
                'org_id': self_org.id,
                'tenant_id': self_tenant.id,
                'admin_email': admin_email
            }
        )
        db.session.add(audit)
        
        db.session.commit()
        logger.info("Database initialization complete!")
        
        return {
            'org_id': self_org.id,
            'tenant_id': self_tenant.id,
            'admin_email': admin_email
        }

if __name__ == '__main__':
    result = init_db()
    print(f"\nInitialization result: {result}")
