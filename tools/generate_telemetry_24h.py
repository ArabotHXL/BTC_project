#!/usr/bin/env python3
"""
Telemetry生成脚本 - 24小时历史数据
Generate 24 hours of telemetry data for HashPower MegaFarm (site_id=5)

根据Architect策略:
- 选择site_id=5的所有矿机（无状态过滤）
- 按状态生成不同指标:
  * Active: ±10% hashrate jitter, ±8% power jitter
  * Maintenance: 低指标, elevated temps
  * Offline: 零值
- 精确24条hourly记录（对齐到整点）
- 批量INSERT（≤10k行/批次）
- 事务执行，支持rollback
"""

import os
import sys
import random
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import HostingMiner, MinerTelemetry
from sqlalchemy import text


# Constants for NULL-safe fallbacks
DEFAULT_HASHRATE_TH = 110.0
DEFAULT_POWER_W = 3000.0
DEFAULT_TEMP_C = 70.0


def get_base_hashrate(miner):
    """Get base hashrate with layered fallbacks"""
    if miner.actual_hashrate:
        return miner.actual_hashrate
    if hasattr(miner, 'miner_model') and miner.miner_model:
        if hasattr(miner.miner_model, 'reference_hashrate'):
            return miner.miner_model.reference_hashrate
    return DEFAULT_HASHRATE_TH


def get_base_power(miner):
    """Get base power with layered fallbacks"""
    if miner.actual_power:
        return miner.actual_power
    if hasattr(miner, 'miner_model') and miner.miner_model:
        if hasattr(miner.miner_model, 'reference_power'):
            return miner.miner_model.reference_power
    return DEFAULT_POWER_W


