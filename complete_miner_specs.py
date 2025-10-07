#!/usr/bin/env python3
"""
补充矿机技术规格数据
"""

import logging
from app import app, db
from models import MinerModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 补充的技术规格数据
MINER_SPECS = {
    # Bitmain S21 系列
    "Antminer S21e XP Hyd 3U": {
        "operating_temp_min": 5, "operating_temp_max": 35,
        "length_mm": 650, "width_mm": 310, "height_mm": 430,
        "weight_kg": 25.0
    },
    "Antminer S21 XP+ Hyd": {
        "operating_temp_min": 5, "operating_temp_max": 35,
        "length_mm": 430, "width_mm": 195.5, "height_mm": 290,
        "weight_kg": 18.5
    },
    "Antminer S21+": {
        "operating_temp_min": 0, "operating_temp_max": 45,
        "length_mm": 430, "width_mm": 195.5, "height_mm": 290,
        "weight_kg": 14.8
    },
    "Antminer S19 XP Hyd": {
        "operating_temp_min": 5, "operating_temp_max": 35,
        "length_mm": 410, "width_mm": 196, "height_mm": 301,
        "weight_kg": 17.0
    },
    "Antminer S19j Pro+": {
        "operating_temp_min": 5, "operating_temp_max": 45,
        "length_mm": 370, "width_mm": 195.5, "height_mm": 290,
        "weight_kg": 13.2
    },
    "Antminer S19k Pro": {
        "operating_temp_min": 5, "operating_temp_max": 45,
        "length_mm": 370, "width_mm": 195.5, "height_mm": 290,
        "weight_kg": 13.5
    },
    "Antminer T21": {
        "operating_temp_min": 0, "operating_temp_max": 45,
        "length_mm": 430, "width_mm": 195.5, "height_mm": 290,
        "weight_kg": 14.2
    },
    
    # MicroBT M60 系列
    "WhatsMiner M60S+": {
        "operating_temp_min": 0, "operating_temp_max": 40,
        "length_mm": 490, "width_mm": 265, "height_mm": 400,
        "weight_kg": 19.5
    },
    "WhatsMiner M60S": {
        "operating_temp_min": 0, "operating_temp_max": 40,
        "length_mm": 490, "width_mm": 265, "height_mm": 400,
        "weight_kg": 19.0
    },
    "WhatsMiner M60": {
        "operating_temp_min": 0, "operating_temp_max": 40,
        "length_mm": 490, "width_mm": 265, "height_mm": 400,
        "weight_kg": 18.5
    },
    
    # MicroBT M66 系列（浸没式）
    "WhatsMiner M66S++": {
        "operating_temp_min": 5, "operating_temp_max": 35,
        "length_mm": 570, "width_mm": 316, "height_mm": 430,
        "weight_kg": 35.0
    },
    "WhatsMiner M66S+": {
        "operating_temp_min": 5, "operating_temp_max": 35,
        "length_mm": 570, "width_mm": 316, "height_mm": 430,
        "weight_kg": 34.5
    },
    "WhatsMiner M66S": {
        "operating_temp_min": 5, "operating_temp_max": 35,
        "length_mm": 570, "width_mm": 316, "height_mm": 430,
        "weight_kg": 34.0
    },
    
    # MicroBT M63 系列（水冷）
    "WhatsMiner M63S+": {
        "operating_temp_min": 5, "operating_temp_max": 35,
        "length_mm": 570, "width_mm": 316, "height_mm": 430,
        "weight_kg": 36.0
    },
    "WhatsMiner M63S": {
        "operating_temp_min": 5, "operating_temp_max": 35,
        "length_mm": 570, "width_mm": 316, "height_mm": 430,
        "weight_kg": 35.5
    },
    
    # MicroBT 其他系列
    "WhatsMiner M50S+": {
        "operating_temp_min": 0, "operating_temp_max": 40,
        "length_mm": 390, "width_mm": 155, "height_mm": 208,
        "weight_kg": 11.0
    },
    "WhatsMiner M30S++": {
        "operating_temp_min": 0, "operating_temp_max": 40,
        "length_mm": 390, "width_mm": 155, "height_mm": 208,
        "weight_kg": 10.8
    },
    "WhatsMiner M30S+": {
        "operating_temp_min": 0, "operating_temp_max": 40,
        "length_mm": 390, "width_mm": 155, "height_mm": 208,
        "weight_kg": 10.5
    },
    
    # Canaan Avalon 系列
    "Avalon A1566": {
        "operating_temp_min": -5, "operating_temp_max": 35,
        "length_mm": 455, "width_mm": 130, "height_mm": 440,
        "weight_kg": 12.0
    },
    "AvalonMiner 1466": {
        "operating_temp_min": -5, "operating_temp_max": 35,
        "length_mm": 331, "width_mm": 195, "height_mm": 292,
        "weight_kg": 11.5
    },
    "AvalonMiner 1366": {
        "operating_temp_min": -5, "operating_temp_max": 35,
        "length_mm": 331, "width_mm": 195, "height_mm": 292,
        "weight_kg": 11.0
    },
    
    # 其他制造商
    "Bitdeer SEALMINER A2 Pro Hyd": {
        "operating_temp_min": 5, "operating_temp_max": 35,
        "length_mm": 520, "width_mm": 280, "height_mm": 420,
        "weight_kg": 32.0
    },
    "Auradine Teraflux AH3880": {
        "operating_temp_min": 5, "operating_temp_max": 35,
        "length_mm": 600, "width_mm": 300, "height_mm": 450,
        "weight_kg": 40.0
    }
}

def complete_miner_specs():
    """补充矿机技术规格"""
    logger.info("=" * 70)
    logger.info("🔧 开始补充矿机技术规格数据...")
    logger.info("=" * 70)
    
    with app.app_context():
        try:
            updated_count = 0
            not_found_count = 0
            
            for model_name, specs in MINER_SPECS.items():
                miner = MinerModel.query.filter_by(model_name=model_name).first()
                
                if not miner:
                    logger.warning(f"⚠️ 未找到矿机: {model_name}")
                    not_found_count += 1
                    continue
                
                # 更新技术规格
                for key, value in specs.items():
                    setattr(miner, key, value)
                
                updated_count += 1
                logger.info(f"✅ 已更新: {model_name}")
            
            # 提交更改
            db.session.commit()
            
            logger.info("=" * 70)
            logger.info(f"🎉 技术规格补充完成!")
            logger.info(f"📊 统计:")
            logger.info(f"   - 已更新: {updated_count} 个矿机")
            logger.info(f"   - 未找到: {not_found_count} 个")
            logger.info("=" * 70)
            
            # 验证结果
            total = MinerModel.query.count()
            complete = MinerModel.query.filter(
                MinerModel.operating_temp_min.isnot(None),
                MinerModel.length_mm.isnot(None),
                MinerModel.weight_kg.isnot(None)
            ).count()
            
            logger.info(f"📈 数据完整性:")
            logger.info(f"   - 总矿机数: {total}")
            logger.info(f"   - 完整数据: {complete} ({complete*100//total}%)")
            
        except Exception as e:
            logger.error(f"❌ 更新失败: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    complete_miner_specs()
    logger.info("✨ 完成！")
