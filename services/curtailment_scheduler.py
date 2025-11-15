import logging
import os
import socket
import atexit
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger

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
        4. 更新计划状态
        """
        if not self._app:
            logger.error("Flask应用未设置，无法检查计划")
            return
        
        try:
            with self._app.app_context():
                from models import CurtailmentPlan, PlanStatus, ExecutionMode, db
                from intelligence.curtailment_engine import CurtailmentEngine
                
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
                        logger.info(f"⚡ 开始执行限电计划: {plan.plan_name} (ID={plan.id})")
                        
                        if plan.execution_mode == ExecutionMode.AUTO:
                            self._execute_plan_auto(plan)
                        elif plan.execution_mode == ExecutionMode.SEMI_AUTO:
                            if plan.status == PlanStatus.APPROVED:
                                self._execute_plan_auto(plan)
                            else:
                                logger.info(f"⏸️ 半自动计划需要审批: {plan.plan_name}")
                        else:
                            logger.info(f"✋ 手动计划不自动执行: {plan.plan_name}")
                            plan.status = PlanStatus.PENDING
                            db.session.commit()
                    
                    except Exception as e:
                        logger.error(f"❌ 执行计划失败 {plan.plan_name}: {e}", exc_info=True)
                        
        except Exception as e:
            logger.error(f"❌ 检查待执行计划任务异常: {e}", exc_info=True)
    
    def _execute_plan_auto(self, plan):
        """
        自动执行限电计划
        
        Args:
            plan: CurtailmentPlan实例
        """
        from models import db, PlanStatus, HostingMiner, MinerStatus, CurtailmentExecution, ExecutionAction, ExecutionStatus
        from intelligence.curtailment_engine import CurtailmentEngine
        
        try:
            plan.status = PlanStatus.EXECUTING
            db.session.commit()
            
            engine = CurtailmentEngine(site_id=plan.site_id)
            
            if not plan.strategy_id:
                logger.error(f"计划 {plan.plan_name} 没有选择策略，跳过执行")
                plan.status = PlanStatus.PENDING
                db.session.commit()
                return
            
            result = engine.calculate_curtailment_plan(
                strategy_id=plan.strategy_id,
                target_reduction_kw=float(plan.target_power_reduction_kw)
            )
            
            if not result or not result.get('selected_miners'):
                logger.warning(f"计划 {plan.plan_name} 没有选中任何矿机")
                plan.status = PlanStatus.COMPLETED
                db.session.commit()
                return
            
            selected_miner_ids = result['selected_miners']
            miners_to_shutdown = HostingMiner.query.filter(  # type: ignore
                HostingMiner.id.in_(selected_miner_ids),  # type: ignore
                HostingMiner.status == MinerStatus.ACTIVE  # type: ignore
            ).all()
            
            logger.info(f"🔌 准备关闭 {len(miners_to_shutdown)} 台矿机")
            
            success_count = 0
            failed_count = 0
            
            for miner in miners_to_shutdown:
                try:
                    miner.status = MinerStatus.CURTAILED
                    
                    power_saved_kw = (miner.actual_power_consumption or 
                                     miner.miner_model.reference_power_consumption) / 1000.0
                    
                    execution = CurtailmentExecution(
                        plan_id=plan.id,
                        miner_id=miner.id,
                        execution_action=ExecutionAction.SHUTDOWN,
                        execution_status=ExecutionStatus.SUCCESS,
                        power_saved_kw=power_saved_kw
                    )
                    db.session.add(execution)
                    
                    success_count += 1
                    logger.debug(f"  ✅ 矿机 {miner.miner_name} 已关闭")
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"  ❌ 矿机 {miner.miner_name} 关闭失败: {e}")
                    
                    execution = CurtailmentExecution(
                        plan_id=plan.id,
                        miner_id=miner.id,
                        execution_action=ExecutionAction.SHUTDOWN,
                        execution_status=ExecutionStatus.FAILED,
                        error_message=str(e)
                    )
                    db.session.add(execution)
            
            plan.calculated_power_reduction_kw = result.get('actual_power_saved_kw', 0)
            # 保持EXECUTING状态，等待手动恢复或自动恢复（如果有scheduled_end_time）
            db.session.commit()
            
            logger.info(
                f"✅ 计划执行完成: {plan.plan_name} | "
                f"成功={success_count}, 失败={failed_count}, "
                f"节省功率={result.get('actual_power_saved_kw', 0)} kW"
            )
            
            if plan.scheduled_end_time:
                logger.info(f"   等待自动恢复，结束时间={plan.scheduled_end_time}")
            else:
                logger.info(f"   需要手动恢复（POST /api/curtailment/schedules/{plan.id}/recover）")
            
        except Exception as e:
            logger.error(f"自动执行计划失败: {e}", exc_info=True)
            plan.status = PlanStatus.PENDING
            db.session.commit()
    
    def _check_recovery_plans(self):
        """
        定时任务：检查需要恢复的限电计划
        
        检查逻辑：
        1. 找到状态为EXECUTING且已过结束时间的计划
        2. 恢复被限电的矿机
        3. 更新计划状态为COMPLETED
        """
        if not self._app:
            logger.error("Flask应用未设置，无法检查恢复")
            return
        
        try:
            with self._app.app_context():
                from models import CurtailmentPlan, PlanStatus, HostingMiner, MinerStatus, CurtailmentExecution, ExecutionAction, ExecutionStatus, db
                
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
                        logger.info(f"🔌 开始恢复计划: {plan.plan_name} (ID={plan.id})")
                        
                        curtailed_miners = HostingMiner.query.join(  # type: ignore
                            CurtailmentExecution,
                            HostingMiner.id == CurtailmentExecution.miner_id  # type: ignore
                        ).filter(
                            CurtailmentExecution.plan_id == plan.id,  # type: ignore
                            CurtailmentExecution.execution_action == ExecutionAction.SHUTDOWN,  # type: ignore
                            CurtailmentExecution.execution_status == ExecutionStatus.SUCCESS,  # type: ignore
                            HostingMiner.status == MinerStatus.CURTAILED  # type: ignore
                        ).all()
                        
                        logger.info(f"  找到 {len(curtailed_miners)} 台需要恢复的矿机")
                        
                        success_count = 0
                        failed_count = 0
                        
                        for miner in curtailed_miners:
                            try:
                                miner.status = MinerStatus.ACTIVE
                                
                                execution = CurtailmentExecution(
                                    plan_id=plan.id,
                                    miner_id=miner.id,
                                    execution_action=ExecutionAction.STARTUP,
                                    execution_status=ExecutionStatus.SUCCESS
                                )
                                db.session.add(execution)
                                
                                success_count += 1
                                logger.debug(f"    ✅ 矿机 {miner.miner_name} 已恢复")
                                
                            except Exception as e:
                                failed_count += 1
                                logger.error(f"    ❌ 矿机 {miner.miner_name} 恢复失败: {e}")
                                
                                execution = CurtailmentExecution(
                                    plan_id=plan.id,
                                    miner_id=miner.id,
                                    execution_action=ExecutionAction.STARTUP,
                                    execution_status=ExecutionStatus.FAILED,
                                    error_message=str(e)
                                )
                                db.session.add(execution)
                        
                        plan.status = PlanStatus.COMPLETED
                        db.session.commit()
                        
                        logger.info(
                            f"✅ 计划恢复完成: {plan.plan_name} | "
                            f"成功={success_count}, 失败={failed_count}"
                        )
                        
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
        3. 发送提醒通知（Toast + 可选邮件）
        """
        if not self._app:
            logger.error("Flask应用未设置，无法发送通知")
            return
        
        try:
            with self._app.app_context():
                from models import CurtailmentPlan, PlanStatus, db
                
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
                
                for plan in upcoming_plans:
                    time_until_start = (plan.scheduled_start_time - now).total_seconds() / 60
                    logger.info(
                        f"  ⏰ 计划 {plan.plan_name} 将在 {time_until_start:.0f} 分钟后执行"
                    )
                    
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
