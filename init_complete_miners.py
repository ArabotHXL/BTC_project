#!/usr/bin/env python3
"""
完整的矿机数据库初始化脚本 - 包含42+个主流ASIC矿机型号
基于2024-2025年市场主流型号
"""

import logging
from datetime import date
from app import app, db
from models import MinerModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 完整的矿机数据（42+个型号）
COMPLETE_MINER_DATA = [
    # ===== BITMAIN ANTMINER S21 系列 (2024-2025最新) =====
    {
        "model_name": "Antminer S21e XP Hyd 3U",
        "manufacturer": "Bitmain",
        "reference_hashrate": 860.0,
        "reference_power": 11180,
        "chip_type": "BM1370",
        "is_liquid_cooled": True,
        "release_date": date(2025, 1, 1),
        "reference_price": 17000,
        "fan_count": 0,
        "noise_level": 40
    },
    {
        "model_name": "Antminer S21 XP+ Hyd",
        "manufacturer": "Bitmain",
        "reference_hashrate": 500.0,
        "reference_power": 5500,
        "chip_type": "BM1370",
        "is_liquid_cooled": True,
        "release_date": date(2025, 7, 1),
        "reference_price": 12700,
        "fan_count": 0,
        "noise_level": 40
    },
    {
        "model_name": "Antminer S21 XP",
        "manufacturer": "Bitmain",
        "reference_hashrate": 270.0,
        "reference_power": 3645,
        "chip_type": "BM1366AE",
        "release_date": date(2024, 6, 1),
        "reference_price": 4000,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "Antminer S21 Pro",
        "manufacturer": "Bitmain",
        "reference_hashrate": 234.0,
        "reference_power": 3531,
        "chip_type": "BM1366AE",
        "release_date": date(2024, 3, 1),
        "reference_price": 5000,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "Antminer S21+",
        "manufacturer": "Bitmain",
        "reference_hashrate": 216.0,
        "reference_power": 3800,
        "chip_type": "BM1366AE",
        "release_date": date(2024, 8, 1),
        "reference_price": 4500,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "Antminer S21",
        "manufacturer": "Bitmain",
        "reference_hashrate": 200.0,
        "reference_power": 3550,
        "chip_type": "BM1366AE",
        "release_date": date(2023, 9, 1),
        "reference_price": 4000,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "Antminer S21 Hyd",
        "manufacturer": "Bitmain",
        "reference_hashrate": 335.0,
        "reference_power": 5360,
        "chip_type": "BM1366AE",
        "is_liquid_cooled": True,
        "release_date": date(2024, 6, 1),
        "reference_price": 15000,
        "fan_count": 0,
        "noise_level": 50
    },
    {
        "model_name": "Antminer S21 Pro Hyd",
        "manufacturer": "Bitmain",
        "reference_hashrate": 319.0,
        "reference_power": 5445,
        "chip_type": "BM1366AE",
        "is_liquid_cooled": True,
        "release_date": date(2024, 9, 1),
        "reference_price": 18000,
        "fan_count": 0,
        "noise_level": 50
    },
    {
        "model_name": "Antminer S21 XP Hyd",
        "manufacturer": "Bitmain",
        "reference_hashrate": 473.0,
        "reference_power": 5676,
        "chip_type": "BM1366AE",
        "is_liquid_cooled": True,
        "release_date": date(2024, 12, 1),
        "reference_price": 25000,
        "fan_count": 0,
        "noise_level": 50
    },
    
    # ===== BITMAIN ANTMINER S19 系列 (2020-2023) =====
    {
        "model_name": "Antminer S19 XP Hyd",
        "manufacturer": "Bitmain",
        "reference_hashrate": 255.0,
        "reference_power": 5304,
        "chip_type": "BM1366",
        "is_liquid_cooled": True,
        "release_date": date(2022, 10, 1),
        "reference_price": 8000,
        "fan_count": 0,
        "noise_level": 50
    },
    {
        "model_name": "Antminer S19 XP",
        "manufacturer": "Bitmain",
        "reference_hashrate": 140.0,
        "reference_power": 3010,
        "chip_type": "BM1366",
        "release_date": date(2022, 1, 1),
        "reference_price": 4500,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "Antminer S19j Pro",
        "manufacturer": "Bitmain",
        "reference_hashrate": 100.0,
        "reference_power": 3068,
        "chip_type": "BM1366",
        "release_date": date(2021, 8, 1),
        "reference_price": 2800,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "Antminer S19j Pro+",
        "manufacturer": "Bitmain",
        "reference_hashrate": 120.0,
        "reference_power": 3000,
        "chip_type": "BM1366",
        "release_date": date(2021, 12, 1),
        "reference_price": 3200,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "Antminer S19k Pro",
        "manufacturer": "Bitmain",
        "reference_hashrate": 120.0,
        "reference_power": 2760,
        "chip_type": "BM1366",
        "release_date": date(2023, 9, 1),
        "reference_price": 3500,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "Antminer S19 Pro",
        "manufacturer": "Bitmain",
        "reference_hashrate": 110.0,
        "reference_power": 3250,
        "chip_type": "BM1366",
        "release_date": date(2020, 5, 1),
        "reference_price": 3200,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "Antminer S19",
        "manufacturer": "Bitmain",
        "reference_hashrate": 95.0,
        "reference_power": 3250,
        "chip_type": "BM1366",
        "release_date": date(2020, 5, 1),
        "reference_price": 2500,
        "fan_count": 4,
        "noise_level": 75
    },
    
    # ===== BITMAIN ANTMINER T 系列 =====
    {
        "model_name": "Antminer T21",
        "manufacturer": "Bitmain",
        "reference_hashrate": 190.0,
        "reference_power": 3610,
        "chip_type": "BM1366AE",
        "release_date": date(2024, 3, 1),
        "reference_price": 3800,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "Antminer T19",
        "manufacturer": "Bitmain",
        "reference_hashrate": 84.0,
        "reference_power": 3150,
        "chip_type": "BM1366",
        "release_date": date(2020, 11, 1),
        "reference_price": 2000,
        "fan_count": 4,
        "noise_level": 75
    },
    
    # ===== MICROBT WHATSMINER M60 系列 (2024-2025最新) =====
    {
        "model_name": "WhatsMiner M60S+",
        "manufacturer": "MicroBT",
        "reference_hashrate": 212.0,
        "reference_power": 3600,
        "chip_type": "WM2124",
        "release_date": date(2024, 6, 1),
        "reference_price": 4500,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "WhatsMiner M60S",
        "manufacturer": "MicroBT",
        "reference_hashrate": 186.0,
        "reference_power": 3441,
        "chip_type": "WM2124",
        "release_date": date(2024, 3, 1),
        "reference_price": 4200,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "WhatsMiner M60",
        "manufacturer": "MicroBT",
        "reference_hashrate": 170.0,
        "reference_power": 3400,
        "chip_type": "WM2124",
        "release_date": date(2024, 1, 1),
        "reference_price": 4000,
        "fan_count": 4,
        "noise_level": 75
    },
    
    # ===== MICROBT WHATSMINER M66 系列 (水冷/浸没式) =====
    {
        "model_name": "WhatsMiner M66S++",
        "manufacturer": "MicroBT",
        "reference_hashrate": 356.0,
        "reference_power": 5518,
        "chip_type": "WM2174",
        "is_liquid_cooled": True,
        "release_date": date(2024, 12, 1),
        "reference_price": 8660,
        "fan_count": 0,
        "noise_level": 45
    },
    {
        "model_name": "WhatsMiner M66S+",
        "manufacturer": "MicroBT",
        "reference_hashrate": 356.0,
        "reference_power": 5500,
        "chip_type": "WM2174",
        "is_liquid_cooled": True,
        "release_date": date(2024, 9, 1),
        "reference_price": 8200,
        "fan_count": 0,
        "noise_level": 45
    },
    {
        "model_name": "WhatsMiner M66S",
        "manufacturer": "MicroBT",
        "reference_hashrate": 350.0,
        "reference_power": 5500,
        "chip_type": "WM2174",
        "is_liquid_cooled": True,
        "release_date": date(2024, 6, 1),
        "reference_price": 7800,
        "fan_count": 0,
        "noise_level": 45
    },
    
    # ===== MICROBT WHATSMINER M63 系列 (水冷) =====
    {
        "model_name": "WhatsMiner M63S+",
        "manufacturer": "MicroBT",
        "reference_hashrate": 412.0,
        "reference_power": 7004,
        "chip_type": "WM2174",
        "is_liquid_cooled": True,
        "release_date": date(2024, 3, 1),
        "reference_price": 9500,
        "fan_count": 0,
        "noise_level": 45
    },
    {
        "model_name": "WhatsMiner M63S",
        "manufacturer": "MicroBT",
        "reference_hashrate": 390.0,
        "reference_power": 7215,
        "chip_type": "WM2174",
        "is_liquid_cooled": True,
        "release_date": date(2023, 10, 1),
        "reference_price": 9000,
        "fan_count": 0,
        "noise_level": 45
    },
    
    # ===== MICROBT WHATSMINER M56/M53 系列 =====
    {
        "model_name": "WhatsMiner M56S",
        "manufacturer": "MicroBT",
        "reference_hashrate": 238.0,
        "reference_power": 5550,
        "chip_type": "WM2174",
        "release_date": date(2024, 4, 1),
        "reference_price": 10000,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "WhatsMiner M56",
        "manufacturer": "MicroBT",
        "reference_hashrate": 230.0,
        "reference_power": 5550,
        "chip_type": "WM2174",
        "release_date": date(2024, 1, 1),
        "reference_price": 9000,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "WhatsMiner M53S",
        "manufacturer": "MicroBT",
        "reference_hashrate": 230.0,
        "reference_power": 6174,
        "chip_type": "WM2124",
        "release_date": date(2023, 8, 1),
        "reference_price": 8500,
        "fan_count": 4,
        "noise_level": 78
    },
    {
        "model_name": "WhatsMiner M53",
        "manufacturer": "MicroBT",
        "reference_hashrate": 226.0,
        "reference_power": 6174,
        "chip_type": "WM2124",
        "release_date": date(2023, 5, 1),
        "reference_price": 8000,
        "fan_count": 4,
        "noise_level": 78
    },
    
    # ===== MICROBT WHATSMINER M50/M30 系列 =====
    {
        "model_name": "WhatsMiner M50S+",
        "manufacturer": "MicroBT",
        "reference_hashrate": 136.0,
        "reference_power": 3264,
        "chip_type": "WM1832",
        "release_date": date(2022, 6, 1),
        "reference_price": 3600,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "WhatsMiner M50S",
        "manufacturer": "MicroBT",
        "reference_hashrate": 126.0,
        "reference_power": 3276,
        "chip_type": "WM1832",
        "release_date": date(2022, 2, 1),
        "reference_price": 3500,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "WhatsMiner M50",
        "manufacturer": "MicroBT",
        "reference_hashrate": 114.0,
        "reference_power": 3306,
        "chip_type": "WM1832",
        "release_date": date(2021, 6, 1),
        "reference_price": 3000,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "WhatsMiner M30S++",
        "manufacturer": "MicroBT",
        "reference_hashrate": 112.0,
        "reference_power": 3472,
        "chip_type": "WM1832",
        "release_date": date(2021, 3, 1),
        "reference_price": 2800,
        "fan_count": 4,
        "noise_level": 75
    },
    {
        "model_name": "WhatsMiner M30S+",
        "manufacturer": "MicroBT",
        "reference_hashrate": 100.0,
        "reference_power": 3400,
        "chip_type": "WM1832",
        "release_date": date(2020, 10, 1),
        "reference_price": 2600,
        "fan_count": 4,
        "noise_level": 75
    },
    
    # ===== CANAAN AVALON 系列 =====
    {
        "model_name": "Avalon A1566",
        "manufacturer": "Canaan",
        "reference_hashrate": 185.0,
        "reference_power": 3420,
        "chip_type": "4nm ASIC",
        "release_date": date(2025, 1, 1),
        "reference_price": 3800,
        "fan_count": 4,
        "noise_level": 65
    },
    {
        "model_name": "Avalon Q",
        "manufacturer": "Canaan",
        "reference_hashrate": 90.0,
        "reference_power": 1674,
        "chip_type": "4nm ASIC",
        "release_date": date(2025, 1, 1),
        "reference_price": 1599,
        "fan_count": 2,
        "noise_level": 55
    },
    {
        "model_name": "AvalonMiner 1466",
        "manufacturer": "Canaan",
        "reference_hashrate": 150.0,
        "reference_power": 3420,
        "chip_type": "7nm ASIC",
        "release_date": date(2023, 6, 1),
        "reference_price": 3000,
        "fan_count": 4,
        "noise_level": 70
    },
    {
        "model_name": "AvalonMiner 1366",
        "manufacturer": "Canaan",
        "reference_hashrate": 100.0,
        "reference_power": 3420,
        "chip_type": "7nm ASIC",
        "release_date": date(2022, 8, 1),
        "reference_price": 2400,
        "fan_count": 4,
        "noise_level": 70
    },
    {
        "model_name": "Avalon Mini 3",
        "manufacturer": "Canaan",
        "reference_hashrate": 37.5,
        "reference_power": 800,
        "chip_type": "4nm ASIC",
        "release_date": date(2024, 10, 1),
        "reference_price": 1500,
        "fan_count": 2,
        "noise_level": 45
    },
    
    # ===== 其他制造商 =====
    {
        "model_name": "Bitdeer SEALMINER A2 Pro Hyd",
        "manufacturer": "Bitdeer",
        "reference_hashrate": 500.0,
        "reference_power": 7450,
        "chip_type": "Custom",
        "is_liquid_cooled": True,
        "release_date": date(2025, 6, 1),
        "reference_price": 3958,
        "fan_count": 0,
        "noise_level": 40
    },
    {
        "model_name": "Auradine Teraflux AH3880",
        "manufacturer": "Auradine",
        "reference_hashrate": 600.0,
        "reference_power": 8700,
        "chip_type": "Custom",
        "is_liquid_cooled": True,
        "release_date": date(2025, 3, 1),
        "reference_price": 7800,
        "fan_count": 0,
        "noise_level": 40
    }
]

