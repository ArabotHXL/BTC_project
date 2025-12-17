#!/usr/bin/env python3
"""
初始化矿机数据库脚本
将现有的矿机数据导入到数据库中，方便以后动态管理
"""

import logging
from datetime import datetime, date
from app import app, db
from models import MinerModel

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 从mining_calculator.py中获取现有的矿机数据
EXISTING_MINER_DATA = {
    "Antminer S19": {"hashrate": 95, "power_watt": 3250},
    "Antminer S19 Pro": {"hashrate": 110, "power_watt": 3250},
    "Antminer S19j Pro": {"hashrate": 100, "power_watt": 3068},
    "Antminer S19 XP": {"hashrate": 140, "power_watt": 3010},
    "Antminer S21": {"hashrate": 200, "power_watt": 3550},
    "Antminer S21 Pro": {"hashrate": 234, "power_watt": 3531},
    "Antminer S21 XP": {"hashrate": 270, "power_watt": 3645},
    "Antminer S21 Hyd": {"hashrate": 335, "power_watt": 5360},
    "Antminer S21 Pro Hyd": {"hashrate": 319, "power_watt": 5445},
    "Antminer S21 XP Hyd": {"hashrate": 473, "power_watt": 5676},
    "Antminer T19": {"hashrate": 84, "power_watt": 3150},
    "WhatsMiner M50": {"hashrate": 114, "power_watt": 3306},
    "WhatsMiner M50S": {"hashrate": 126, "power_watt": 3276},
    "WhatsMiner M53": {"hashrate": 226, "power_watt": 6174},
    "WhatsMiner M53S": {"hashrate": 230, "power_watt": 6174},
    "WhatsMiner M56": {"hashrate": 230, "power_watt": 5550},
    "WhatsMiner M56S": {"hashrate": 238, "power_watt": 5550},
    "Avalon Q": {"hashrate": 90, "power_watt": 1674},
    "Avalon Mini 3": {"hashrate": 37.5, "power_watt": 800}
}

