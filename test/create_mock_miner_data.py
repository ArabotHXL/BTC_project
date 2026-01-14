#!/usr/bin/env python3
"""
Mock Data Generator for Testing "Add Miner" Functionality

This script creates mock data that can be used to test the "+ Add Miner" feature.
It generates realistic test data including serial numbers, IP addresses, and miner specifications.

Usage:
    conda activate snakeenv
    python test/create_mock_miner_data.py
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Import app and models
try:
    from app import app
    from db import db
    from models import HostingSite, MinerModel, UserAccess, HostingMiner
except ImportError:
    # Alternative import path
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import app
    from db import db
    from models import HostingSite, MinerModel, UserAccess, HostingMiner

# Mock data configurations
MOCK_MINER_MODELS = [
    {
        "model_name": "Antminer S19 Pro",
        "manufacturer": "Bitmain",
        "reference_hashrate": 110.0,  # TH/s
        "reference_power": 3250,  # W
        "reference_efficiency": 29.5,  # J/TH
    },
    {
        "model_name": "Antminer S19j Pro",
        "manufacturer": "Bitmain",
        "reference_hashrate": 104.0,
        "reference_power": 3068,
        "reference_efficiency": 29.5,
    },
    {
        "model_name": "WhatsMiner M30S++",
        "manufacturer": "MicroBT",
        "reference_hashrate": 112.0,
        "reference_power": 3472,
        "reference_efficiency": 31.0,
    },
    {
        "model_name": "WhatsMiner M31S+",
        "manufacturer": "MicroBT",
        "reference_hashrate": 82.0,
        "reference_power": 3360,
        "reference_efficiency": 41.0,
    },
    {
        "model_name": "AvalonMiner 1246",
        "manufacturer": "Canaan",
        "reference_hashrate": 90.0,
        "reference_power": 3420,
        "reference_efficiency": 38.0,
    },
]

def generate_serial_number(manufacturer, index):
    """Generate a realistic serial number"""
    prefixes = {
        "Bitmain": "BM",
        "MicroBT": "MB",
        "Canaan": "CA"
    }
    prefix = prefixes.get(manufacturer, "XX")
    year = datetime.now().year
    return f"{prefix}{year}{index:06d}"

def generate_ip_address(base="192.168.1"):
    """Generate a random IP address"""
    last_octet = random.randint(100, 254)
    return f"{base}.{last_octet}"

def generate_mac_address():
    """Generate a random MAC address"""
    return ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)])

def generate_rack_position():
    """Generate a rack position"""
    rack = random.choice(["A", "B", "C", "D"])
    row = random.randint(1, 10)
    position = random.randint(1, 20)
    return f"{rack}-{row:02d}-{position:02d}"

def create_mock_miner_data(count=10, site_id=None, customer_id=None, miner_model_id=None):
    """
    Create mock miner data for testing
    
    Args:
        count: Number of mock miners to generate
        site_id: Specific site ID (if None, will use first available)
        customer_id: Specific customer ID (if None, will use first available)
        miner_model_id: Specific miner model ID (if None, will randomize)
    
    Returns:
        List of miner data dictionaries
    """
    with app.app_context():
        # Get available sites
        sites = HostingSite.query.all()
        if not sites:
            print("⚠️  No hosting sites found. Please create a site first.")
            return []
        
        # Get available miner models
        miner_models = MinerModel.query.all()
        if not miner_models:
            print("⚠️  No miner models found. Creating default models...")
            for model_data in MOCK_MINER_MODELS:
                existing = MinerModel.query.filter_by(model_name=model_data["model_name"]).first()
                if not existing:
                    model = MinerModel(**model_data)
                    db.session.add(model)
            db.session.commit()
            miner_models = MinerModel.query.all()
        
        # Get available customers
        customers = UserAccess.query.filter(UserAccess.role.in_(['client', 'customer', 'user'])).all()
        if not customers:
            print("⚠️  No customers found. Using first user as customer...")
            customers = UserAccess.query.limit(1).all()
        
        # Use provided IDs or defaults
        selected_site_id = site_id or sites[0].id
        selected_customer_id = customer_id or (customers[0].id if customers else None)
        
        if not selected_customer_id:
            print("❌ No customer ID available. Cannot create mock data.")
            return []
        
        mock_data = []
        
        for i in range(count):
            # Select random miner model if not specified
            if miner_model_id:
                model = MinerModel.query.get(miner_model_id)
            else:
                model = random.choice(miner_models)
            
            if not model:
                continue
            
            # Generate realistic values with some variance
            base_hashrate = model.reference_hashrate
            base_power = model.reference_power
            
            # Add ±5% variance for realistic data
            hashrate_variance = random.uniform(-0.05, 0.05)
            power_variance = random.uniform(-0.05, 0.05)
            
            actual_hashrate = round(base_hashrate * (1 + hashrate_variance), 2)
            actual_power = round(base_power * (1 + power_variance), 0)
            
            # Generate serial number
            serial_number = generate_serial_number(model.manufacturer, i + 1)
            
            # Create miner data
            miner_data = {
                "site_id": selected_site_id,
                "customer_id": selected_customer_id,
                "miner_model_id": model.id,
                "serial_number": serial_number,
                "actual_hashrate": actual_hashrate,
                "actual_power": actual_power,
                "rack_position": generate_rack_position(),
                "ip_address": generate_ip_address(),
                "mac_address": generate_mac_address(),
                "notes": f"Mock test miner #{i+1} - {model.model_name}",
                "approval_notes": "Auto-generated test data"
            }
            
            mock_data.append(miner_data)
        
        return mock_data

def save_mock_data_to_file(mock_data, filename="mock_miner_data.json"):
    """Save mock data to JSON file"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'w') as f:
        json.dump(mock_data, f, indent=2)
    print(f"✅ Mock data saved to: {filepath}")
    return filepath

