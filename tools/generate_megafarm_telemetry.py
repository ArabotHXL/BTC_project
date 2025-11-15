#!/usr/bin/env python3
"""
为HashPower MegaFarm 20MW场地的矿机生成模拟CGMiner telemetry数据

直接更新HostingMiner表的CGMiner字段，同时插入MinerTelemetry历史记录

Usage:
    python tools/generate_megafarm_telemetry.py
"""

import sys
import os
import random
import json
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import HostingMiner, MinerTelemetry, MinerModel

def generate_online_telemetry(miner):
    """为在线矿机生成telemetry数据"""
    
    # 获取矿机型号的额定算力和功耗
    miner_model = db.session.get(MinerModel, miner.miner_model_id)
    rated_hashrate = miner_model.reference_hashrate if miner_model else 110.0
    rated_power = miner_model.reference_power if miner_model else 3250.0
    
    # 算力在额定值的95%-105%之间波动
    hashrate = rated_hashrate * random.uniform(0.95, 1.05)
    
    # 功耗在额定值的95%-105%之间波动
    power = rated_power * random.uniform(0.95, 1.05)
    
    # 温度在合理范围内
    temp_avg = random.uniform(60, 80)
    temp_max = temp_avg + random.uniform(5, 15)
    
    # 风扇转速 (通常3个风扇)
    fan_speeds = [
        random.randint(3000, 6000),
        random.randint(3000, 6000),
        random.randint(3000, 6000)
    ]
    fan_avg = int(sum(fan_speeds) / len(fan_speeds))
    
    # 拒绝率通常很低
    reject_rate = random.uniform(0.1, 2.0)
    
    # 硬件错误数
    hardware_errors = random.randint(0, 5)
    
    # 运行时间 (1-30天)
    uptime_seconds = random.randint(86400, 30 * 86400)
    
    # 接受/拒绝的份额
    total_shares = random.randint(10000, 100000)
    rejected_shares = int(total_shares * reject_rate / 100)
    accepted_shares = total_shares - rejected_shares
    
    # 矿池信息
    pool_urls = [
        'stratum+tcp://btc.pool.com:3333',
        'stratum+tcp://btc.f2pool.com:3333',
        'stratum+tcp://btc.antpool.com:3333',
        'stratum+tcp://btc.viabtc.com:3333'
    ]
    pool_url = random.choice(pool_urls)
    pool_worker = f"hashpower.{miner.serial_number}"
    
    return {
        'hashrate': hashrate,
        'power': power,
        'temperature_avg': round(temp_avg, 1),
        'temperature_max': round(temp_max, 1),
        'fan_speeds': json.dumps(fan_speeds),
        'fan_avg': fan_avg,
        'reject_rate': round(reject_rate, 2),
        'hardware_errors': hardware_errors,
        'cgminer_online': True,
        'pool_url': pool_url,
        'pool_worker': pool_worker,
        'uptime_seconds': uptime_seconds,
        'hashrate_5s': round(hashrate, 2),
        'accepted_shares': accepted_shares,
        'rejected_shares': rejected_shares,
        'last_seen': datetime.utcnow()
    }

def generate_offline_telemetry():
    """为离线矿机生成telemetry数据"""
    return {
        'temperature_avg': None,
        'temperature_max': None,
        'fan_speeds': None,
        'fan_avg': None,
        'reject_rate': None,
        'hardware_errors': None,
        'cgminer_online': False,
        'pool_url': None,
        'pool_worker': None,
        'uptime_seconds': None,
        'hashrate_5s': None,
        'accepted_shares': None,
        'rejected_shares': None,
        'last_seen': datetime.utcnow() - timedelta(minutes=random.randint(10, 1440))
    }

def update_miner_telemetry(miner):
    """更新矿机的CGMiner telemetry数据"""
    
    is_online = miner.status == 'active'
    
    if is_online:
        data = generate_online_telemetry(miner)
        
        # 更新HostingMiner表
        miner.temperature_avg = data['temperature_avg']
        miner.temperature_max = data['temperature_max']
        miner.fan_speeds = data['fan_speeds']
        miner.fan_avg = data['fan_avg']
        miner.reject_rate = data['reject_rate']
        miner.hardware_errors = data['hardware_errors']
        miner.cgminer_online = data['cgminer_online']
        miner.pool_url = data['pool_url']
        miner.pool_worker = data['pool_worker']
        miner.uptime_seconds = data['uptime_seconds']
        miner.hashrate_5s = data['hashrate_5s']
        miner.accepted_shares = data['accepted_shares']
        miner.rejected_shares = data['rejected_shares']
        miner.last_seen = data['last_seen']
        
        return data
    else:
        data = generate_offline_telemetry()
        
        # 更新HostingMiner表
        miner.cgminer_online = data['cgminer_online']
        miner.last_seen = data['last_seen']
        
        return None

