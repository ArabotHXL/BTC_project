import logging
import json
from datetime import datetime
from tools.test_cgminer import CGMinerTester
from models import db, HostingMiner

logger = logging.getLogger(__name__)

def collect_all_miners_telemetry():
    """
    采集所有矿机的CGMiner遥测数据
    
    查询所有有IP地址的矿机（排除维护中状态），使用CGMinerTester采集遥测数据
    并更新数据库。
    
    Returns:
        dict: {'success': int, 'failed': int} 成功和失败的数量
    """
    try:
        miners = HostingMiner.query.filter(
            HostingMiner.ip_address.isnot(None),
            HostingMiner.status != 'maintenance'
        ).all()
        
        logger.info(f"开始采集 {len(miners)} 台矿机的CGMiner数据")
        
        success_count = 0
        fail_count = 0
        
        for miner in miners:
            try:
                db.session.refresh(miner)
                
                tester = CGMinerTester(miner.ip_address, timeout=3)
                telemetry = tester.get_telemetry_data()
                
                if telemetry:
                    update_miner_telemetry_data(miner, telemetry)
                    success_count += 1
                    logger.debug(f"矿机 {miner.serial_number} 数据采集成功")
                else:
                    mark_miner_offline(miner)
                    fail_count += 1
                    logger.debug(f"矿机 {miner.serial_number} 无法连接")
            except Exception as e:
                logger.error(f"采集矿机 {miner.serial_number} 失败: {e}")
                try:
                    db.session.refresh(miner)
                except:
                    pass
                mark_miner_offline(miner)
                fail_count += 1
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"数据库提交失败: {e}")
            db.session.rollback()
        
        logger.info(f"CGMiner数据采集完成: {success_count}成功, {fail_count}失败")
        return {'success': success_count, 'failed': fail_count}
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"CGMiner数据采集任务异常: {e}", exc_info=True)
        return {'success': 0, 'failed': 0, 'error': str(e)}

def update_miner_telemetry_data(miner, telemetry):
    """
    更新矿机遥测数据
    
    复用 modules/hosting/routes.py 的 update_miner_telemetry 函数逻辑
    
    Args:
        miner: HostingMiner对象
        telemetry: CGMinerTester.get_telemetry_data()返回的字典
    """
    try:
        if 'online' in telemetry:
            miner.cgminer_online = telemetry['online']
            if telemetry['online']:
                miner.last_seen = datetime.utcnow()
        
        if telemetry.get('online'):
            if 'hashrate_5s' in telemetry:
                miner.hashrate_5s = telemetry['hashrate_5s']
            if 'hashrate_avg' in telemetry:
                miner.actual_hashrate = telemetry['hashrate_avg']
            if 'temperature_avg' in telemetry and telemetry['temperature_avg']:
                miner.temperature_avg = telemetry['temperature_avg']
            if 'temperature_max' in telemetry and telemetry['temperature_max']:
                miner.temperature_max = telemetry['temperature_max']
            
            if 'fan_speeds' in telemetry and telemetry['fan_speeds']:
                miner.fan_speeds = json.dumps(telemetry['fan_speeds'])
            if 'fan_avg' in telemetry and telemetry['fan_avg']:
                miner.fan_avg = telemetry['fan_avg']
            
            if 'accepted_shares' in telemetry:
                miner.accepted_shares = telemetry['accepted_shares']
            if 'rejected_shares' in telemetry:
                miner.rejected_shares = telemetry['rejected_shares']
            if 'hardware_errors' in telemetry:
                miner.hardware_errors = telemetry['hardware_errors']
            if 'reject_rate' in telemetry:
                miner.reject_rate = telemetry['reject_rate']
            
            if 'uptime_seconds' in telemetry:
                miner.uptime_seconds = telemetry['uptime_seconds']
            if 'pool_url' in telemetry:
                miner.pool_url = telemetry['pool_url']
            if 'pool_worker' in telemetry:
                miner.pool_worker = telemetry['pool_worker']
            
            if miner.status == 'offline':
                miner.status = 'active'
        
        miner.updated_at = datetime.utcnow()
        
    except Exception as e:
        logger.error(f"更新矿机 {miner.serial_number} 遥测数据失败: {e}")
        raise

def mark_miner_offline(miner):
    """
    标记矿机为离线状态
    
    Args:
        miner: HostingMiner对象
    """
    try:
        miner.cgminer_online = False
        
        time_since_seen = datetime.utcnow() - (miner.last_seen or datetime.utcnow())
        if miner.status == 'active' and time_since_seen.total_seconds() > 300:
            miner.status = 'offline'
        
        miner.updated_at = datetime.utcnow()
        
    except Exception as e:
        logger.error(f"标记矿机 {miner.serial_number} 离线失败: {e}")
        raise
