import logging
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from tools.test_cgminer import CGMinerTester
from models import db, HostingMiner

logger = logging.getLogger(__name__)

MINER_TIMEOUT = 1
MAX_CONCURRENT_POLLS = 20
SKIP_OFFLINE_HOURS = 24

def poll_single_miner(miner_id, ip_address, serial_number):
    """
    采集单台矿机数据（线程安全）
    
    Args:
        miner_id: 矿机ID
        ip_address: IP地址
        serial_number: 序列号
    
    Returns:
        tuple: (miner_id, telemetry_data or None, error_msg or None)
    """
    try:
        tester = CGMinerTester(ip_address, timeout=MINER_TIMEOUT)
        telemetry = tester.get_telemetry_data()
        return (miner_id, telemetry, None)
    except Exception as e:
        return (miner_id, None, str(e))

def collect_all_miners_telemetry():
    """
    采集所有矿机的CGMiner遥测数据（并发优化版）
    
    使用线程池并发采集，每台矿机1秒超时，跳过长期离线矿机
    
    Returns:
        dict: {'success': int, 'failed': int, 'skipped': int}
    """
    try:
        skip_threshold = datetime.utcnow() - timedelta(hours=SKIP_OFFLINE_HOURS)
        
        miners = HostingMiner.query.filter(
            HostingMiner.ip_address.isnot(None),
            HostingMiner.status != 'maintenance',
            db.or_(
                HostingMiner.status != 'offline',
                HostingMiner.last_seen > skip_threshold,
                HostingMiner.last_seen.is_(None)
            )
        ).all()
        
        total_miners = HostingMiner.query.filter(
            HostingMiner.ip_address.isnot(None),
            HostingMiner.status != 'maintenance'
        ).count()
        
        skipped = total_miners - len(miners)
        
        logger.info(f"开始采集 {len(miners)} 台矿机的CGMiner数据 (跳过{skipped}台长期离线)")
        
        if not miners:
            return {'success': 0, 'failed': 0, 'skipped': skipped}
        
        miner_map = {m.id: m for m in miners}
        poll_tasks = [(m.id, m.ip_address, m.serial_number) for m in miners]
        
        success_count = 0
        fail_count = 0
        
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_POLLS) as executor:
            futures = {
                executor.submit(poll_single_miner, mid, ip, sn): mid 
                for mid, ip, sn in poll_tasks
            }
            
            for future in as_completed(futures, timeout=30):
                try:
                    miner_id, telemetry, error = future.result(timeout=2)
                    miner = miner_map.get(miner_id)
                    
                    if not miner:
                        continue
                    
                    if telemetry:
                        update_miner_telemetry_data(miner, telemetry)
                        success_count += 1
                    else:
                        mark_miner_offline(miner)
                        fail_count += 1
                        if error:
                            logger.debug(f"❌ 连接超时: {miner.ip_address}:4028")
                            
                except Exception as e:
                    fail_count += 1
                    logger.debug(f"采集任务异常: {e}")
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"数据库提交失败: {e}")
            db.session.rollback()
        
        logger.info(f"CGMiner数据采集完成: {success_count}成功, {fail_count}失败, {skipped}跳过")
        return {'success': success_count, 'failed': fail_count, 'skipped': skipped}
        
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