def insert_telemetry_history(miner, telemetry_data, hours=24):
    """插入MinerTelemetry历史记录"""
    
    if not telemetry_data:  # 离线矿机不插入历史记录
        return 0
    
    records_inserted = 0
    
    # 每小时插入一条历史记录
    for i in range(hours):
        time_offset = datetime.utcnow() - timedelta(hours=hours - i)
        
        # 检查是否已存在该时间点的记录（按小时去重）
        existing = MinerTelemetry.query.filter_by(
            miner_id=miner.id
        ).filter(
            MinerTelemetry.recorded_at >= time_offset - timedelta(minutes=30),
            MinerTelemetry.recorded_at <= time_offset + timedelta(minutes=30)
        ).first()
        
        if existing:
            continue
        
        # 插入历史记录
        telemetry = MinerTelemetry(
            miner_id=miner.id,
            hashrate=telemetry_data['hashrate'],
            power_consumption=telemetry_data['power'],
            temperature=telemetry_data['temperature_avg'],
            fan_speed=telemetry_data['fan_avg'],
            pool_url=telemetry_data['pool_url'],
            pool_worker=telemetry_data['pool_worker'],
            accepted_shares=telemetry_data['accepted_shares'],
            rejected_shares=telemetry_data['rejected_shares'],
            recorded_at=time_offset
        )
        db.session.add(telemetry)
        records_inserted += 1
    
    return records_inserted

def main():
    """主函数"""
    with app.app_context():
        print("=" * 80)
        print("HashPower MegaFarm 20MW - 模拟CGMiner Telemetry数据生成器")
        print("=" * 80)
        
        # 查询HashPower MegaFarm站点
        site_id = 5
        
        # 查询该站点的所有矿机
        miners = HostingMiner.query.filter_by(site_id=site_id).all()
        
        if not miners:
            print(f"❌ 未找到站点 {site_id} 的矿机")
            return
        
        print(f"\n✓ 找到 {len(miners)} 台矿机")
        print(f"  - Active: {sum(1 for m in miners if m.status == 'active')}")
        print(f"  - Offline: {sum(1 for m in miners if m.status == 'offline')}")
        print(f"  - Maintenance: {sum(1 for m in miners if m.status == 'maintenance')}")
        
        # 询问用户
        print("\n操作选项：")
        print("1. 更新实时CGMiner数据（HostingMiner表）")
        print("2. 更新实时数据 + 生成24小时历史记录（MinerTelemetry表）")
        
        choice = input("\n请选择 (1/2): ")
        
        if choice not in ['1', '2']:
            print("已取消")
            return
        
        include_history = (choice == '2')
        
        print("\n开始生成telemetry数据...")
        
        # 分批处理，避免内存溢出
        batch_size = 100
        total_updated = 0
        total_history_records = 0
        
        for i in range(0, len(miners), batch_size):
            batch_miners = miners[i:i + batch_size]
            
            for miner in batch_miners:
                # 更新实时数据
                telemetry_data = update_miner_telemetry(miner)
                total_updated += 1
                
                # 插入历史记录（可选）
                if include_history and telemetry_data:
                    records = insert_telemetry_history(miner, telemetry_data, hours=24)
                    total_history_records += records
            
            # 提交批次
            db.session.commit()
            print(f"  进度: {min(i + batch_size, len(miners))}/{len(miners)} 矿机处理完成")
        
        print(f"\n✓ 成功更新 {total_updated} 台矿机的实时CGMiner数据")
        
        if include_history:
            print(f"✓ 成功生成 {total_history_records} 条历史telemetry记录")
            print(f"  平均每台矿机: {total_history_records / sum(1 for m in miners if m.status == 'active'):.1f} 条记录")
        
        # 显示统计信息
        online_miners = HostingMiner.query.filter_by(
            site_id=site_id,
            cgminer_online=True
        ).count()
        
        print(f"\n数据库统计:")
        print(f"  在线矿机: {online_miners}/{len(miners)}")
        print(f"  最新更新时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        if include_history:
            total_telemetry = MinerTelemetry.query.filter(
                MinerTelemetry.miner_id.in_([m.id for m in miners])
            ).count()
            print(f"  MinerTelemetry历史记录总数: {total_telemetry}")
        
        print("\n" + "=" * 80)
        print("✓ 完成！现在可以在实时监控页面查看数据了")
        print("=" * 80)

if __name__ == '__main__':
    main()
