#!/usr/bin/env python3
"""
区块链数据自动上链调度器
Blockchain Data Auto-Recording Scheduler

这个模块提供定时任务功能，定期将挖矿数据记录到区块链和IPFS
This module provides scheduled task functionality to periodically record mining data to blockchain and IPFS

特性 Features:
- 定时任务调度 Scheduled task management
- 错误处理和重试机制 Error handling and retry mechanisms  
- 批量数据处理 Batch data processing
- 数据完整性检查 Data integrity checks
- 性能监控 Performance monitoring
"""

import logging
import threading
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import traceback

# 导入项目模块 Import project modules
from app import app, db
from models import BlockchainRecord, BlockchainVerificationStatus
try:
    from blockchain_integration import (
        quick_register_mining_data, 
        quick_verify_mining_data,
        get_blockchain_integration
    )
    BLOCKCHAIN_AVAILABLE = True
except ImportError:
    BLOCKCHAIN_AVAILABLE = False
    
try:
    from api_client import api_client
    API_CLIENT_AVAILABLE = True
except ImportError:
    API_CLIENT_AVAILABLE = False
    
try:
    from mining_calculator import calculate_mining_profitability
    MINING_CALC_AVAILABLE = True
except ImportError:
    MINING_CALC_AVAILABLE = False

