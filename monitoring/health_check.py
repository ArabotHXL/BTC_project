#!/usr/bin/env python3
"""
健康检查系统
Health Check System

实现Kubernetes风格的健康检查端点：
- /health/liveness - 存活探针（进程是否运行）
- /health/readiness - 就绪探针（服务是否可接受流量）
- /health/startup - 启动探针（应用是否完成启动）

Kubernetes-style health check endpoints:
- /health/liveness - Liveness probe (is process alive)
- /health/readiness - Readiness probe (can accept traffic)
- /health/startup - Startup probe (finished initialization)
"""

import logging
import time
import os
from typing import Dict, List, Callable
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """健康检查基类"""
    
    def __init__(self, name: str, critical: bool = False):
        """
        Parameters:
        -----------
        name : str
            检查名称
        critical : bool
            是否关键（关键检查失败会导致整体不健康）
        """
        self.name = name
        self.critical = critical
    
    def check(self) -> tuple:
        """
        执行健康检查
        
        Returns:
        --------
        tuple : (is_healthy: bool, message: str, duration_ms: float)
        """
        raise NotImplementedError


class DatabaseHealthCheck(HealthCheck):
    """数据库健康检查"""
    
    def __init__(self, db_engine=None):
        super().__init__("database", critical=True)
        self.db_engine = db_engine
    
    def check(self) -> tuple:
        """检查数据库连接"""
        start_time = time.time()
        
        try:
            if self.db_engine is None:
                # 尝试导入数据库引擎
                try:
                    from db import db
                    self.db_engine = db.engine
                except ImportError:
                    return False, "Database engine not available", 0
            
            # 执行简单查询测试连接
            from sqlalchemy import text
            with self.db_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            duration_ms = (time.time() - start_time) * 1000
            return True, "Database connection OK", duration_ms
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Database health check failed: {e}")
            return False, f"Database connection failed: {str(e)}", duration_ms


class RedisHealthCheck(HealthCheck):
    """Redis健康检查"""
    
    def __init__(self, redis_client=None):
        super().__init__("redis", critical=False)
        self.redis_client = redis_client
    
    def check(self) -> tuple:
        """检查Redis连接"""
        start_time = time.time()
        
        try:
            if self.redis_client is None:
                # 尝试创建Redis客户端
                try:
                    import redis
                    redis_host = os.getenv('REDIS_HOST', 'localhost')
                    redis_port = int(os.getenv('REDIS_PORT', 6379))
                    self.redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        socket_connect_timeout=2
                    )
                except ImportError:
                    return True, "Redis not configured (optional)", 0
            
            # 执行PING测试
            self.redis_client.ping()
            
            duration_ms = (time.time() - start_time) * 1000
            return True, "Redis connection OK", duration_ms
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(f"Redis health check failed: {e}")
            # Redis不是关键服务，失败不影响整体健康
            return True, f"Redis unavailable (degraded): {str(e)}", duration_ms


class DiskSpaceHealthCheck(HealthCheck):
    """磁盘空间健康检查"""
    
    def __init__(self, threshold_percent: int = 90):
        super().__init__("disk_space", critical=False)
        self.threshold_percent = threshold_percent
    
    def check(self) -> tuple:
        """检查磁盘空间"""
        start_time = time.time()
        
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            
            usage_percent = (used / total) * 100
            duration_ms = (time.time() - start_time) * 1000
            
            if usage_percent >= self.threshold_percent:
                return False, f"Disk usage critical: {usage_percent:.1f}%", duration_ms
            else:
                return True, f"Disk usage OK: {usage_percent:.1f}%", duration_ms
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Disk space check failed: {e}")
            return False, f"Disk check failed: {str(e)}", duration_ms


class MemoryHealthCheck(HealthCheck):
    """内存健康检查"""
    
    def __init__(self, threshold_percent: int = 90):
        super().__init__("memory", critical=False)
        self.threshold_percent = threshold_percent
    
    def check(self) -> tuple:
        """检查内存使用"""
        start_time = time.time()
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            duration_ms = (time.time() - start_time) * 1000
            
            if usage_percent >= self.threshold_percent:
                return False, f"Memory usage critical: {usage_percent:.1f}%", duration_ms
            else:
                return True, f"Memory usage OK: {usage_percent:.1f}%", duration_ms
                
        except ImportError:
            return True, "Memory check skipped (psutil not available)", 0
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Memory check failed: {e}")
            return False, f"Memory check failed: {str(e)}", duration_ms


