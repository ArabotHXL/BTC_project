#!/usr/bin/env python3
"""
启动速度优化器
提供三种启动模式：快速、平衡、完整
"""
import os
import sys
import time

def set_optimization_level(level="fast"):
    """
    设置优化级别
    
    Args:
        level: "fast", "balanced", "full"
    """
    
    if level == "fast":
        # 快速启动模式 - 最大优化 (目标: 1-2秒)
        env_vars = {
            "FAST_STARTUP": "1",
            "SKIP_DATABASE_HEALTH_CHECK": "1",
            "PYTHONOPTIMIZE": "1", 
            "ENABLE_BACKGROUND_SERVICES": "0",
            "LOAD_CORE_MODULES": "1",
            "LOAD_ADVANCED_MODULES": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "FLASK_ENV": "production"
        }
        print("🚀 快速启动模式 - 预期启动时间: 1-2秒")
        
    elif level == "balanced":
        # 平衡模式 - 适中优化 (目标: 3-5秒)
        env_vars = {
            "FAST_STARTUP": "1",
            "SKIP_DATABASE_HEALTH_CHECK": "0",
            "PYTHONOPTIMIZE": "1",
            "ENABLE_BACKGROUND_SERVICES": "1", 
            "LOAD_CORE_MODULES": "1",
            "LOAD_ADVANCED_MODULES": "1",
            "PYTHONDONTWRITEBYTECODE": "1"
        }
        print("⚖️ 平衡启动模式 - 预期启动时间: 3-5秒")
        
    else:  # full
        # 完整模式 - 无优化 (目标: 10-15秒)
        env_vars = {
            "FAST_STARTUP": "0",
            "SKIP_DATABASE_HEALTH_CHECK": "0", 
            "PYTHONOPTIMIZE": "0",
            "ENABLE_BACKGROUND_SERVICES": "1",
            "LOAD_CORE_MODULES": "1",
            "LOAD_ADVANCED_MODULES": "1",
            "PYTHONDONTWRITEBYTECODE": "0"
        }
        print("🔧 完整启动模式 - 预期启动时间: 10-15秒")
    
    # 应用环境变量
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"  设置 {key}={value}")
    
    return env_vars

def benchmark_startup():
    """测试启动速度"""
    print("\n" + "="*50)
    print("启动速度基准测试")
    print("="*50)
    
    # 测试三种模式
    modes = ["fast", "balanced", "full"]
    results = {}
    
    for mode in modes:
        print(f"\n测试 {mode.upper()} 模式:")
        set_optimization_level(mode)
        
        start_time = time.time()
        
        # 重新导入以应用新的环境变量
        if 'main' in sys.modules:
            del sys.modules['main']
        if 'app' in sys.modules:
            del sys.modules['app']
            
        try:
            from main import app
            end_time = time.time()
            duration = end_time - start_time
            results[mode] = duration
            print(f"✅ {mode.capitalize()} 模式启动时间: {duration:.2f}秒")
        except Exception as e:
            print(f"❌ {mode.capitalize()} 模式启动失败: {e}")
            results[mode] = None
    
    # 显示结果对比
    print("\n" + "="*50)
    print("启动速度对比结果")
    print("="*50)
    
    for mode, duration in results.items():
        if duration:
            improvement = ""
            if mode == "fast" and results.get("full"):
                saved = results["full"] - duration
                improvement = f" (节省 {saved:.1f}秒)"
            print(f"{mode.capitalize():8}: {duration:.2f}秒{improvement}")
    
    return results

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode in ["fast", "balanced", "full"]:
            set_optimization_level(mode)
            print(f"\n环境变量已设置为 {mode.upper()} 模式")
        elif mode == "benchmark":
            benchmark_startup()
        else:
            print("用法: python startup_optimizer.py [fast|balanced|full|benchmark]")
    else:
        # 默认快速模式
        set_optimization_level("fast")
        print("\n默认使用快速启动模式")