# 补充详细的矿机信息
DETAILED_MINER_INFO = {
    "Antminer S19": {
        "chip_type": "BM1366",
        "fan_count": 4,
        "operating_temp_min": 5,
        "operating_temp_max": 45,
        "noise_level": 75,
        "length_mm": 370,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 13.2,
        "release_date": date(2020, 5, 1),
        "price_usd": 2500
    },
    "Antminer S19 Pro": {
        "chip_type": "BM1366",
        "fan_count": 4,
        "operating_temp_min": 5,
        "operating_temp_max": 45,
        "noise_level": 75,
        "length_mm": 370,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 13.2,
        "release_date": date(2020, 5, 1),
        "price_usd": 3200
    },
    "Antminer S19j Pro": {
        "chip_type": "BM1366",
        "fan_count": 4,
        "operating_temp_min": 5,
        "operating_temp_max": 45,
        "noise_level": 75,
        "length_mm": 370,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 13.2,
        "release_date": date(2021, 8, 1),
        "price_usd": 2800
    },
    "Antminer S19 XP": {
        "chip_type": "BM1366",
        "fan_count": 4,
        "operating_temp_min": 5,
        "operating_temp_max": 45,
        "noise_level": 75,
        "length_mm": 370,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 13.2,
        "release_date": date(2022, 1, 1),
        "price_usd": 4500
    },
    "Antminer S21": {
        "chip_type": "BM1366AE",
        "fan_count": 4,
        "operating_temp_min": 0,
        "operating_temp_max": 45,
        "noise_level": 75,
        "length_mm": 430,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 14.5,
        "release_date": date(2023, 9, 1),
        "price_usd": 6500
    },
    "Antminer S21 Pro": {
        "chip_type": "BM1366AE",
        "fan_count": 4,
        "operating_temp_min": 0,
        "operating_temp_max": 45,
        "noise_level": 75,
        "length_mm": 430,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 14.8,
        "release_date": date(2024, 3, 1),
        "price_usd": 8500
    },
    "Antminer S21 XP": {
        "chip_type": "BM1366AE",
        "fan_count": 4,
        "operating_temp_min": 0,
        "operating_temp_max": 45,
        "noise_level": 75,
        "length_mm": 430,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 15.2,
        "release_date": date(2024, 8, 1),
        "price_usd": 12000
    },
    "Antminer S21 Hyd": {
        "chip_type": "BM1366AE",
        "fan_count": 0,  # 水冷无风扇
        "operating_temp_min": 5,
        "operating_temp_max": 35,
        "noise_level": 50,
        "length_mm": 430,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 17.5,
        "release_date": date(2024, 6, 1),
        "price_usd": 15000,
        "is_liquid_cooled": True
    },
    "Antminer S21 Pro Hyd": {
        "chip_type": "BM1366AE",
        "fan_count": 0,  # 水冷无风扇
        "operating_temp_min": 5,
        "operating_temp_max": 35,
        "noise_level": 50,
        "length_mm": 430,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 17.8,
        "release_date": date(2024, 9, 1),
        "price_usd": 18000,
        "is_liquid_cooled": True
    },
    "Antminer S21 XP Hyd": {
        "chip_type": "BM1366AE",
        "fan_count": 0,  # 水冷无风扇
        "operating_temp_min": 5,
        "operating_temp_max": 35,
        "noise_level": 50,
        "length_mm": 430,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 18.5,
        "release_date": date(2024, 12, 1),
        "price_usd": 25000,
        "is_liquid_cooled": True
    },
    "Antminer T19": {
        "chip_type": "BM1366",
        "fan_count": 4,
        "operating_temp_min": 5,
        "operating_temp_max": 45,
        "noise_level": 75,
        "length_mm": 370,
        "width_mm": 195.5,
        "height_mm": 290,
        "weight_kg": 13.0,
        "release_date": date(2020, 11, 1),
        "price_usd": 2000
    },
    # WhatsMiner 系列
    "WhatsMiner M50": {
        "chip_type": "WM1832",
        "fan_count": 4,
        "operating_temp_min": 0,
        "operating_temp_max": 40,
        "noise_level": 75,
        "length_mm": 390,
        "width_mm": 155,
        "height_mm": 208,
        "weight_kg": 10.5,
        "release_date": date(2021, 6, 1),
        "price_usd": 3000
    },
    "WhatsMiner M50S": {
        "chip_type": "WM1832",
        "fan_count": 4,
        "operating_temp_min": 0,
        "operating_temp_max": 40,
        "noise_level": 75,
        "length_mm": 390,
        "width_mm": 155,
        "height_mm": 208,
        "weight_kg": 10.8,
        "release_date": date(2022, 2, 1),
        "price_usd": 3500
    },
    "WhatsMiner M53": {
        "chip_type": "WM2124",
        "fan_count": 4,
        "operating_temp_min": 0,
        "operating_temp_max": 40,
        "noise_level": 78,
        "length_mm": 570,
        "width_mm": 316,
        "height_mm": 430,
        "weight_kg": 33.0,
        "release_date": date(2023, 5, 1),
        "price_usd": 8000
    },
    "WhatsMiner M53S": {
        "chip_type": "WM2124",
        "fan_count": 4,
        "operating_temp_min": 0,
        "operating_temp_max": 40,
        "noise_level": 78,
        "length_mm": 570,
        "width_mm": 316,
        "height_mm": 430,
        "weight_kg": 33.2,
        "release_date": date(2023, 8, 1),
        "price_usd": 8500
    },
    "WhatsMiner M56": {
        "chip_type": "WM2174",
        "fan_count": 4,
        "operating_temp_min": 0,
        "operating_temp_max": 40,
        "noise_level": 75,
        "length_mm": 482,
        "width_mm": 265,
        "height_mm": 388,
        "weight_kg": 18.5,
        "release_date": date(2024, 1, 1),
        "price_usd": 9000
    },
    "WhatsMiner M56S": {
        "chip_type": "WM2174",
        "fan_count": 4,
        "operating_temp_min": 0,
        "operating_temp_max": 40,
        "noise_level": 75,
        "length_mm": 482,
        "width_mm": 265,
        "height_mm": 388,
        "weight_kg": 18.8,
        "release_date": date(2024, 4, 1),
        "price_usd": 10000
    },
    "Avalon Q": {
        "chip_type": "4nm ASIC",
        "fan_count": 2,
        "operating_temp_min": -5,
        "operating_temp_max": 35,
        "noise_level": 55,  # 45-65 dB范围，取中间值
        "length_mm": 455,
        "width_mm": 130.5,
        "height_mm": 440,
        "weight_kg": 10.5,
        "release_date": date(2025, 1, 1),
        "price_usd": 1599
    },
    "Avalon Mini 3": {
        "chip_type": "4nm ASIC",
        "fan_count": 2,
        "operating_temp_min": -5,
        "operating_temp_max": 40,
        "noise_level": 45,  # 33-55 dB, using average
        "length_mm": 760,
        "width_mm": 104,
        "height_mm": 214,
        "weight_kg": 8.35,
        "release_date": date(2024, 10, 1),
        "price_usd": 1500  # Based on market pricing range
    }
}

