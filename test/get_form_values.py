#!/usr/bin/env python3
"""
Get Database Values for Add Miner Form

This script queries the database to get actual values you can use
to fill in the "Add Miner" form.
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from app import app
from db import db
from models import HostingSite, MinerModel, UserAccess, HostingMiner

def get_form_values():
    """Get all values needed for the Add Miner form"""
    
    with app.app_context():
        print("="*80)
        print("📋 DATABASE VALUES FOR 'ADD MINER' FORM")
        print("="*80)
        
        # 1. Get Sites
        print("\n📍 SITES (Select one for 'Site' field):")
        print("-" * 80)
        sites = HostingSite.query.order_by(HostingSite.id).all()
        if sites:
            for site in sites:
                print(f"  ID: {site.id:3d} | Name: {site.name:30s} | Location: {site.location}")
        else:
            print("  ⚠️  No sites found in database!")
            print("  💡 You need to create a site first: Hosting → Site Management → Add Site")
        
        # 2. Get Miner Models
        print("\n🔧 MINER MODELS (Select one for 'Miner Model' field):")
        print("-" * 80)
        models = MinerModel.query.order_by(MinerModel.model_name).all()
        if models:
            for model in models:
                print(f"  Name: {model.model_name:30s} | Hashrate: {model.reference_hashrate:6.1f} TH/s | Power: {model.reference_power:5.0f} W")
        else:
            print("  ⚠️  No miner models found in database!")
            print("  💡 Run: python test/create_mock_miner_data.py (it will create models)")
        
        # 3. Get Customers/Users
        print("\n👤 CUSTOMERS (Enter email for 'Customer Email' field):")
        print("-" * 80)
        customers = UserAccess.query.filter(
            UserAccess.role.in_(['client', 'customer', 'user', 'owner'])
        ).order_by(UserAccess.email).all()
        
        if customers:
            for customer in customers:
                print(f"  ID: {customer.id:3d} | Email: {customer.email:40s} | Name: {customer.name or 'N/A'}")
        else:
            print("  ⚠️  No customers found in database!")
            print("  💡 You can use your own email if you're logged in")
        
        # 4. Get existing miners (to avoid duplicate serial numbers)
        print("\n🔢 EXISTING MINERS (Avoid these serial numbers):")
        print("-" * 80)
        existing_miners = HostingMiner.query.order_by(HostingMiner.serial_number).limit(10).all()
        if existing_miners:
            for miner in existing_miners:
                print(f"  Serial: {miner.serial_number:20s} | Model: {miner.miner_model.model_name if miner.miner_model else 'N/A'}")
        else:
            print("  ✅ No existing miners - you can use any serial number")
        
        # 5. Example form values
        print("\n" + "="*80)
        print("📝 EXAMPLE FORM VALUES (Copy and use these):")
        print("="*80)
        
        if sites and models and customers:
            example_site = sites[0]
            example_model = models[0]
            example_customer = customers[0]
            
            print(f"""
Serial Number:    BM2025{len(existing_miners)+1:06d}
Miner Model:      {example_model.model_name}
Site:             {example_site.name} (ID: {example_site.id})
Customer Email:   {example_customer.email}
IP Address:        192.168.1.{100 + len(existing_miners)}
Rack Position:    A-01-{len(existing_miners)+1:02d}
Notes:            Test miner #{len(existing_miners)+1}
            """)
        else:
            print("\n⚠️  Cannot generate example - missing required data!")
            if not sites:
                print("   - Create a site first")
            if not models:
                print("   - Create miner models first")
            if not customers:
                print("   - Create a customer/user first")
        
        print("="*80)
        print("\n💡 TIP: Use the values above to fill in the 'Add Miner' form")
        print("="*80)

if __name__ == "__main__":
    try:
        get_form_values()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