class HealthCheckManager:
    """健康检查管理器"""
    
    def __init__(self):
        """初始化健康检查管理器"""
        self.checks = []
        self.startup_complete = False
        self.startup_time = time.time()
        
        # 注册默认健康检查
        self.register_default_checks()
        
        logger.info("✅ 健康检查管理器已初始化")
    
    def register_default_checks(self):
        """注册默认健康检查"""
        self.add_check(DatabaseHealthCheck())
        self.add_check(RedisHealthCheck())
        self.add_check(DiskSpaceHealthCheck(threshold_percent=90))
        self.add_check(MemoryHealthCheck(threshold_percent=90))
    
    def add_check(self, health_check: HealthCheck):
        """
        添加健康检查
        
        Parameters:
        -----------
        health_check : HealthCheck
            健康检查实例
        """
        self.checks.append(health_check)
        logger.info(f"添加健康检查: {health_check.name} (关键={health_check.critical})")
    
    def mark_startup_complete(self):
        """标记启动完成"""
        self.startup_complete = True
        elapsed = time.time() - self.startup_time
        logger.info(f"✅ 应用启动完成，耗时 {elapsed:.2f}秒")
    
    def liveness_check(self) -> Dict:
        """
        存活探针
        Liveness Probe - 检查进程是否存活
        
        Returns:
        --------
        dict : 健康检查结果
        """
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": {
                "process": {
                    "status": "healthy",
                    "message": "Process is running"
                }
            }
        }
    
    def readiness_check(self) -> Dict:
        """
        就绪探针
        Readiness Probe - 检查服务是否可以接受流量
        
        Returns:
        --------
        dict : 健康检查结果
        """
        start_time = time.time()
        results = {}
        overall_healthy = True
        overall_status = HealthStatus.HEALTHY
        
        # 执行所有健康检查
        for check in self.checks:
            try:
                is_healthy, message, duration_ms = check.check()
                
                results[check.name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "message": message,
                    "duration_ms": round(duration_ms, 2),
                    "critical": check.critical
                }
                
                # 关键检查失败，整体不健康
                if not is_healthy and check.critical:
                    overall_healthy = False
                    overall_status = HealthStatus.UNHEALTHY
                # 非关键检查失败，降级
                elif not is_healthy and not check.critical:
                    if overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                        
            except Exception as e:
                logger.error(f"Health check {check.name} failed with exception: {e}")
                results[check.name] = {
                    "status": "unhealthy",
                    "message": f"Check failed: {str(e)}",
                    "duration_ms": 0,
                    "critical": check.critical
                }
                
                if check.critical:
                    overall_healthy = False
                    overall_status = HealthStatus.UNHEALTHY
        
        total_duration_ms = (time.time() - start_time) * 1000
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_duration_ms": round(total_duration_ms, 2),
            "checks": results
        }
    
    def startup_check(self) -> Dict:
        """
        启动探针
        Startup Probe - 检查应用是否完成启动
        
        Returns:
        --------
        dict : 健康检查结果
        """
        if self.startup_complete:
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": "Application startup complete",
                "startup_duration_seconds": round(time.time() - self.startup_time, 2)
            }
        else:
            elapsed = time.time() - self.startup_time
            return {
                "status": "starting",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": f"Application is starting... ({elapsed:.1f}s elapsed)",
                "startup_duration_seconds": round(elapsed, 2)
            }


# 全局健康检查管理器实例
health_check_manager = HealthCheckManager()


def register_health_endpoints(app):
    """
    注册健康检查端点到Flask应用
    
    Parameters:
    -----------
    app : Flask
        Flask应用实例
    """
    from flask import jsonify
    
    @app.route('/health/liveness')
    def health_liveness():
        """存活探针端点"""
        result = health_check_manager.liveness_check()
        return jsonify(result), 200
    
    @app.route('/health/readiness')
    def health_readiness():
        """就绪探针端点"""
        result = health_check_manager.readiness_check()
        status_code = 200 if result['status'] in ['healthy', 'degraded'] else 503
        return jsonify(result), status_code
    
    @app.route('/health/startup')
    def health_startup():
        """启动探针端点"""
        result = health_check_manager.startup_check()
        status_code = 200 if result['status'] == 'healthy' else 503
        return jsonify(result), status_code
    
    @app.route('/health')
    def health():
        """综合健康检查端点"""
        liveness = health_check_manager.liveness_check()
        readiness = health_check_manager.readiness_check()
        startup = health_check_manager.startup_check()
        
        overall_status = readiness['status']
        status_code = 200 if overall_status in ['healthy', 'degraded'] else 503
        
        return jsonify({
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "liveness": liveness,
            "readiness": readiness,
            "startup": startup
        }), status_code
    
    logger.info("✅ 健康检查端点已注册: /health/liveness, /health/readiness, /health/startup, /health")


if __name__ == '__main__':
    # 测试健康检查
    manager = HealthCheckManager()
    
    print("=== Liveness Check ===")
    print(manager.liveness_check())
    
    print("\n=== Readiness Check ===")
    print(manager.readiness_check())
    
    print("\n=== Startup Check ===")
    print(manager.startup_check())
    
    # 标记启动完成
    time.sleep(1)
    manager.mark_startup_complete()
    
    print("\n=== Startup Check (after complete) ===")
    print(manager.startup_check())