def print_mock_data(mock_data):
    """Print mock data in a readable format"""
    print("\n" + "="*80)
    print("📋 MOCK MINER DATA FOR TESTING")
    print("="*80)
    
    for i, miner in enumerate(mock_data, 1):
        print(f"\n🔧 Miner #{i}:")
        print(f"  Serial Number: {miner['serial_number']}")
        print(f"  Model ID: {miner['miner_model_id']}")
        print(f"  Site ID: {miner['site_id']}")
        print(f"  Customer ID: {miner['customer_id']}")
        print(f"  Hashrate: {miner['actual_hashrate']} TH/s")
        print(f"  Power: {miner['actual_power']} W")
        print(f"  IP Address: {miner.get('ip_address', 'N/A')}")
        print(f"  Rack Position: {miner.get('rack_position', 'N/A')}")
        print(f"  Notes: {miner.get('notes', 'N/A')}")
    
    print("\n" + "="*80)
    print(f"Total: {len(mock_data)} miners")
    print("="*80 + "\n")

def create_javascript_test_data(mock_data):
    """Create JavaScript code snippet for browser console testing"""
    js_code = """
// Copy and paste this into browser console to test "Add Miner" functionality

const mockMiners = """
    js_code += json.dumps(mock_data, indent=2)
    js_code += """;

// Test function to add a miner
async function testAddMiner(minerIndex = 0) {
    const miner = mockMiners[minerIndex];
    if (!miner) {
        console.error('Invalid miner index');
        return;
    }
    
    console.log('Testing Add Miner with:', miner);
    
    try {
        const response = await fetch('/hosting/api/miners', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(miner)
        });
        
        const result = await response.json();
        console.log('Result:', result);
        
        if (result.success) {
            console.log('✅ Miner added successfully!');
        } else {
            console.error('❌ Failed to add miner:', result.error);
        }
    } catch (error) {
        console.error('❌ Error:', error);
    }
}

// Usage:
// testAddMiner(0);  // Add first miner
// testAddMiner(1);  // Add second miner
"""
    return js_code

def main():
    """Main function"""
    print("🚀 Creating Mock Miner Data for Testing")
    print("="*80)
    
    # Use app context
    with app.app_context():
        # Check database connection
        try:
            db.session.execute(db.text("SELECT 1"))
            print("✅ Database connection successful")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return
        
        # Create mock data
        print("\n📝 Generating mock data...")
        mock_data = create_mock_miner_data(count=10)
        
        if not mock_data:
            print("❌ Failed to generate mock data")
            return
        
        # Print data
        print_mock_data(mock_data)
        
        # Save to file
        json_file = save_mock_data_to_file(mock_data)
        
        # Create JavaScript test code
        js_code = create_javascript_test_data(mock_data)
        js_file = os.path.join(os.path.dirname(__file__), "mock_miner_test.js")
        with open(js_file, 'w') as f:
            f.write(js_code)
        print(f"✅ JavaScript test code saved to: {js_file}")
        
        # Create CSV for batch import
        csv_file = os.path.join(os.path.dirname(__file__), "mock_miners_import.csv")
        with open(csv_file, 'w') as f:
            # Header
            f.write("serial_number,miner_model_id,site_id,customer_id,actual_hashrate,actual_power,ip_address,rack_position,notes\n")
            # Data
            for miner in mock_data:
                f.write(f"{miner['serial_number']},{miner['miner_model_id']},{miner['site_id']},{miner['customer_id']},{miner['actual_hashrate']},{miner['actual_power']},{miner.get('ip_address', '')},{miner.get('rack_position', '')},\"{miner.get('notes', '')}\"\n")
        print(f"✅ CSV import file saved to: {csv_file}")
        
        print("\n" + "="*80)
        print("📚 USAGE INSTRUCTIONS")
        print("="*80)
        print("\n1. JSON Format (for API testing):")
        print(f"   File: {json_file}")
        print("   Use this file to test the API endpoint directly")
        
        print("\n2. JavaScript Console (for browser testing):")
        print(f"   File: {js_file}")
        print("   Open browser console and paste the code from this file")
        print("   Then run: testAddMiner(0)")
        
        print("\n3. CSV Format (for batch import):")
        print(f"   File: {csv_file}")
        print("   Use this for batch import functionality")
        
        print("\n4. Manual Form Testing:")
        print("   Use the data above to manually fill the 'Add Miner' form")
        print("   Required fields:")
        print("   - Serial Number")
        print("   - Miner Model")
        print("   - Site")
        print("   - Customer Email")
        print("   Optional fields:")
        print("   - IP Address")
        print("   - Rack Position")
        print("   - Notes")
        print("\n" + "="*80)

if __name__ == "__main__":
    main()
