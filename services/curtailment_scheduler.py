import logging
import os
import socket
import atexit
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from gmail_oauth_service import send_curtailment_notification_email

logger = logging.getLogger(__name__)

class CurtailmentSchedulerService:
    """
    限电调度服务
    
    功能：
    1. 定时检查待执行的限电计划
    2. 执行前提醒通知
    3. 自动执行限电计划
    4. 自动恢复矿机
    5. 心跳保持调度器锁
    """
    
    def __init__(self):
        executors = {
            'default': ThreadPoolExecutor(max_workers=2)
        }
        self.scheduler = BackgroundScheduler(executors=executors)
        atexit.register(self.stop)
        
        self._app = None
        self._is_running = False
        self.lock_key = "curtailment_scheduler_lock"
        self.process_id = os.getpid()
        self.hostname = socket.gethostname()
        self._notified_plans = set()
        self._notification_failures = {}
    
    def set_flask_app(self, app):
        """设置Flask应用实例"""
        self._app = app
        logger.info(f"限电调度器绑定到Flask应用 (PID={self.process_id}, Host={self.hostname})")
    
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
                worker_info = f"Curtailment Scheduler - PID {self.process_id} @ {self.hostname}"
                
                acquired = SchedulerLock.acquire_lock(
                    lock_key=self.lock_key,
                    process_id=self.process_id,
                    hostname=self.hostname,
                    timeout_seconds=lock_timeout,
                    worker_info=worker_info
                )
                
                if acquired:
                    logger.info(f"🔒 限电调度器获取锁成功: {worker_info}")
                else:
                    logger.info(f"⏳ 限电调度器锁被其他worker持有，跳过启动")
                
                return acquired
                
        except Exception as e:
            logger.error(f"获取限电调度器锁失败: {e}", exc_info=True)
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
                    logger.info(f"🔓 限电调度器释放锁成功")
                    
        except Exception as e:
            logger.error(f"释放限电调度器锁失败: {e}")
    
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
                    logger.debug(f"🔄 限电调度器心跳刷新")
                else:
                    logger.warning(f"⚠️ 心跳失败: 锁已丢失，停止调度器")
                    self.stop()
                    
        except Exception as e:
            logger.error(f"限电调度器心跳失败: {e}")
    
    def _check_pending_plans(self):
        """
        定时任务：检查待执行的限电计划
        
        检查逻辑：
        1. 找到状态为PENDING或APPROVED的计划
        2. 检查开始时间是否到达
        3. 执行限电（根据execution_mode）
        4. 调用CurtailmentPlanService执行
        """
        if not self._app:
            logger.error("Flask应用未设置，无法检查计划")
            return
        
        try:
            with self._app.app_context():
                from models import CurtailmentPlan, PlanStatus, ExecutionMode
                from services.curtailment_plan_service import CurtailmentPlanService
                
                now = datetime.utcnow()
                
                pending_plans = CurtailmentPlan.query.filter(  # type: ignore
                    CurtailmentPlan.status.in_([PlanStatus.PENDING, PlanStatus.APPROVED]),  # type: ignore
                    CurtailmentPlan.scheduled_start_time <= now  # type: ignore
                ).all()
                
                if not pending_plans:
                    logger.debug("✅ 没有待执行的限电计划")
                    return
                
                logger.info(f"📋 发现 {len(pending_plans)} 个待执行的限电计划")
                
                for plan in pending_plans:
                    try:
                        # 检查执行模式
                        if plan.execution_mode == ExecutionMode.AUTO:
                            should_execute = True
                        elif plan.execution_mode == ExecutionMode.SEMI_AUTO:
                            should_execute = (plan.status == PlanStatus.APPROVED)
                            if not should_execute:
                                logger.info(f"⏸️ 半自动计划需要审批: {plan.plan_name}")
                        else:
                            should_execute = False
                            logger.info(f"✋ 手动计划不自动执行: {plan.plan_name}")
                        
                        if should_execute:
                            logger.info(f"⚡ 开始执行限电计划: {plan.plan_name} (ID={plan.id})")
                            result = CurtailmentPlanService.execute_plan(plan.id)
                            
                            if result['success']:
                                logger.info(
                                    f"✅ 计划执行成功: {result['plan_name']} | "
                                    f"关闭={result['miners_shutdown']}, "
                                    f"失败={result['miners_failed']}, "
                                    f"节省={result['total_power_saved_kw']}kW"
                                )
                            else:
                                logger.error(f"❌ 计划执行失败: {result.get('error', 'Unknown error')}")
                    
                    except Exception as e:
                        logger.error(f"❌ 执行计划失败 {plan.plan_name}: {e}", exc_info=True)
                        
        except Exception as e:
            logger.error(f"❌ 检查待执行计划任务异常: {e}", exc_info=True)
    
    def _check_recovery_plans(self):
        """
        定时任务：检查需要恢复的限电计划
        
        检查逻辑：
        1. 找到状态为EXECUTING且已过结束时间的计划
        2. 先更新status = RECOVERY_PENDING（标记即将恢复）
        3. 调用CurtailmentPlanService恢复被限电的矿机
        4. Service层会根据恢复结果设置最终状态（COMPLETED或RECOVERY_PENDING）
        """
        if not self._app:
            logger.error("Flask应用未设置，无法检查恢复")
            return
        
        try:
            with self._app.app_context():
                from models import CurtailmentPlan, PlanStatus, db
                from services.curtailment_plan_service import CurtailmentPlanService
                
                now = datetime.utcnow()
                
                recovery_plans = CurtailmentPlan.query.filter(  # type: ignore
                    CurtailmentPlan.status == PlanStatus.EXECUTING,  # type: ignore
                    CurtailmentPlan.scheduled_end_time.isnot(None),  # type: ignore
                    CurtailmentPlan.scheduled_end_time <= now  # type: ignore
                ).all()
                
                if not recovery_plans:
                    logger.debug("✅ 没有需要恢复的限电计划")
                    return
                
                logger.info(f"🔄 发现 {len(recovery_plans)} 个需要恢复的计划")
                
                for plan in recovery_plans:
                    try:
                        # 先更新状态为RECOVERY_PENDING（标记即将恢复）
                        plan.status = PlanStatus.RECOVERY_PENDING
                        db.session.commit()
                        logger.info(f"  📌 计划状态已更新为RECOVERY_PENDING: {plan.plan_name}")
                        
                        # 调用服务层恢复矿机
                        logger.info(f"🔌 开始恢复计划: {plan.plan_name} (ID={plan.id})")
                        result = CurtailmentPlanService.recover_plan(plan.id)
                        
                        if result['success']:
                            logger.info(
                                f"✅ 计划恢复成功: {result['plan_name']} | "
                                f"恢复={result['miners_recovered']}, "
                                f"失败={result['miners_failed']}, "
                                f"最终状态={result['plan_status']}"
                            )
                        else:
                            logger.error(f"❌ 计划恢复失败: {result.get('error', 'Unknown error')}")
                        
                    except Exception as e:
                        logger.error(f"❌ 恢复计划失败 {plan.plan_name}: {e}", exc_info=True)
                        
        except Exception as e:
            logger.error(f"❌ 检查恢复计划任务异常: {e}", exc_info=True)
    
    def _send_upcoming_notifications(self):
        """
        定时任务：发送即将执行的计划提醒
        
        检查逻辑：
        1. 找到15分钟内即将执行的计划
        2. 检查是否已发送提醒
        3. 发送提醒通知（邮件）
        """
        if not self._app:
            logger.error("Flask应用未设置，无法发送通知")
            return
        
        try:
            with self._app.app_context():
                from models import CurtailmentPlan, PlanStatus, User, db
                
                now = datetime.utcnow()
                notify_window_start = now
                notify_window_end = now + timedelta(minutes=15)
                
                upcoming_plans = CurtailmentPlan.query.filter(  # type: ignore
                    CurtailmentPlan.status.in_([PlanStatus.PENDING, PlanStatus.APPROVED]),  # type: ignore
                    CurtailmentPlan.scheduled_start_time >= notify_window_start,  # type: ignore
                    CurtailmentPlan.scheduled_start_time <= notify_window_end  # type: ignore
                ).all()
                
                if not upcoming_plans:
                    logger.debug("✅ 没有即将执行的计划需要通知")
                    return
                
                logger.info(f"🔔 发现 {len(upcoming_plans)} 个即将执行的计划")
                
                creator_ids = [p.created_by_id for p in upcoming_plans if p.created_by_id]
                creators_map = {}
                if creator_ids:
                    creators = User.query.filter(User.id.in_(creator_ids)).all()
                    creators_map = {u.id: u for u in creators}
                
                for plan in upcoming_plans:
                    time_until_start = (plan.scheduled_start_time - now).total_seconds() / 60
                    logger.info(
                        f"  ⏰ 计划 {plan.plan_name} 将在 {time_until_start:.0f} 分钟后执行"
                    )
                    
                    if plan.id in self._notified_plans:
                        logger.debug(f"  ✓ 已发送过通知，跳过: {plan.plan_name}")
                        continue
                    
                    if plan.created_by_id:
                        try:
                            creator = creators_map.get(plan.created_by_id)
                            if creator and creator.email:
                                success = send_curtailment_notification_email(
                                    to_email=creator.email,
                                    plan=plan,
                                    time_until_start=time_until_start,
                                    language='zh'
                                )
                                
                                if success:
                                    self._notified_plans.add(plan.id)
                                    if plan.id in self._notification_failures:
                                        del self._notification_failures[plan.id]
                                    logger.info(
                                        f"  ✅ 已发送通知: {plan.plan_name} → {creator.email} "
                                        f"(将在 {int(time_until_start)} 分钟后执行)"
                                    )
                                else:
                                    self._notification_failures[plan.id] = \
                                        self._notification_failures.get(plan.id, 0) + 1
                                    failure_count = self._notification_failures[plan.id]
                                    
                                    logger.error(
                                        f"  ❌ 邮件发送失败 (第{failure_count}次)，将在下次调度器运行时重试: "
                                        f"{plan.plan_name} → {creator.email}"
                                    )
                                    
                                    if failure_count >= 3:
                                        logger.warning(
                                            f"  ⚠️ 计划 {plan.plan_name} 邮件通知已失败 {failure_count} 次，"
                                            f"请检查SMTP配置或网络连接"
                                        )
                            else:
                                logger.warning(f"  ⚠️ 计划创建者未找到或无邮箱: {plan.plan_name}")
                        except Exception as e:
                            logger.error(f"  ❌ 发送邮件通知异常 {plan.plan_name}: {e}")
                    else:
                        logger.debug(f"  ℹ️ 计划没有创建者信息，跳过邮件通知: {plan.plan_name}")
                    
        except Exception as e:
            logger.error(f"❌ 发送通知任务异常: {e}", exc_info=True)
    
    def start_scheduler(self):
        """
        启动调度器
        
        使用SchedulerLock机制确保只有一个worker实例运行调度器
        """
        if self._is_running:
            logger.info("限电调度器已在运行中")
            return
        
        if not self._app:
            logger.error("Flask应用未设置，无法启动调度器")
            return
        
        if not self._acquire_scheduler_lock():
            logger.info("未获得调度器锁，跳过启动")
            return
        
        try:
            self.scheduler.add_job(
                id='check_pending_plans',
                func=self._check_pending_plans,
                trigger=IntervalTrigger(minutes=1),
                max_instances=1,
                coalesce=True,
                replace_existing=True
            )
            logger.info("✅ 已添加限电计划检查任务: 每1分钟执行一次")
            
            self.scheduler.add_job(
                id='check_recovery_plans',
                func=self._check_recovery_plans,
                trigger=IntervalTrigger(minutes=1),
                max_instances=1,
                coalesce=True,
                replace_existing=True
            )
            logger.info("✅ 已添加矿机恢复检查任务: 每1分钟执行一次")
            
            self.scheduler.add_job(
                id='send_upcoming_notifications',
                func=self._send_upcoming_notifications,
                trigger=IntervalTrigger(minutes=5),
                max_instances=1,
                coalesce=True,
                replace_existing=True
            )
            logger.info("✅ 已添加即将执行通知任务: 每5分钟执行一次")
            
            self.scheduler.add_job(
                id='curtailment_scheduler_heartbeat',
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
                f"🚀 限电调度器启动成功 "
                f"(PID={self.process_id}, Host={self.hostname})"
            )
            
        except Exception as e:
            logger.error(f"启动限电调度器失败: {e}", exc_info=True)
            self._release_scheduler_lock()
    
    def stop(self):
        """确保调度器正确停止"""
        if self.scheduler and self.scheduler.running:
            logger.info("Stopping Curtailment scheduler...")
            try:
                self.scheduler.shutdown(wait=True)
                logger.info("🛑 限电调度器已停止")
            except Exception as e:
                logger.error(f"停止限电调度器失败: {e}")
        
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

curtailment_scheduler = CurtailmentSchedulerService()

def set_flask_app(app):
    """设置Flask应用实例（供外部调用）"""
    curtailment_scheduler.set_flask_app(app)
