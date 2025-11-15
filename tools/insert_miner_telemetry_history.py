#!/usr/bin/env python3
"""
MinerTelemetry历史数据生成脚本
Generate 24 hours of historical telemetry data for active miners

为6000台active矿机生成24小时的历史遥测记录（每小时一条）
总共约144,000条记录，使用批量插入提高性能
"""

import sys
import os
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, HostingMiner, MinerTelemetry


def generate_telemetry_history(batch_size=100, max_miners=6000, hours=24):
    """
    为active矿机生成历史遥测数据
    
    参数:
        batch_size: 每批处理的矿机数量（默认100台）
        max_miners: 最大处理的矿机数量（默认6000台）
        hours: 生成的历史小时数（默认24小时）
    """
    with app.app_context():
        print(f"🚀 开始生成MinerTelemetry历史数据...")
        print(f"📊 配置: batch_size={batch_size}, max_miners={max_miners}, hours={hours}")
        
        # 查询active矿机
        active_miners = HostingMiner.query.filter_by(status='active').limit(max_miners).all()
        total_miners = len(active_miners)
        
        if total_miners == 0:
            print("❌ 未找到active状态的矿机")
            return
        
        print(f"✅ 找到 {total_miners} 台active矿机")
        
        # 统计信息
        total_records = 0
        batch_count = 0
        miners_processed = 0
        
        # 当前时间
        now = datetime.utcnow()
        
        # 分批处理矿机
        for i in range(0, total_miners, batch_size):
            batch_miners = active_miners[i:i + batch_size]
            batch_records = []
            
            for miner in batch_miners:
                # 获取矿机基准数据
                base_hashrate = miner.actual_hashrate or 100.0
                base_power = miner.actual_power or 3000.0
                base_temp = miner.temperature_max or 65.0
                base_fan_speed = miner.fan_avg or 5000
                
                # 为该矿机生成24小时的历史记录（每小时一条）
                for hour_offset in range(hours):
                    # 计算记录时间（从24小时前到现在）
                    recorded_time = now - timedelta(hours=(hours - hour_offset - 1))
                    
                    # 添加随机波动（±10%）
                    hashrate_variation = random.uniform(-0.10, 0.10)
                    power_variation = random.uniform(-0.08, 0.08)
                    temp_variation = random.uniform(-0.15, 0.15)
                    fan_variation = random.uniform(-0.12, 0.12)
                    
                    hashrate = max(0, base_hashrate * (1 + hashrate_variation))
                    power_consumption = max(0, base_power * (1 + power_variation))
                    temperature = max(30, min(95, base_temp * (1 + temp_variation)))
                    fan_speed = max(2000, min(8000, int(base_fan_speed * (1 + fan_variation))))
                    
                    # 生成shares数据（随机增长）
                    accepted_shares = random.randint(1000, 5000)
                    rejected_shares = random.randint(0, 50)
                    
                    # 矿池信息（使用矿机的当前矿池或默认值）
                    pool_url = miner.pool_url or "stratum+tcp://pool.example.com:3333"
                    pool_worker = miner.pool_worker or f"worker_{miner.id}"
                    
                    # 创建遥测记录
                    telemetry = MinerTelemetry(
                        miner_id=miner.id,
                        hashrate=round(hashrate, 2),
                        power_consumption=round(power_consumption, 2),
                        temperature=round(temperature, 2),
                        fan_speed=fan_speed,
                        pool_url=pool_url,
                        pool_worker=pool_worker,
                        accepted_shares=accepted_shares,
                        rejected_shares=rejected_shares,
                        recorded_at=recorded_time
                    )
                    
                    batch_records.append(telemetry)
            
            # 批量插入
            try:
                db.session.bulk_save_objects(batch_records)
                db.session.commit()
                
                miners_processed += len(batch_miners)
                total_records += len(batch_records)
                batch_count += 1
                
                print(f"✅ 批次 {batch_count}: 处理 {len(batch_miners)} 台矿机, "
                      f"插入 {len(batch_records)} 条记录 "
                      f"(总计: {miners_processed}/{total_miners} 矿机, {total_records} 条记录)")
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ 批次 {batch_count} 插入失败: {e}")
                continue
        
        print(f"\n🎉 完成！")
        print(f"📊 统计:")
        print(f"   - 处理矿机数: {miners_processed}")
        print(f"   - 插入记录数: {total_records}")
        print(f"   - 处理批次数: {batch_count}")
        print(f"   - 时间范围: {hours} 小时")
        print(f"   - 平均每台矿机: {total_records/miners_processed:.1f} 条记录")


def check_existing_data():
    """检查现有的遥测数据"""
    with app.app_context():
        total_telemetry = MinerTelemetry.query.count()
        active_miners = HostingMiner.query.filter_by(status='active').count()
        
        print(f"📊 当前数据统计:")
        print(f"   - Active矿机数: {active_miners}")
        print(f"   - 现有遥测记录: {total_telemetry}")
        
        if total_telemetry > 0:
            oldest = MinerTelemetry.query.order_by(MinerTelemetry.recorded_at.asc()).first()
            newest = MinerTelemetry.query.order_by(MinerTelemetry.recorded_at.desc()).first()
            if oldest and newest:
                print(f"   - 最早记录: {oldest.recorded_at}")
                print(f"   - 最新记录: {newest.recorded_at}")


if __name__ == '__main__':
    print("=" * 60)
    print("MinerTelemetry历史数据生成工具")
    print("=" * 60)
    
    # 检查现有数据
    check_existing_data()
    
    print("\n是否继续生成历史数据？")
    print("⚠️  这将为最多6000台active矿机生成约144,000条历史记录")
    
    response = input("输入 'yes' 继续: ").strip().lower()
    
    if response == 'yes':
        print("\n开始生成...")
        generate_telemetry_history(
            batch_size=100,  # 每100台矿机提交一次
            max_miners=6000,  # 最多处理6000台矿机
            hours=24  # 生成24小时历史
        )
    else:
        print("❌ 已取消")