def generate_telemetry_24h(site_id=5, batch_size=10000):
    """
    为指定站点生成24小时的遥测数据
    
    Args:
        site_id: 站点ID (默认5 = HashPower MegaFarm)
        batch_size: 批量插入大小 (默认10000行)
    
    Returns:
        dict: 执行统计信息
    """
    
    with app.app_context():
        print(f"\n{'='*70}")
        print(f"🚀 开始生成24小时遥测数据 - Site ID: {site_id}")
        print(f"{'='*70}\n")
        
        # ===================================================================
        # Step 1: 获取目标矿机（site_id=5的所有矿机，无状态过滤）
        # ===================================================================
        print(f"📊 Step 1: 查询Site {site_id}的所有矿机...")
        
        miners = HostingMiner.query.filter_by(site_id=site_id).all()
        
        if not miners:
            print(f"❌ 错误: Site {site_id} 没有找到任何矿机")
            return {
                'success': False,
                'error': f'No miners found for site_id={site_id}',
                'miners_count': 0,
                'records_generated': 0
            }
        
        print(f"✅ 找到 {len(miners)} 台矿机")
        
        # 统计各状态矿机数量
        status_counts = {}
        for miner in miners:
            status = miner.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n矿机状态分布:")
        for status, count in sorted(status_counts.items()):
            print(f"  - {status}: {count} 台")
        
        # ===================================================================
        # Step 2: 生成24小时时间戳（对齐到整点）
        # ===================================================================
        print(f"\n📅 Step 2: 生成24小时时间戳...")
        
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        timestamps = []
        
        for hour_offset in range(24):
            # 从24小时前到现在，每小时一个点
            timestamp = now - timedelta(hours=23 - hour_offset)
            timestamps.append(timestamp)
        
        print(f"✅ 生成 {len(timestamps)} 个时间点")
        print(f"   起始: {timestamps[0]}")
        print(f"   结束: {timestamps[-1]}")
        
        # ===================================================================
        # Step 3: 生成遥测记录
        # ===================================================================
        print(f"\n🔧 Step 3: 生成遥测记录...")
        
        telemetry_records = []
        total_records = len(miners) * len(timestamps)
        
        print(f"   预计生成: {total_records} 条记录 ({len(miners)} miners × {len(timestamps)} hours)")
        
        for miner in miners:
            for timestamp in timestamps:
                # 根据矿机状态生成不同的指标
                if miner.status == 'active':
                    # Active矿机: realistic jitter around actual values
                    base_hashrate = get_base_hashrate(miner)
                    base_power = get_base_power(miner)
                    hashrate = base_hashrate * (1 + random.uniform(-0.10, 0.10))
                    power = base_power * (1 + random.uniform(-0.08, 0.08))
                    temp = random.uniform(65, 85)
                    fan = random.randint(4000, 6000)
                    
                elif miner.status == 'maintenance':
                    # Maintenance矿机: 低/空闲指标, elevated temps
                    base_hashrate = get_base_hashrate(miner)
                    base_power = get_base_power(miner)
                    hashrate = base_hashrate * random.uniform(0.05, 0.20)
                    power = base_power * random.uniform(0.10, 0.30)
                    temp = random.uniform(70, 95)  # Elevated
                    fan = random.randint(3000, 7000)  # High variance
                    
                else:  # offline 或其他状态
                    # Offline矿机: 零值, NULL temps
                    hashrate = 0.0
                    power = 0.0
                    temp = None
                    fan = None
                
                # 创建遥测记录字典（用于批量INSERT）
                record = {
                    'miner_id': miner.id,
                    'hashrate': round(hashrate, 2),
                    'power_consumption': round(power, 2),
                    'temperature': round(temp, 2) if temp is not None else None,
                    'fan_speed': fan,
                    'recorded_at': timestamp,
                    'accepted_shares': 0,  # 可选，这里简化为0
                    'rejected_shares': 0   # 可选，这里简化为0
                }
                
                telemetry_records.append(record)
        
        print(f"✅ 生成 {len(telemetry_records)} 条记录")
        
        # ===================================================================
        # Step 4: 批量插入数据库（使用事务）
        # ===================================================================
        print(f"\n💾 Step 4: 批量插入数据库...")
        print(f"   批次大小: {batch_size} 行/批次")
        
        try:
            # 开始事务
            total_inserted = 0
            num_batches = (len(telemetry_records) + batch_size - 1) // batch_size
            
            print(f"   共分为 {num_batches} 个批次")
            
            for i in range(0, len(telemetry_records), batch_size):
                batch = telemetry_records[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                print(f"   批次 {batch_num}/{num_batches}: 插入 {len(batch)} 条记录...", end='', flush=True)
                
                # 使用SQLAlchemy Core批量插入
                db.session.execute(
                    MinerTelemetry.__table__.insert(),
                    batch
                )
                
                total_inserted += len(batch)
                print(f" ✅")
            
            # 提交事务
            db.session.commit()
            print(f"\n✅ 成功插入 {total_inserted} 条记录")
            
        except Exception as e:
            # 回滚事务
            db.session.rollback()
            print(f"\n❌ 插入失败，已回滚: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'miners_count': len(miners),
                'records_generated': len(telemetry_records),
                'records_inserted': 0
            }
        
        # ===================================================================
        # Step 5: 返回统计信息
        # ===================================================================
        stats = {
            'success': True,
            'site_id': site_id,
            'miners_count': len(miners),
            'status_distribution': status_counts,
            'hours_generated': len(timestamps),
            'records_generated': len(telemetry_records),
            'records_inserted': total_inserted,
            'time_range': {
                'start': timestamps[0].isoformat(),
                'end': timestamps[-1].isoformat()
            }
        }
        
        print(f"\n{'='*70}")
        print(f"📊 执行统计:")
        print(f"{'='*70}")
        print(f"✅ 矿机数量: {stats['miners_count']}")
        print(f"✅ 时间范围: {stats['hours_generated']} 小时")
        print(f"✅ 生成记录: {stats['records_generated']}")
        print(f"✅ 插入记录: {stats['records_inserted']}")
        print(f"✅ 起始时间: {stats['time_range']['start']}")
        print(f"✅ 结束时间: {stats['time_range']['end']}")
        print(f"{'='*70}\n")
        
        return stats


def validate_telemetry(site_id=5):
    """
    验证生成的遥测数据质量
    
    Args:
        site_id: 站点ID
    
    Returns:
        dict: 验证结果
    """
    
    with app.app_context():
        print(f"\n{'='*70}")
        print(f"🔍 开始验证遥测数据 - Site ID: {site_id}")
        print(f"{'='*70}\n")
        
        validation_results = {
            'check_record_count': None,
            'check_hourly_cadence': None,
            'check_status_metrics': None
        }
        
        # ===================================================================
        # 验证1: 每台矿机应该有24条记录
        # ===================================================================
        print("📋 验证1: 检查每台矿机的记录数量...")
        
        query1 = text("""
            SELECT miner_id, COUNT(*) as record_count
            FROM miner_telemetry
            WHERE miner_id IN (SELECT id FROM hosting_miners WHERE site_id = :site_id)
            GROUP BY miner_id
            HAVING COUNT(*) != 24
        """)
        
        result1 = db.session.execute(query1, {'site_id': site_id}).fetchall()
        
        if len(result1) == 0:
            print("✅ PASS: 所有矿机都有24条记录")
            validation_results['check_record_count'] = 'PASS'
        else:
            print(f"❌ FAIL: 发现 {len(result1)} 台矿机记录数量不是24:")
            for row in result1[:10]:  # 只显示前10条
                print(f"   - Miner ID {row[0]}: {row[1]} 条记录")
            validation_results['check_record_count'] = 'FAIL'
        
        # ===================================================================
        # 验证2: 验证hourly cadence（每小时一条）
        # ===================================================================
        print("\n⏰ 验证2: 检查时间间隔是否为1小时...")
        
        query2 = text("""
            WITH telemetry_with_lag AS (
                SELECT 
                    miner_id,
                    recorded_at,
                    LAG(recorded_at) OVER (PARTITION BY miner_id ORDER BY recorded_at) as prev_time,
                    EXTRACT(epoch FROM recorded_at - LAG(recorded_at) OVER (PARTITION BY miner_id ORDER BY recorded_at))/3600 as hours_gap
                FROM miner_telemetry
                WHERE miner_id IN (SELECT id FROM hosting_miners WHERE site_id = :site_id)
            )
            SELECT miner_id, recorded_at, prev_time, hours_gap
            FROM telemetry_with_lag
            WHERE hours_gap IS NOT NULL AND hours_gap != 1.0
            LIMIT 10
        """)
        
        result2 = db.session.execute(query2, {'site_id': site_id}).fetchall()
        
        if len(result2) == 0:
            print("✅ PASS: 所有记录的时间间隔都是1小时")
            validation_results['check_hourly_cadence'] = 'PASS'
        else:
            print(f"❌ FAIL: 发现时间间隔不是1小时的记录:")
            for row in result2:
                print(f"   - Miner ID {row[0]}: {row[1]} -> {row[2]} (间隔: {row[3]:.2f}h)")
            validation_results['check_hourly_cadence'] = 'FAIL'
        
        # ===================================================================
        # 验证3: 验证各状态矿机的指标范围
        # ===================================================================
        print("\n📊 验证3: 检查各状态矿机的指标范围...")
        
        query3 = text("""
            SELECT 
                hm.status,
                COUNT(*) as record_count,
                AVG(mt.hashrate) as avg_hashrate,
                AVG(mt.power_consumption) as avg_power,
                AVG(mt.temperature) as avg_temp,
                MIN(mt.hashrate) as min_hashrate,
                MAX(mt.hashrate) as max_hashrate
            FROM miner_telemetry mt
            JOIN hosting_miners hm ON mt.miner_id = hm.id
            WHERE hm.site_id = :site_id
            GROUP BY hm.status
            ORDER BY hm.status
        """)
        
        result3 = db.session.execute(query3, {'site_id': site_id}).fetchall()
        
        print("\n状态    | 记录数 | 平均算力 | 平均功耗 | 平均温度 | 算力范围")
        print("-" * 80)
        
        validation_passed = True
        for row in result3:
            status = row[0]
            count = row[1]
            avg_hashrate = row[2] or 0
            avg_power = row[3] or 0
            avg_temp = row[4] or 0
            min_hashrate = row[5] or 0
            max_hashrate = row[6] or 0
            
            print(f"{status:10} | {count:6} | {avg_hashrate:8.2f} | {avg_power:8.2f} | "
                  f"{avg_temp:8.2f} | {min_hashrate:.2f}-{max_hashrate:.2f}")
            
            # 简单验证逻辑
            if status == 'offline' and avg_hashrate > 0.01:
                validation_passed = False
                print(f"   ⚠️  WARNING: Offline矿机应该算力为0，但平均算力为 {avg_hashrate}")
            
            if status == 'active' and avg_hashrate < 1.0:
                validation_passed = False
                print(f"   ⚠️  WARNING: Active矿机算力过低: {avg_hashrate}")
        
        if validation_passed:
            print("\n✅ PASS: 各状态指标范围正常")
            validation_results['check_status_metrics'] = 'PASS'
        else:
            print("\n⚠️  WARNING: 部分状态指标异常")
            validation_results['check_status_metrics'] = 'WARNING'
        
        # ===================================================================
        # 总结验证结果
        # ===================================================================
        print(f"\n{'='*70}")
        print(f"📊 验证结果汇总:")
        print(f"{'='*70}")
        
        all_passed = all(
            result in ['PASS', 'WARNING'] 
            for result in validation_results.values()
        )
        
        for check, result in validation_results.items():
            icon = "✅" if result == 'PASS' else "⚠️" if result == 'WARNING' else "❌"
            print(f"{icon} {check}: {result}")
        
        if all_passed:
            print(f"\n🎉 整体验证: PASS")
        else:
            print(f"\n❌ 整体验证: FAIL")
        
        print(f"{'='*70}\n")
        
        return validation_results


if __name__ == '__main__':
    # 执行生成
    stats = generate_telemetry_24h(site_id=5, batch_size=10000)
    
    if stats['success']:
        # 执行验证
        validation = validate_telemetry(site_id=5)
        
        print("\n🏁 脚本执行完成！")
    else:
        print("\n❌ 脚本执行失败！")
        sys.exit(1)
