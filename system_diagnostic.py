#!/usr/bin/env python3
"""
系统诊断工具
System Diagnostic Tool

统一的系统健康检查和状态监控工具
Unified system health check and status monitoring tool
"""

import requests
import psycopg2
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any

class SystemDiagnostic:
    """系统诊断器"""
    
    def __init__(self):
        self.base_url = "http://0.0.0.0:5000"
        self.db_url = os.environ.get('DATABASE_URL')
        self.session = requests.Session()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "status": "unknown",
            "components": {},
            "alerts": [],
            "recommendations": []
        }
    
    def check_server_health(self) -> Dict:
        """检查服务器健康状态"""
        try:
            start_time = time.time()
            response = self.session.get(self.base_url, timeout=10)
            response_time = time.time() - start_time
            
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": round(response_time, 3),
                "status_code": response.status_code,
                "content_length": len(response.text)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def check_database_health(self) -> Dict:
        """检查数据库健康状态"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # 检查连接
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            # 检查关键表
            tables = ['market_analytics', 'network_snapshots', 'user_access', 'login_records']
            table_status = {}
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_status[table] = {"count": count, "status": "ok"}
                except Exception as e:
                    table_status[table] = {"status": "error", "error": str(e)}
            
            cursor.close()
            conn.close()
            
            return {
                "status": "healthy",
                "version": version.split()[0],
                "tables": table_status
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def check_api_endpoints(self) -> Dict:
        """检查API端点健康状态"""
        endpoints = [
            ("/api/btc-price", "BTC价格"),
            ("/api/network-stats", "网络统计"),
            ("/api/miners", "矿机数据"),
            ("/api/sha256-comparison", "挖矿对比")
        ]
        
        api_status = {}
        
        for endpoint, name in endpoints:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        success = data.get('success', False)
                        status = "healthy" if success else "warning"
                    except:
                        status = "warning"
                else:
                    status = "unhealthy"
                
                api_status[endpoint] = {
                    "name": name,
                    "status": status,
                    "response_time": round(response_time, 3),
                    "status_code": response.status_code
                }
            except Exception as e:
                api_status[endpoint] = {
                    "name": name,
                    "status": "error",
                    "error": str(e)
                }
        
        return api_status
    
    def check_analytics_system(self) -> Dict:
        """检查分析系统状态"""
        try:
            # 检查分析数据API
            response = self.session.get(f"{self.base_url}/api/analytics/market-data", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    market_data = data.get('data', {})
                    return {
                        "status": "healthy",
                        "latest_price": market_data.get('btc_price'),
                        "latest_hashrate": market_data.get('network_hashrate'),
                        "last_update": market_data.get('timestamp')
                    }
            
            return {
                "status": "warning",
                "message": "分析系统可访问但数据异常"
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e)
            }
    
    def check_external_apis(self) -> Dict:
        """检查外部API连接状态"""
        external_apis = {
            "CoinGecko": "https://api.coingecko.com/api/v3/ping",
            "Blockchain.info": "https://blockchain.info/q/getblockcount",
            "Minerstat": "https://api.minerstat.com/v2/coins?list=BTC"
        }
        
        api_status = {}
        
        for name, url in external_apis.items():
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                response_time = time.time() - start_time
                
                api_status[name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": round(response_time, 3),
                    "status_code": response.status_code
                }
            except Exception as e:
                api_status[name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return api_status
    
    def run_diagnostic(self) -> Dict:
        """运行完整系统诊断"""
        print("🔍 开始系统诊断...")
        
        # 服务器健康检查
        print("  检查服务器状态...")
        self.results["components"]["server"] = self.check_server_health()
        
        # 数据库健康检查
        print("  检查数据库状态...")
        self.results["components"]["database"] = self.check_database_health()
        
        # API端点检查
        print("  检查API端点...")
        self.results["components"]["apis"] = self.check_api_endpoints()
        
        # 分析系统检查
        print("  检查分析系统...")
        self.results["components"]["analytics"] = self.check_analytics_system()
        
        # 外部API检查
        print("  检查外部API...")
        self.results["components"]["external_apis"] = self.check_external_apis()
        
        # 生成总体状态和建议
        self._analyze_results()
        
        return self.results
    
    def _analyze_results(self):
        """分析结果并生成状态和建议"""
        components = self.results["components"]
        
        # 计算健康组件数量
        healthy_count = 0
        total_count = 0
        critical_issues = []
        warnings = []
        
        # 服务器状态
        if components["server"]["status"] == "healthy":
            healthy_count += 1
        elif components["server"]["status"] == "error":
            critical_issues.append("服务器无法访问")
        total_count += 1
        
        # 数据库状态
        if components["database"]["status"] == "healthy":
            healthy_count += 1
        elif components["database"]["status"] == "error":
            critical_issues.append("数据库连接失败")
        total_count += 1
        
        # API状态
        api_healthy = 0
        api_total = len(components["apis"])
        for api, status in components["apis"].items():
            if status["status"] == "healthy":
                api_healthy += 1
            elif status["status"] == "error":
                warnings.append(f"API {status['name']} 不可用")
        
        if api_healthy >= api_total * 0.75:  # 75%以上API正常
            healthy_count += 1
        total_count += 1
        
        # 分析系统状态
        if components["analytics"]["status"] == "healthy":
            healthy_count += 1
        elif components["analytics"]["status"] == "error":
            warnings.append("分析系统异常")
        total_count += 1
        
        # 外部API状态
        external_healthy = 0
        external_total = len(components["external_apis"])
        for api, status in components["external_apis"].items():
            if status["status"] == "healthy":
                external_healthy += 1
        
        if external_healthy >= external_total * 0.5:  # 50%以上外部API正常
            healthy_count += 1
        total_count += 1
        
        # 确定总体状态
        health_ratio = healthy_count / total_count
        
        if health_ratio >= 0.9 and not critical_issues:
            self.results["status"] = "healthy"
        elif health_ratio >= 0.7 and not critical_issues:
            self.results["status"] = "warning"
        else:
            self.results["status"] = "critical"
        
        # 添加告警和建议
        self.results["alerts"] = critical_issues + warnings
        
        if self.results["status"] == "healthy":
            self.results["recommendations"] = ["系统运行正常，继续监控"]
        elif self.results["status"] == "warning":
            self.results["recommendations"] = [
                "检查警告项目并尽快修复",
                "监控系统性能",
                "确保外部API连接稳定"
            ]
        else:
            self.results["recommendations"] = [
                "立即检查关键系统组件",
                "修复数据库和服务器连接问题",
                "联系技术支持"
            ]
    
    def generate_report(self) -> str:
        """生成诊断报告"""
        status_emoji = {
            "healthy": "🟢",
            "warning": "🟡", 
            "critical": "🔴",
            "error": "❌"
        }
        
        report = []
        report.append("=" * 80)
        report.append("系统诊断报告")
        report.append("=" * 80)
        report.append(f"检查时间: {self.results['timestamp']}")
        report.append(f"总体状态: {status_emoji.get(self.results['status'], '❓')} {self.results['status'].upper()}")
        report.append("")
        
        # 组件状态
        report.append("📊 组件状态:")
        
        # 服务器
        server = self.results["components"]["server"]
        report.append(f"  {status_emoji.get(server['status'], '❓')} 服务器: {server.get('response_time', 'N/A')}s")
        
        # 数据库
        db = self.results["components"]["database"]
        report.append(f"  {status_emoji.get(db['status'], '❓')} 数据库: {db.get('version', 'N/A')}")
        
        # API端点
        apis = self.results["components"]["apis"]
        healthy_apis = sum(1 for api in apis.values() if api["status"] == "healthy")
        report.append(f"  {status_emoji.get('healthy' if healthy_apis >= len(apis) * 0.75 else 'warning', '❓')} API端点: {healthy_apis}/{len(apis)} 正常")
        
        # 分析系统
        analytics = self.results["components"]["analytics"]
        report.append(f"  {status_emoji.get(analytics['status'], '❓')} 分析系统: {analytics.get('latest_price', 'N/A')}")
        
        # 外部API
        external = self.results["components"]["external_apis"]
        healthy_external = sum(1 for api in external.values() if api["status"] == "healthy")
        report.append(f"  {status_emoji.get('healthy' if healthy_external >= len(external) * 0.5 else 'warning', '❓')} 外部API: {healthy_external}/{len(external)} 可用")
        
        # 告警
        if self.results["alerts"]:
            report.append("")
            report.append("⚠️  告警:")
            for alert in self.results["alerts"]:
                report.append(f"  - {alert}")
        
        # 建议
        if self.results["recommendations"]:
            report.append("")
            report.append("💡 建议:")
            for rec in self.results["recommendations"]:
                report.append(f"  - {rec}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)

def main():
    """主函数"""
    diagnostic = SystemDiagnostic()
    results = diagnostic.run_diagnostic()
    
    # 显示报告
    print(diagnostic.generate_report())
    
    # 保存详细结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"system_diagnostic_report_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"详细报告已保存至: {filename}")

if __name__ == "__main__":
    main()