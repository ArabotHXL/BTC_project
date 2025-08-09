#!/usr/bin/env python3
"""
Seed script to create default subscription plans.
Run: python seed_plans.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from models import db
from models_subscription import Plan


def seed_plans():
    """Create default subscription plans."""
    with app.app_context():
        # Define plan configurations
        plans = [
            {
                'id': 'free',
                'name': 'Free',
                'price': 0,
                'max_miners': 1,
                'coins': 'BTC',
                'history_days': 7,
                'allow_api': False,
                'allow_scenarios': False,
                'allow_advanced_analytics': False
            },
            {
                'id': 'basic',
                'name': 'Basic',
                'price': 2900,  # $29 in cents
                'max_miners': 100,
                'coins': 'BTC,LTC,KAS,DOGE',
                'history_days': 30,
                'allow_api': False,
                'allow_scenarios': True,
                'allow_advanced_analytics': True
            },
            {
                'id': 'pro',
                'name': 'Pro',
                'price': 9900,  # $99 in cents
                'max_miners': 999999,
                'coins': 'BTC,LTC,KAS,DOGE,ETHPoW,BCH,ZEC,DASH',
                'history_days': 365,
                'allow_api': True,
                'allow_scenarios': True,
                'allow_advanced_analytics': True
            }
        ]
        
        # Create plans if they don't exist
        for plan_data in plans:
            existing_plan = Plan.query.get(plan_data['id'])
            if not existing_plan:
                plan = Plan(**plan_data)
                db.session.add(plan)
                print(f"Created plan: {plan_data['name']} ({plan_data['id']})")
            else:
                print(f"Plan already exists: {plan_data['name']} ({plan_data['id']})")
        
        db.session.commit()
        print("\n✅ Plans seeded successfully!")
        
        # Display plans
        print("\nCurrent plans:")
        for plan in Plan.query.all():
            print(f"  {plan.id}: {plan.name} - ${plan.price/100:.2f}/month")
            print(f"    Max miners: {plan.max_miners}")
            print(f"    History days: {plan.history_days}")
            print(f"    Features: API={plan.allow_api}, Scenarios={plan.allow_scenarios}, Analytics={plan.allow_advanced_analytics}")
            print()


if __name__ == '__main__':
    seed_plans()