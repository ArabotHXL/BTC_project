#!/usr/bin/env python3
"""
快速批量更新HashPower MegaFarm的矿机CGMiner数据
使用SQL批量更新，速度更快
"""

import sys
import os
import random
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db

def main():
    with app.app_context():
        print("正在批量更新CGMiner数据...")
        
        # 方案：直接使用SQL UPDATE语句批量更新
        # 1. 为active矿机设置在线数据
        # 2. 为offline矿机设置离线状态
        
        # 获取矿机总数
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as total, status 
            FROM hosting_miners 
            WHERE site_id = 5 
            GROUP BY status
        """))
        
        stats = list(result)
        print("\n矿机统计：")
        for row in stats:
            print(f"  {row.status}: {row.total}")
        
        # 更新active矿机为在线状态
        print("\n更新active矿机...")
        db.session.execute(db.text("""
            UPDATE hosting_miners
            SET 
                cgminer_online = true,
                temperature_avg = 60 + random() * 20,
                temperature_max = 70 + random() * 20,
                fan_avg = 4000 + (random() * 2000)::int,
                reject_rate = random() * 2,
                hardware_errors = (random() * 5)::int,
                uptime_seconds = 86400 + (random() * 30 * 86400)::int,
                accepted_shares = 50000 + (random() * 50000)::int,
                rejected_shares = (random() * 1000)::int,
                last_seen = NOW(),
                pool_url = 'stratum+tcp://btc.pool.com:3333',
                pool_worker = 'hashpower.' || serial_number
            WHERE site_id = 5 AND status = 'active'
        """))
        
        # 更新offline矿机为离线状态
        print("更新offline矿机...")
        db.session.execute(db.text("""
            UPDATE hosting_miners
            SET 
                cgminer_online = false,
                last_seen = NOW() - interval '10 minutes' * (random() * 144)::int
            WHERE site_id = 5 AND status = 'offline'
        """))
        
        # 更新maintenance矿机为离线状态
        print("更新maintenance矿机...")
        db.session.execute(db.text("""
            UPDATE hosting_miners
            SET 
                cgminer_online = false,
                last_seen = NOW() - interval '1 hour'
            WHERE site_id = 5 AND status = 'maintenance'
        """))
        
        db.session.commit()
        
        # 验证结果
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as online_count 
            FROM hosting_miners 
            WHERE site_id = 5 AND cgminer_online = true
        """))
        online_count = result.scalar()
        
        print(f"\n✓ 完成！")
        print(f"  在线矿机: {online_count}")
        print(f"  更新时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

if __name__ == '__main__':
    main()