def init_complete_miners():
    """初始化完整的矿机数据库（42+个型号）"""
    logger.info("=" * 70)
    logger.info("🚀 开始导入完整矿机数据库（42+个型号）...")
    logger.info("=" * 70)
    
    with app.app_context():
        try:
            # 创建数据库表
            db.create_all()
            logger.info("✅ 数据库表创建完成")
            
            # 检查现有数据
            existing_count = MinerModel.query.count()
            logger.info(f"📊 当前数据库中有 {existing_count} 条矿机数据")
            
            # 导入新矿机数据
            imported_count = 0
            skipped_count = 0
            
            for miner_data in COMPLETE_MINER_DATA:
                model_name = miner_data['model_name']
                
                # 检查是否已存在
                existing_miner = MinerModel.query.filter_by(model_name=model_name).first()
                if existing_miner:
                    logger.info(f"⏩ 矿机已存在，跳过: {model_name}")
                    skipped_count += 1
                    continue
                
                # 创建矿机记录
                miner = MinerModel(**miner_data)
                db.session.add(miner)
                imported_count += 1
                
                efficiency = round(miner_data['reference_power'] / miner_data['reference_hashrate'], 2)
                logger.info(f"✅ 已添加: {model_name} - {miner_data['reference_hashrate']}TH/s, {miner_data['reference_power']}W, {efficiency}W/TH")
            
            # 提交数据
            db.session.commit()
            
            # 统计结果
            final_count = MinerModel.query.count()
            logger.info("=" * 70)
            logger.info(f"🎉 矿机数据导入完成!")
            logger.info(f"📊 统计结果:")
            logger.info(f"   - 新增: {imported_count} 条")
            logger.info(f"   - 跳过: {skipped_count} 条")
            logger.info(f"   - 总计: {final_count} 条矿机记录")
            logger.info("=" * 70)
            
            # 按制造商统计
            manufacturers = db.session.query(
                MinerModel.manufacturer,
                db.func.count(MinerModel.id)
            ).group_by(MinerModel.manufacturer).all()
            
            logger.info("📈 按制造商统计:")
            for mfg, count in manufacturers:
                logger.info(f"   - {mfg}: {count} 个型号")
            
        except Exception as e:
            logger.error(f"❌ 导入矿机数据失败: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    init_complete_miners()
    logger.info("✨ 完成！")