# 配置日志 Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BlockchainScheduler:
    """区块链数据自动调度器 Blockchain Data Auto Scheduler"""
    
    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        self.stats = {
            'tasks_executed': 0,
            'successful_records': 0,
            'failed_records': 0,
            'last_execution': None,
            'uptime_start': datetime.utcnow()
        }
        
        # 任务配置 Task configuration
        self.task_config = {
            'daily_summary_recording': {
                'enabled': True,
                'frequency': 'daily',  # daily, hourly, weekly
                'time': '02:00',  # 02:00 UTC
                'retry_attempts': 3,
                'retry_delay': 300  # 5 minutes
            },
            'network_state_recording': {
                'enabled': True,
                'frequency': 'hourly',
                'retry_attempts': 2,
                'retry_delay': 180  # 3 minutes
            },
            'batch_historical_sync': {
                'enabled': False,  # 手动启用 Manual enable
                'frequency': 'weekly',
                'day': 'sunday',
                'time': '01:00',
                'retry_attempts': 5,
                'retry_delay': 600  # 10 minutes
            },
            'data_integrity_check': {
                'enabled': True,
                'frequency': 'daily',
                'time': '03:00',
                'retry_attempts': 2,
                'retry_delay': 300
            }
        }
        
        logger.info("区块链调度器已初始化 Blockchain Scheduler initialized")
    
    def start(self):
        """启动调度器 Start scheduler"""
        if self.is_running:
            logger.warning("调度器已在运行中 Scheduler already running")
            return
        
        try:
            # 注册定时任务 Register scheduled tasks
            self._register_tasks()
            
            # 启动调度器线程 Start scheduler thread
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
            logger.info("区块链调度器已启动 Blockchain Scheduler started")
            
        except Exception as e:
            logger.error(f"启动调度器失败 Failed to start scheduler: {e}")
            self.is_running = False
    
    def stop(self):
        """停止调度器 Stop scheduler"""
        if not self.is_running:
            logger.warning("调度器未在运行 Scheduler not running")
            return
        
        self.is_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        logger.info("区块链调度器已停止 Blockchain Scheduler stopped")
    
    def _register_tasks(self):
        """注册定时任务 Register scheduled tasks"""
        config = self.task_config
        
        # 每日摘要记录 Daily summary recording
        if config['daily_summary_recording']['enabled']:
            schedule.every().day.at(config['daily_summary_recording']['time']).do(
                self._execute_with_retry, 
                self._record_daily_summary,
                'daily_summary_recording'
            )
            logger.info(f"已注册每日摘要任务 Registered daily summary task at {config['daily_summary_recording']['time']}")
        
        # 网络状态记录 Network state recording
        if config['network_state_recording']['enabled']:
            schedule.every().hour.do(
                self._execute_with_retry,
                self._record_network_state,
                'network_state_recording'
            )
            logger.info("已注册每小时网络状态任务 Registered hourly network state task")
        
        # 批量历史同步 Batch historical sync
        if config['batch_historical_sync']['enabled']:
            schedule.every().week.do(
                self._execute_with_retry,
                self._batch_historical_sync,
                'batch_historical_sync'
            )
            logger.info("已注册每周批量同步任务 Registered weekly batch sync task")
        
        # 数据完整性检查 Data integrity check
        if config['data_integrity_check']['enabled']:
            schedule.every().day.at(config['data_integrity_check']['time']).do(
                self._execute_with_retry,
                self._check_data_integrity,
                'data_integrity_check'
            )
            logger.info(f"已注册数据完整性检查任务 Registered data integrity check at {config['data_integrity_check']['time']}")
    
    def _run_scheduler(self):
        """运行调度器主循环 Run scheduler main loop"""
        logger.info("调度器主循环已启动 Scheduler main loop started")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(30)  # 检查间隔30秒 Check every 30 seconds
                
            except Exception as e:
                logger.error(f"调度器主循环错误 Scheduler main loop error: {e}")
                time.sleep(60)  # 错误后等待1分钟 Wait 1 minute after error
    
    def _execute_with_retry(self, task_func, task_name: str):
        """执行任务并支持重试 Execute task with retry support"""
        config = self.task_config.get(task_name, {})
        max_attempts = config.get('retry_attempts', 3)
        retry_delay = config.get('retry_delay', 300)
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"执行任务 Executing task: {task_name} (尝试 attempt {attempt}/{max_attempts})")
                
                with app.app_context():
                    result = task_func()
                    
                    if result:
                        self.stats['tasks_executed'] += 1
                        self.stats['successful_records'] += 1
                        self.stats['last_execution'] = datetime.utcnow()
                        logger.info(f"任务成功 Task successful: {task_name}")
                        return result
                    else:
                        raise Exception(f"任务返回失败 Task returned failure: {task_name}")
                        
            except Exception as e:
                logger.error(f"任务执行失败 Task execution failed: {task_name} (尝试 attempt {attempt}/{max_attempts}): {e}")
                
                if attempt < max_attempts:
                    logger.info(f"等待重试 Waiting for retry: {retry_delay}秒 seconds")
                    time.sleep(retry_delay)
                else:
                    self.stats['failed_records'] += 1
                    logger.error(f"任务最终失败 Task finally failed: {task_name}")
                    
                    # 记录失败到数据库 Record failure to database
                    self._record_task_failure(task_name, str(e))
    
    def _record_daily_summary(self) -> bool:
        """记录每日挖矿摘要 Record daily mining summary"""
        try:
            logger.info("开始记录每日挖矿摘要 Starting daily mining summary recording")
            
            # 获取网络信息 Get network information
            btc_price = self._get_btc_price()
            network_info = self._get_bitcoin_network_info()
            
            if not btc_price or not network_info:
                logger.error("无法获取网络信息 Cannot get network information")
                return False
            
            # 构建每日摘要数据 Build daily summary data
            daily_summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "type": "daily_mining_summary",
                "btc_price": btc_price,
                "network_hashrate": network_info.get('hashrate', 0),
                "network_difficulty": network_info.get('difficulty', 0),
                "block_reward": network_info.get('block_reward', 6.25),
                "average_block_time": network_info.get('average_block_time', 600),
                "network_status": self._get_blockchain_status(),
                "recorded_by": "blockchain_scheduler_daily",
                "calculation_method": "network_summary",
                "data_source": "real_time_api"
            }
            
            # 记录到区块链 Record to blockchain
            result = quick_register_mining_data(daily_summary)
            
            if result:
                logger.info(f"每日摘要已记录 Daily summary recorded: {result['data_hash'][:16]}...")
                return True
            else:
                logger.error("每日摘要记录失败 Daily summary recording failed")
                return False
                
        except Exception as e:
            logger.error(f"记录每日摘要时出错 Error recording daily summary: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _record_network_state(self) -> bool:
        """记录网络状态 Record network state"""
        try:
            logger.info("开始记录网络状态 Starting network state recording")
            
            # 获取网络信息 Get network information
            btc_price = self._get_btc_price()
            network_info = self._get_bitcoin_network_info()
            
            if not btc_price or not network_info:
                logger.warning("无法获取完整网络信息，跳过此次记录 Cannot get complete network info, skipping")
                return False
            
            # 构建网络状态数据 Build network state data
            network_state = {
                "timestamp": datetime.utcnow().isoformat(),
                "hour": datetime.utcnow().strftime("%Y-%m-%d_%H"),
                "type": "hourly_network_state",
                "btc_price": btc_price,
                "network_hashrate": network_info.get('hashrate', 0),
                "network_difficulty": network_info.get('difficulty', 0),
                "block_reward": network_info.get('block_reward', 6.25),
                "recorded_by": "blockchain_scheduler_hourly",
                "calculation_method": "network_monitoring",
                "data_source": "real_time_api"
            }
            
            # 记录到区块链 Record to blockchain
            result = quick_register_mining_data(network_state)
            
            if result:
                logger.info(f"网络状态已记录 Network state recorded: {result['data_hash'][:16]}...")
                return True
            else:
                logger.warning("网络状态记录失败 Network state recording failed")
                return False
                
        except Exception as e:
            logger.error(f"记录网络状态时出错 Error recording network state: {e}")
            return False
    
    def _batch_historical_sync(self) -> bool:
        """批量历史数据同步 Batch historical data sync"""
        try:
            logger.info("开始批量历史数据同步 Starting batch historical data sync")
            
            # 查找未上链的区块链记录 Find unrecorded blockchain records
            unrecorded_records = db.session.query(BlockchainRecord).filter(
                BlockchainRecord.verification_status == BlockchainVerificationStatus.REGISTERED,
                BlockchainRecord.transaction_hash.is_(None)
            ).limit(50).all()  # 限制每次处理50条 Limit 50 records per batch
            
            if not unrecorded_records:
                logger.info("没有找到需要同步的历史记录 No historical records found for sync")
                return True
            
            logger.info(f"找到 {len(unrecorded_records)} 条记录需要同步 Found {len(unrecorded_records)} records for sync")
            
            # 批量处理 Batch processing
            sync_data = []
            for record in unrecorded_records:
                try:
                    # 从summary中恢复数据 Restore data from summary
                    mining_data = json.loads(record.mining_data_summary) if record.mining_data_summary else {}
                    mining_data['sync_type'] = 'historical_batch'
                    mining_data['original_timestamp'] = record.data_timestamp.isoformat() if record.data_timestamp else None
                    sync_data.append(mining_data)
                    
                except Exception as record_error:
                    logger.error(f"处理记录失败 Failed to process record {record.id}: {record_error}")
                    continue
            
            if sync_data:
                # 批量上链 Batch register to blockchain
                batch_result = self._batch_register_mining_data(sync_data)
                
                if batch_result:
                    logger.info(f"批量同步成功 Batch sync successful: {len(batch_result)} 条记录 records")
                    return True
                else:
                    logger.error("批量同步失败 Batch sync failed")
                    return False
            else:
                logger.warning("没有有效数据可同步 No valid data for sync")
                return False
                
        except Exception as e:
            logger.error(f"批量历史数据同步时出错 Error in batch historical sync: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _check_data_integrity(self) -> bool:
        """检查数据完整性 Check data integrity"""
        try:
            logger.info("开始数据完整性检查 Starting data integrity check")
            
            # 查询最近7天的记录 Query records from last 7 days
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_records = db.session.query(BlockchainRecord).filter(
                BlockchainRecord.data_timestamp >= seven_days_ago,
                BlockchainRecord.verification_status == BlockchainVerificationStatus.REGISTERED
            ).all()
            
            verified_count = 0
            failed_count = 0
            
            for record in recent_records:
                try:
                    # 验证区块链数据 Verify blockchain data
                    if record.data_hash and record.ipfs_cid:
                        verification_result = self._verify_blockchain_data(
                            record.data_hash, 
                            record.ipfs_cid
                        )
                        
                        if verification_result and verification_result.get('is_valid', False):
                            verified_count += 1
                            
                            # 更新验证状态 Update verification status
                            record.verification_status = BlockchainVerificationStatus.VERIFIED
                        else:
                            failed_count += 1
                            logger.warning(f"数据验证失败 Data verification failed for record {record.id}")
                            record.verification_status = BlockchainVerificationStatus.FAILED
                    
                except Exception as verify_error:
                    logger.error(f"验证记录失败 Failed to verify record {record.id}: {verify_error}")
                    failed_count += 1
                    continue
            
            # 提交数据库更改 Commit database changes
            db.session.commit()
            
            logger.info(f"数据完整性检查完成 Data integrity check completed: {verified_count} 验证成功 verified, {failed_count} 失败 failed")
            
            # 记录检查结果 Record check results
            integrity_summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "data_integrity_check",
                "total_checked": len(recent_records),
                "verified_count": verified_count,
                "failed_count": failed_count,
                "check_period_days": 7,
                "recorded_by": "blockchain_scheduler_integrity",
                "calculation_method": "data_verification",
                "data_source": "blockchain_verification"
            }
            
            # 将检查结果也上链 Record check results to blockchain
            result = quick_register_mining_data(integrity_summary)
            
            if result:
                logger.info(f"完整性检查结果已记录 Integrity check results recorded: {result['data_hash'][:16]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"数据完整性检查时出错 Error in data integrity check: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _record_task_failure(self, task_name: str, error_message: str):
        """记录任务失败信息 Record task failure information"""
        try:
            with app.app_context():
                failure_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "scheduler_task_failure",
                    "task_name": task_name,
                    "error_message": error_message,
                    "recorded_by": "blockchain_scheduler_error",
                    "calculation_method": "error_logging",
                    "data_source": "scheduler_internal"
                }
                
                # 尝试记录错误到区块链 Try to record error to blockchain
                result = quick_register_mining_data(failure_record)
                
                if result:
                    logger.info(f"任务失败已记录到区块链 Task failure recorded to blockchain: {result['data_hash'][:16]}...")
                else:
                    logger.warning("无法将任务失败记录到区块链 Cannot record task failure to blockchain")
                    
        except Exception as e:
            logger.error(f"记录任务失败信息时出错 Error recording task failure: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息 Get scheduler statistics"""
        uptime = datetime.utcnow() - self.stats['uptime_start']
        
        return {
            'is_running': self.is_running,
            'uptime_seconds': uptime.total_seconds(),
            'uptime_hours': uptime.total_seconds() / 3600,
            'tasks_executed': self.stats['tasks_executed'],
            'successful_records': self.stats['successful_records'],
            'failed_records': self.stats['failed_records'],
            'success_rate': (self.stats['successful_records'] / max(self.stats['tasks_executed'], 1)) * 100,
            'last_execution': self.stats['last_execution'].isoformat() if self.stats['last_execution'] else None,
            'task_config': self.task_config
        }
    
    def force_execute_task(self, task_name: str) -> bool:
        """强制执行指定任务 Force execute specific task"""
        task_methods = {
            'daily_summary_recording': self._record_daily_summary,
            'network_state_recording': self._record_network_state,
            'batch_historical_sync': self._batch_historical_sync,
            'data_integrity_check': self._check_data_integrity
        }
        
        if task_name not in task_methods:
            logger.error(f"未知任务 Unknown task: {task_name}")
            return False
        
        logger.info(f"强制执行任务 Force executing task: {task_name}")
        
        try:
            with app.app_context():
                result = task_methods[task_name]()
                if result:
                    logger.info(f"强制执行成功 Force execution successful: {task_name}")
                else:
                    logger.error(f"强制执行失败 Force execution failed: {task_name}")
                return result
                
        except Exception as e:
            logger.error(f"强制执行任务时出错 Error in force execution: {task_name}: {e}")
            return False
    
    # 辅助方法 Helper methods
    def _get_btc_price(self) -> Optional[float]:
        """获取BTC价格 Get BTC price"""
        try:
            if API_CLIENT_AVAILABLE:
                return api_client.get_btc_price()
            else:
                logger.warning("API客户端不可用，使用默认价格 API client unavailable, using default price")
                return 80000.0  # 默认价格
        except Exception as e:
            logger.error(f"获取BTC价格失败 Failed to get BTC price: {e}")
            return 80000.0
    
    def _get_bitcoin_network_info(self) -> Optional[Dict[str, Any]]:
        """获取比特币网络信息 Get Bitcoin network info"""
        try:
            if API_CLIENT_AVAILABLE:
                market_data = api_client.get_market_data()
                return {
                    'hashrate': market_data.get('network_hashrate', 900.0),  # EH/s
                    'difficulty': market_data.get('network_difficulty', 119.12),
                    'block_reward': 3.125,  # Current block reward after 2024 halving
                    'average_block_time': 600  # 10 minutes in seconds
                }
            else:
                logger.warning("API客户端不可用，使用默认网络信息 API client unavailable, using default network info")
                return {
                    'hashrate': 900.0,
                    'difficulty': 119.12,
                    'block_reward': 3.125,
                    'average_block_time': 600
                }
        except Exception as e:
            logger.error(f"获取网络信息失败 Failed to get network info: {e}")
            return None
    
    def _get_blockchain_status(self) -> str:
        """获取区块链状态 Get blockchain status"""
        try:
            if BLOCKCHAIN_AVAILABLE:
                integration = get_blockchain_integration()
                if integration and integration.w3 and integration.w3.is_connected():
                    return "connected"
                else:
                    return "disconnected"
            else:
                return "unavailable"
        except Exception as e:
            logger.error(f"获取区块链状态失败 Failed to get blockchain status: {e}")
            return "error"
    
    def _batch_register_mining_data(self, batch_data: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """批量注册挖矿数据 Batch register mining data"""
        try:
            results = []
            for data in batch_data:
                result = quick_register_mining_data(data)
                if result:
                    results.append(result)
                else:
                    logger.warning(f"单个数据记录失败 Individual data record failed: {data.get('timestamp', 'unknown')}")
            
            return results if results else None
            
        except Exception as e:
            logger.error(f"批量注册失败 Batch registration failed: {e}")
            return None
    
    def _verify_blockchain_data(self, data_hash: str, ipfs_cid: str) -> Optional[Dict[str, Any]]:
        """验证区块链数据 Verify blockchain data"""
        try:
            # 使用quick_verify_mining_data进行验证
            result = quick_verify_mining_data(data_hash)
            if result and result.get('valid', False):
                return {
                    'is_valid': True,
                    'data_hash': data_hash,
                    'ipfs_cid': ipfs_cid,
                    'verification_result': result
                }
            else:
                return {
                    'is_valid': False,
                    'data_hash': data_hash,
                    'ipfs_cid': ipfs_cid,
                    'error': result.get('error', 'Verification failed')
                }
                
        except Exception as e:
            logger.error(f"数据验证失败 Data verification failed: {e}")
            return {
                'is_valid': False,
                'data_hash': data_hash,
                'ipfs_cid': ipfs_cid,
                'error': str(e)
            }


# 全局调度器实例 Global scheduler instance
scheduler_instance = None

def get_scheduler() -> BlockchainScheduler:
    """获取调度器实例 Get scheduler instance"""
    global scheduler_instance
    if scheduler_instance is None:
        scheduler_instance = BlockchainScheduler()
    return scheduler_instance

def start_blockchain_scheduler():
    """启动区块链调度器 Start blockchain scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler

def stop_blockchain_scheduler():
    """停止区块链调度器 Stop blockchain scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()

if __name__ == "__main__":
    # 测试运行 Test run
    logging.basicConfig(level=logging.DEBUG)
    
    print("启动区块链调度器测试 Starting blockchain scheduler test...")
    
    scheduler = BlockchainScheduler()
    
    try:
        scheduler.start()
        print("调度器已启动，按Ctrl+C停止 Scheduler started, press Ctrl+C to stop")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n正在停止调度器 Stopping scheduler...")
        scheduler.stop()
        print("调度器已停止 Scheduler stopped")