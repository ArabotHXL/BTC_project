#!/usr/bin/env python3
"""
Generate demo telemetry data for Single Miner Dashboard
生成单矿机仪表板的演示数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random
import json

from app import app, db
from api.collector_api import MinerTelemetryLive, MinerTelemetryHistory


def generate_board_data(num_boards=3, overall_health='online'):
    """Generate realistic board-level health data"""
    boards = []
    for i in range(num_boards):
        if overall_health == 'online':
            health = random.choices(['A', 'B', 'C'], weights=[70, 25, 5])[0]
            chips_total = random.choice([76, 88, 114, 126])
            chips_ok = chips_total if health == 'A' else int(chips_total * random.uniform(0.85, 0.98))
            hashrate_ths = random.uniform(35, 42) if health in ['A', 'B'] else random.uniform(25, 35)
            temp_c = random.uniform(58, 72) if health in ['A', 'B'] else random.uniform(72, 82)
        elif overall_health == 'warning':
            health = random.choices(['B', 'C', 'D'], weights=[30, 50, 20])[0]
            chips_total = random.choice([76, 88, 114])
            chips_ok = int(chips_total * random.uniform(0.70, 0.90))
            hashrate_ths = random.uniform(25, 35)
            temp_c = random.uniform(70, 85)
        else:
            health = random.choices(['C', 'D', 'F'], weights=[20, 40, 40])[0]
            chips_total = random.choice([76, 88])
            chips_ok = int(chips_total * random.uniform(0.50, 0.75))
            hashrate_ths = random.uniform(10, 25)
            temp_c = random.uniform(75, 90)
        
        boards.append({
            "index": i,
            "hashrate_ths": round(hashrate_ths, 2),
            "temp_c": round(temp_c, 1),
            "chips_ok": chips_ok,
            "chips_total": chips_total,
            "health": health
        })
    return boards


def generate_live_telemetry(miner_serial, site_id, model_name, status='online'):
    """Generate realistic live telemetry data for a miner"""
    now = datetime.utcnow()
    
    if status == 'online':
        hashrate_ghs = random.uniform(95000, 115000)
        hashrate_expected = 110000
        temp_avg = random.uniform(62, 68)
        temp_min = temp_avg - random.uniform(3, 8)
        temp_max = temp_avg + random.uniform(5, 12)
        power = random.uniform(3100, 3400)
        online = True
        overall_health = 'online'
        boards = generate_board_data(3, 'online')
        boards_healthy = sum(1 for b in boards if b['health'] in ['A', 'B'])
    elif status == 'warning':
        hashrate_ghs = random.uniform(70000, 90000)
        hashrate_expected = 110000
        temp_avg = random.uniform(72, 78)
        temp_min = temp_avg - random.uniform(2, 5)
        temp_max = temp_avg + random.uniform(8, 15)
        power = random.uniform(3200, 3500)
        online = True
        overall_health = 'warning'
        boards = generate_board_data(3, 'warning')
        boards_healthy = sum(1 for b in boards if b['health'] in ['A', 'B'])
    else:
        hashrate_ghs = 0
        hashrate_expected = 110000
        temp_avg = 0
        temp_min = 0
        temp_max = 0
        power = 0
        online = False
        overall_health = 'offline'
        boards = []
        boards_healthy = 0
    
    return {
        'miner_id': miner_serial,
        'site_id': site_id,
        'ip_address': f'192.168.1.{random.randint(10, 250)}',
        'online': online,
        'last_seen': now if online else now - timedelta(hours=random.randint(1, 24)),
        'hashrate_ghs': round(hashrate_ghs, 2),
        'hashrate_5s_ghs': round(hashrate_ghs * random.uniform(0.95, 1.05), 2),
        'hashrate_expected_ghs': hashrate_expected,
        'temperature_avg': round(temp_avg, 1),
        'temperature_min': round(temp_min, 1),
        'temperature_max': round(temp_max, 1),
        'temperature_chips': [round(temp_avg + random.uniform(-5, 5), 1) for _ in range(9)],
        'fan_speeds': [random.randint(4500, 6000) for _ in range(4)],
        'frequency_avg': random.uniform(580, 620),
        'accepted_shares': random.randint(50000, 200000),
        'rejected_shares': random.randint(50, 500),
        'hardware_errors': random.randint(0, 20),
        'uptime_seconds': random.randint(86400, 864000),
        'power_consumption': round(power, 0),
        'efficiency': round(power / (hashrate_ghs / 1000) if hashrate_ghs > 0 else 0, 1),
        'pool_url': 'stratum+tcp://btc.f2pool.com:3333',
        'worker_name': f'farm01.{miner_serial}',
        'pool_latency_ms': round(random.uniform(15, 45), 1),
        'boards_data': boards,
        'boards_total': len(boards),
        'boards_healthy': boards_healthy,
        'overall_health': overall_health,
        'model': model_name,
        'firmware_version': 'Antminer-S19-Pro-2023.12.15',
        'error_message': None if online else 'Connection timeout',
        'latency_ms': round(random.uniform(5, 25), 1),
        'updated_at': now
    }


def generate_history_data(miner_serial, site_id, hours=24):
    """Generate 24h historical telemetry data"""
    now = datetime.utcnow()
    history = []
    
    for h in range(hours, 0, -1):
        timestamp = now - timedelta(hours=h)
        
        time_factor = 1.0
        if 0 <= timestamp.hour < 6:
            time_factor = 0.95
        elif 6 <= timestamp.hour < 12:
            time_factor = 1.02
        elif 12 <= timestamp.hour < 18:
            time_factor = 0.98
        else:
            time_factor = 1.0
        
        random_factor = random.uniform(0.92, 1.08)
        base_hashrate = 105000 * time_factor * random_factor
        
        base_temp = 65 + (timestamp.hour - 12) * 0.3
        temp_avg = base_temp + random.uniform(-3, 3)
        
        power = 3250 + random.uniform(-100, 100)
        
        btc_price = 95000
        difficulty = 90e12
        daily_btc = (base_hashrate * 1e9) / difficulty * 144 * 6.25
        hourly_btc = daily_btc / 24
        revenue_usd = hourly_btc * btc_price
        electricity_cost = power / 1000 * 0.08
        net_profit = revenue_usd - electricity_cost
        
        history.append({
            'miner_id': miner_serial,
            'site_id': site_id,
            'timestamp': timestamp,
            'hashrate_ghs': round(base_hashrate, 2),
            'temperature_avg': round(temp_avg, 1),
            'temperature_min': round(temp_avg - random.uniform(3, 6), 1),
            'temperature_max': round(temp_avg + random.uniform(5, 10), 1),
            'fan_speed_avg': random.randint(5000, 5500),
            'power_consumption': round(power, 0),
            'accepted_shares': random.randint(2000, 5000),
            'rejected_shares': random.randint(5, 30),
            'online': True,
            'boards_healthy': 3,
            'boards_total': 3,
            'overall_health': 'online',
            'net_profit_usd': round(net_profit, 4),
            'revenue_usd': round(revenue_usd, 4)
        })
    
    return history


def main():
    """Main function to generate demo data"""
    print("=" * 60)
    print("🔧 Generating Demo Telemetry Data / 生成演示遥测数据")
    print("=" * 60)
    
    miners_config = [
        {'id': 134, 'serial': 'S19PRO-00115', 'site_id': 5, 'model': 'Antminer S19 Pro', 'status': 'online'},
        {'id': 131, 'serial': 'S19PRO-00112', 'site_id': 5, 'model': 'Antminer S19 Pro', 'status': 'online'},
        {'id': 132, 'serial': 'S19PRO-00113', 'site_id': 5, 'model': 'Antminer S19 Pro', 'status': 'warning'},
        {'id': 133, 'serial': 'S19PRO-00114', 'site_id': 5, 'model': 'Antminer S19 Pro', 'status': 'offline'},
        {'id': 135, 'serial': 'S19PRO-00116', 'site_id': 5, 'model': 'Antminer S19 Pro', 'status': 'online'},
    ]
    
    with app.app_context():
        for miner in miners_config:
            print(f"\n📊 Processing {miner['serial']} ({miner['status']})...")
            
            existing = MinerTelemetryLive.query.filter_by(
                miner_id=miner['serial'],
                site_id=miner['site_id']
            ).first()
            
            if existing:
                print(f"   Updating existing live telemetry...")
                live_data = generate_live_telemetry(
                    miner['serial'], 
                    miner['site_id'], 
                    miner['model'], 
                    miner['status']
                )
                for key, value in live_data.items():
                    setattr(existing, key, value)
            else:
                print(f"   Creating new live telemetry...")
                live_data = generate_live_telemetry(
                    miner['serial'], 
                    miner['site_id'], 
                    miner['model'], 
                    miner['status']
                )
                telemetry = MinerTelemetryLive(**live_data)
                db.session.add(telemetry)
            
            if miner['status'] != 'offline':
                MinerTelemetryHistory.query.filter_by(
                    miner_id=miner['serial'],
                    site_id=miner['site_id']
                ).delete()
                
                print(f"   Generating 24h history data...")
                history_data = generate_history_data(miner['serial'], miner['site_id'])
                for record in history_data:
                    history = MinerTelemetryHistory(**record)
                    db.session.add(history)
                print(f"   ✅ Added {len(history_data)} history records")
        
        db.session.commit()
        print("\n" + "=" * 60)
        print("✅ Demo data generation completed! / 演示数据生成完成！")
        print("=" * 60)
        
        live_count = MinerTelemetryLive.query.filter(
            MinerTelemetryLive.site_id == 5
        ).count()
        history_count = MinerTelemetryHistory.query.filter(
            MinerTelemetryHistory.site_id == 5
        ).count()
        
        print(f"\n📈 Statistics / 统计:")
        print(f"   Live telemetry records: {live_count}")
        print(f"   History records: {history_count}")
        print(f"\n🔗 View miner dashboard at: /hosting/miner/134/detail")


if __name__ == '__main__':
    main()
