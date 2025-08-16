
#!/usr/bin/env python3
"""
页面加载速度测试工具
测试每个页面的响应时间和性能指标
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, List
import concurrent.futures
import statistics

class PageLoadingSpeedTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def test_page_speed(self, path: str, page_name: str, repeat: int = 3) -> Dict:
        """测试单个页面的加载速度"""
        print(f"🔍 测试页面: {page_name} ({path})")
        
        times = []
        status_codes = []
        content_sizes = []
        
        for i in range(repeat):
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{path}", timeout=15)
                end_time = time.time()
                
                load_time = (end_time - start_time) * 1000  # 转换为毫秒
                times.append(load_time)
                status_codes.append(response.status_code)
                content_sizes.append(len(response.content))
                
                print(f"  第{i+1}次: {load_time:.0f}ms (状态码: {response.status_code})")
                
            except Exception as e:
                print(f"  第{i+1}次: 错误 - {str(e)}")
                times.append(999999)  # 错误情况下记录极大值
                status_codes.append(0)
                content_sizes.append(0)
        
        # 计算统计数据
        valid_times = [t for t in times if t < 999999]
        if valid_times:
            avg_time = statistics.mean(valid_times)
            min_time = min(valid_times)
            max_time = max(valid_times)
        else:
            avg_time = min_time = max_time = 999999
            
        # 性能评级
        if avg_time < 200:
            grade = "优秀 ⭐⭐⭐"
        elif avg_time < 500:
            grade = "良好 ⭐⭐"
        elif avg_time < 1000:
            grade = "一般 ⭐"
        else:
            grade = "需要优化 ❌"
        
        result = {
            'path': path,
            'page_name': page_name,
            'avg_time_ms': round(avg_time, 1),
            'min_time_ms': round(min_time, 1),
            'max_time_ms': round(max_time, 1),
            'avg_content_size_kb': round(statistics.mean(content_sizes) / 1024, 1) if content_sizes else 0,
            'success_rate': len(valid_times) / repeat * 100,
            'status_codes': status_codes,
            'grade': grade,
            'timestamp': datetime.now().isoformat()
        }
        
        self.results.append(result)
        return result
    
    def test_all_pages(self) -> List[Dict]:
        """测试所有主要页面"""
        pages_to_test = [
            ('/', '首页'),
            ('/calculator', '挖矿计算器'),
            ('/login', '登录页'),
            ('/price', '价格页面'),
            ('/analytics', '数据分析'),
            ('/curtailment_calculator', '电力削减计算器'),
            ('/network_history', '网络历史'),
            ('/crm/dashboard', 'CRM仪表盘'),
            ('/admin/user_access', '用户管理'),
            ('/deribit-analysis', 'Deribit分析'),
            ('/batch-calculator', '批量计算器'),
        ]
        
        print("🚀 开始页面加载速度测试...\n")
        
        # 并发测试以获得更真实的性能数据
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_page = {
                executor.submit(self.test_page_speed, path, name): (path, name)
                for path, name in pages_to_test
            }
            
            for future in concurrent.futures.as_completed(future_to_page):
                path, name = future_to_page[future]
                try:
                    result = future.result()
                except Exception as e:
                    print(f"❌ 页面 {name} ({path}) 测试失败: {str(e)}")
        
        return self.results
    
    def generate_report(self) -> Dict:
        """生成性能报告"""
        if not self.results:
            return {"error": "没有测试数据"}
        
        # 计算总体统计
        all_times = [r['avg_time_ms'] for r in self.results if r['avg_time_ms'] < 999999]
        
        report = {
            'summary': {
                'total_pages_tested': len(self.results),
                'successful_pages': len(all_times),
                'overall_avg_time_ms': round(statistics.mean(all_times), 1) if all_times else 0,
                'fastest_page_ms': min(all_times) if all_times else 0,
                'slowest_page_ms': max(all_times) if all_times else 0,
                'test_timestamp': datetime.now().isoformat()
            },
            'page_results': sorted(self.results, key=lambda x: x['avg_time_ms']),
            'recommendations': self.get_optimization_recommendations()
        }
        
        return report
    
    def get_optimization_recommendations(self) -> List[str]:
        """基于测试结果提供优化建议"""
        recommendations = []
        
        slow_pages = [r for r in self.results if r['avg_time_ms'] > 1000]
        if slow_pages:
            recommendations.append(f"有 {len(slow_pages)} 个页面加载时间超过1秒，需要优化")
        
        large_pages = [r for r in self.results if r['avg_content_size_kb'] > 500]
        if large_pages:
            recommendations.append(f"有 {len(large_pages)} 个页面内容超过500KB，考虑压缩或延迟加载")
        
        failed_pages = [r for r in self.results if r['success_rate'] < 100]
        if failed_pages:
            recommendations.append(f"有 {len(failed_pages)} 个页面存在加载失败，检查错误处理")
        
        if not recommendations:
            recommendations.append("所有页面性能表现良好！")
        
        recommendations.extend([
            "启用Gzip压缩减少传输大小",
            "使用CDN加速静态资源",
            "优化数据库查询",
            "实施更积极的缓存策略"
        ])
        
        return recommendations
    
    def print_results(self):
        """打印测试结果"""
        print("\n" + "="*70)
        print("📊 页面加载速度测试报告")
        print("="*70)
        
        # 按加载时间排序
        sorted_results = sorted(self.results, key=lambda x: x['avg_time_ms'])
        
        print(f"{'页面名称':<20} {'路径':<25} {'平均时间':<10} {'评级':<15}")
        print("-" * 70)
        
        for result in sorted_results:
            print(f"{result['page_name']:<20} {result['path']:<25} {result['avg_time_ms']:<10.1f}ms {result['grade']:<15}")
        
        # 生成报告
        report = self.generate_report()
        print(f"\n📈 总体统计:")
        print(f"  测试页面数: {report['summary']['total_pages_tested']}")
        print(f"  成功页面数: {report['summary']['successful_pages']}")
        print(f"  平均加载时间: {report['summary']['overall_avg_time_ms']:.1f}ms")
        print(f"  最快页面: {report['summary']['fastest_page_ms']:.1f}ms")
        print(f"  最慢页面: {report['summary']['slowest_page_ms']:.1f}ms")
        
        print(f"\n💡 优化建议:")
        for i, rec in enumerate(report['recommendations'][:5], 1):
            print(f"  {i}. {rec}")
        
        return report

def main():
    """主函数"""
    tester = PageLoadingSpeedTester()
    
    # 测试所有页面
    results = tester.test_all_pages()
    
    # 打印结果
    report = tester.print_results()
    
    # 保存报告到文件
    filename = f"page_loading_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存到: {filename}")

if __name__ == "__main__":
    main()
