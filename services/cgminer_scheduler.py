import logging
import os
import socket
import atexit
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

class CGMinerSchedulerService:
    """
    CGMiner数据采集调度服务
    
    使用APScheduler的BackgroundScheduler在后台定时采集所有矿机的CGMiner遥测数据
    集成SchedulerLock机制防止多worker重复启动
    """
    
    def __init__(self):
        executors = {
            'default': ThreadPoolExecutor(max_workers=2)
        }
        self.scheduler = BackgroundScheduler(executors=executors)
        atexit.register(self.stop)
        
        self._app = None
        self._is_running = False
        self.lock_key = "cgminer_scheduler_lock"
        self.process_id = os.getpid()
        self.hostname = socket.gethostname()
    
    def set_flask_app(self, app):
        """设置Flask应用实例"""
        self._app = app
        logger.info(f"CGMiner调度器绑定到Flask应用 (PID={self.process_id}, Host={self.hostname})")
    
    def _acquire_scheduler_lock(self):
        """
        获取调度器锁，防止多worker重复启动
        
        Returns:
            bool: 成功获取锁返回True，否则返回False
        """
        if not self._app:
            logger.error("Flask应用未设置，无法获取调度器锁")
            return False
        
        try:
            with self._app.app_context():
                from models import SchedulerLock, db
                
                lock_timeout = 300
                worker_info = f"CGMiner Collector - PID {self.process_id} @ {self.hostname}"
                
                acquired = SchedulerLock.acquire_lock(
                    lock_key=self.lock_key,
                    process_id=self.process_id,
                    hostname=self.hostname,
                    timeout_seconds=lock_timeout,
                    worker_info=worker_info
                )
                
                if acquired:
                    logger.info(f"🔒 CGMiner调度器获取锁成功: {worker_info}")
                else:
                    logger.info(f"⏳ CGMiner调度器锁被其他worker持有，跳过启动")
                
                return acquired
                
        except Exception as e:
            logger.error(f"获取CGMiner调度器锁失败: {e}", exc_info=True)
            return False
    
    def _release_scheduler_lock(self):
        """释放调度器锁"""
        if not self._app:
            return
        
        try:
            with self._app.app_context():
                from models import SchedulerLock
                
                released = SchedulerLock.release_lock(
                    lock_key=self.lock_key,
                    process_id=self.process_id
                )
                
                if released:
                    logger.info(f"🔓 CGMiner调度器释放锁成功")
                    
        except Exception as e:
            logger.error(f"释放CGMiner调度器锁失败: {e}")
    
    def _heartbeat_task(self):
        """
        心跳任务，定期刷新锁
        """
        if not self._app:
            return
        
        try:
            with self._app.app_context():
                from models import SchedulerLock, db
                
                lock = SchedulerLock.get_active_lock(self.lock_key)
                if lock and lock.process_id == self.process_id:
                    lock.refresh_lock(timeout_seconds=300)
                    db.session.commit()
                    logger.debug(f"🔄 CGMiner调度器心跳刷新")
                else:
                    logger.warning(f"⚠️ 心跳失败: 锁已丢失，停止调度器")
                    self.stop()
                    
        except Exception as e:
            logger.error(f"CGMiner调度器心跳失败: {e}")
    
    def _collect_telemetry_job(self):
        """
        定时任务：采集所有矿机的CGMiner遥测数据
        """
        if not self._app:
            logger.error("Flask应用未设置，无法执行采集任务")
            return
        
        try:
            with self._app.app_context():
                from services.cgminer_collector import collect_all_miners_telemetry
                
                logger.info("⏰ 开始执行CGMiner数据采集任务")
                result = collect_all_miners_telemetry()
                
                logger.info(
                    f"✅ CGMiner数据采集完成: "
                    f"成功={result.get('success', 0)}, "
                    f"失败={result.get('failed', 0)}"
                )
                
        except Exception as e:
            logger.error(f"❌ CGMiner数据采集任务异常: {e}", exc_info=True)
    
    def start_scheduler(self):
        """
        启动调度器
        
        使用SchedulerLock机制确保只有一个worker实例运行调度器
        """
        if self._is_running:
            logger.info("CGMiner调度器已在运行中")
            return
        
        if not self._app:
            logger.error("Flask应用未设置，无法启动调度器")
            return
        
        if not self._acquire_scheduler_lock():
            logger.info("未获得调度器锁，跳过启动")
            return
        
        try:
            self.scheduler.add_job(
                id='cgminer_collector',
                func=self._collect_telemetry_job,
                trigger=IntervalTrigger(seconds=60),
                max_instances=1,
                coalesce=True,
                replace_existing=True
            )
            logger.info("✅ 已添加CGMiner采集任务: 每60秒执行一次")
            
            self.scheduler.add_job(
                id='cgminer_scheduler_heartbeat',
                func=self._heartbeat_task,
                trigger=IntervalTrigger(seconds=60),
                max_instances=1,
                coalesce=True,
                replace_existing=True
            )
            logger.info("✅ 已添加调度器心跳任务: 每60秒刷新锁")
            
            self.scheduler.start()
            self._is_running = True
            
            logger.info(
                f"🚀 CGMiner调度器启动成功 "
                f"(PID={self.process_id}, Host={self.hostname})"
            )
            
        except Exception as e:
            logger.error(f"启动CGMiner调度器失败: {e}", exc_info=True)
            self._release_scheduler_lock()
    
    def stop(self):
        """确保调度器正确停止"""
        if self.scheduler and self.scheduler.running:
            logger.info("Stopping CGMiner scheduler...")
            try:
                self.scheduler.shutdown(wait=True)
                logger.info("🛑 CGMiner调度器已停止")
            except Exception as e:
                logger.error(f"停止CGMiner调度器失败: {e}")
        
        if self._is_running:
            self._release_scheduler_lock()
            self._is_running = False
    
    def get_scheduler_status(self):
        """
        获取调度器状态
        
        Returns:
            dict: 调度器状态信息
        """
        jobs = []
        if self.scheduler:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None
                })
        
        return {
            'is_running': self._is_running,
            'process_id': self.process_id,
            'hostname': self.hostname,
            'lock_key': self.lock_key,
            'jobs': jobs
        }

cgminer_scheduler = CGMinerSchedulerService()

def set_flask_app(app):
    """设置Flask应用实例（供外部调用）"""
    cgminer_scheduler.set_flask_app(app)
