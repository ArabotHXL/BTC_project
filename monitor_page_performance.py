
#!/usr/bin/env python3
"""
实时页面性能监控工具
"""

import time
import requests
from datetime import datetime
import json
from performance_monitor import monitor

def monitor_page_performance(pages_to_monitor, duration_minutes=10):
    """实时监控页面性能"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    print(f"🔄 开始实时监控页面性能 ({duration_minutes}分钟)")
    print("=" * 50)
    
    end_time = time.time() + (duration_minutes * 60)
    
    while time.time() < end_time:
        for path, name in pages_to_monitor:
            try:
                start = time.time()
                response = session.get(f"{base_url}{path}", timeout=5)
                duration = time.time() - start
                
                # 记录到性能监控器
                monitor.track_request(path, duration, response.status_code)
                
                status = "✅" if response.status_code == 200 else "❌"
                print(f"{datetime.now().strftime('%H:%M:%S')} {status} {name}: {duration*1000:.0f}ms")
                
            except Exception as e:
                print(f"{datetime.now().strftime('%H:%M:%S')} ❌ {name}: 错误 - {str(e)}")
                monitor.track_error("PageLoadError", str(e))
        
        print("-" * 30)
        time.sleep(30)  # 每30秒检查一次
    
    # 生成监控报告
    summary = monitor.get_performance_summary()
    print("\n📊 监控期间性能统计:")
    print(f"请求总数: {summary['requests_per_hour']}")
    print(f"平均响应时间: {summary['avg_request_time_ms']:.1f}ms")
    print(f"错误数: {summary['errors_per_hour']}")
    
    return summary

if __name__ == "__main__":
    # 要监控的关键页面
    critical_pages = [
        ('/', '首页'),
        ('/calculator', '计算器'),
        ('/api/network-stats', '网络API'),
        ('/api/get-btc-price', '价格API')
    ]
    
    monitor_page_performance(critical_pages, 5)