def get_manufacturer(model_name):
    """根据型号名称获取制造商"""
    if model_name.startswith("Antminer"):
        return "Bitmain"
    elif model_name.startswith("WhatsMiner"):
        return "MicroBT"
    elif model_name.startswith("Avalon"):
        return "Canaan"
    else:
        return "Unknown"

def init_miner_database():
    """初始化矿机数据库"""
    logger.info("开始初始化矿机数据库...")
    
    with app.app_context():
        try:
            # 创建数据库表
            db.create_all()
            logger.info("数据库表创建完成")
            
            # 检查是否已有数据
            existing_count = MinerModel.query.count()
            if existing_count > 0:
                logger.info(f"数据库中已有 {existing_count} 条矿机数据，跳过初始化")
                return
            
            # 导入矿机数据
            imported_count = 0
            for model_name, basic_info in EXISTING_MINER_DATA.items():
                # 检查是否已存在
                existing_miner = MinerModel.query.filter_by(model_name=model_name).first()
                if existing_miner:
                    logger.info(f"矿机 {model_name} 已存在，跳过")
                    continue
                
                # 获取详细信息
                detailed_info = DETAILED_MINER_INFO.get(model_name, {})
                
                # 创建矿机记录
                # 处理详细信息中的price_usd -> reference_price
                detailed_copy = detailed_info.copy()
                if 'price_usd' in detailed_copy:
                    detailed_copy['reference_price'] = detailed_copy.pop('price_usd')
                
                miner = MinerModel(
                    model_name=model_name,
                    manufacturer=get_manufacturer(model_name),
                    reference_hashrate=basic_info["hashrate"],
                    reference_power=basic_info["power_watt"],
                    **detailed_copy
                )
                
                db.session.add(miner)
                imported_count += 1
                logger.info(f"已添加矿机: {model_name} - {basic_info['hashrate']}TH/s, {basic_info['power_watt']}W")
            
            # 提交数据
            db.session.commit()
            logger.info(f"成功导入 {imported_count} 条矿机数据到数据库")
            
        except Exception as e:
            logger.error(f"初始化矿机数据库失败: {e}")
            db.session.rollback()
            raise

def list_miners():
    """列出数据库中的所有矿机"""
    with app.app_context():
        miners = MinerModel.get_active_miners()
        logger.info(f"数据库中共有 {len(miners)} 条活跃矿机记录:")
        
        for miner in miners:
            logger.info(f"- {miner.model_name} ({miner.manufacturer}): {miner.hashrate}TH/s, {miner.power_consumption}W, 能效比:{miner.efficiency}W/TH")

def add_new_miner(model_name, manufacturer, hashrate, power_consumption, **kwargs):
    """添加新的矿机型号"""
    with app.app_context():
        try:
            # 检查是否已存在
            existing = MinerModel.query.filter_by(model_name=model_name).first()
            if existing:
                logger.warning(f"矿机 {model_name} 已存在")
                return existing
            
            # 创建新矿机
            miner = MinerModel(
                model_name=model_name,
                manufacturer=manufacturer,
                reference_hashrate=hashrate,
                reference_power=power_consumption,
                **kwargs
            )
            
            db.session.add(miner)
            db.session.commit()
            logger.info(f"成功添加新矿机: {model_name}")
            return miner
            
        except Exception as e:
            logger.error(f"添加矿机失败: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    # 初始化数据库
    init_miner_database()
    
    # 列出所有矿机
    list_miners()
    
    logger.info("矿机数据库初始化完成！")