#!/usr/bin/env python3
"""
Comprehensive 99% Accuracy Test Suite for BTC Mining Calculator
测试所有核心功能，包括API端点、数据库连接、计算准确性等
"""
import sys
import os
import json
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ComprehensiveTestSuite:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.start_time = datetime.now()
        
    def log_test_result(self, test_name: str, success: bool, details: str = "", execution_time: float = 0):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'success': success,
            'details': details,
            'execution_time': round(execution_time, 3),
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name} ({execution_time:.3f}s) - {details}")
        
    def run_test_with_timer(self, test_func, test_name: str):
        """运行测试并计时"""
        start_time = time.time()
        try:
            success, details = test_func()
            execution_time = time.time() - start_time
            self.log_test_result(test_name, success, details, execution_time)
        except Exception as e:
            execution_time = time.time() - start_time
            self.log_test_result(test_name, False, f"异常: {str(e)}", execution_time)

    def test_server_health(self) -> Tuple[bool, str]:
        """测试服务器健康状态"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    return True, f"服务器健康 - 数据库状态: {data.get('database')}"
            return False, f"健康检查失败: {response.status_code}"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    def test_database_connection(self) -> Tuple[bool, str]:
        """测试数据库连接"""
        try:
            from app import app
            from models import db
            from sqlalchemy import text
            
            with app.app_context():
                # 测试基本连接
                result = db.session.execute(text('SELECT 1')).fetchone()
                if result and result[0] == 1:
                    
                    # 检查关键表是否存在
                    tables = ['user_access', 'technical_indicators', 'market_analytics', 'plans', 'subscriptions']
                    missing_tables = []
                    
                    for table in tables:
                        try:
                            count = db.session.execute(text(f'SELECT COUNT(*) FROM {table}')).fetchone()[0]
                            logger.info(f"表 {table}: {count} 条记录")
                        except Exception as e:
                            missing_tables.append(table)
                    
                    if missing_tables:
                        return False, f"缺失表: {', '.join(missing_tables)}"
                    
                    return True, f"数据库连接正常，{len(tables)}个核心表已验证"
                return False, "基本查询失败"
        except Exception as e:
            return False, f"数据库连接错误: {str(e)}"

    def test_subscription_models(self) -> Tuple[bool, str]:
        """测试订阅模型和数据结构"""
        try:
            from app import app
            from models_subscription import Plan, Subscription
            from models import db
            
            with app.app_context():
                # 检查Plan模型
                plans = Plan.query.all()
                plan_count = len(plans)
                
                # 检查Subscription模型
                subscriptions = Subscription.query.all()
                sub_count = len(subscriptions)
                
                # 验证模型字段
                if plans:
                    plan = plans[0]
                    required_fields = ['id', 'name', 'price', 'max_miners', 'allow_api', 'allow_scenarios']
                    missing_fields = [field for field in required_fields if not hasattr(plan, field)]
                    if missing_fields:
                        return False, f"Plan模型缺失字段: {missing_fields}"
                
                return True, f"订阅模型正常 - Plans: {plan_count}, Subscriptions: {sub_count}"
                
        except Exception as e:
            return False, f"订阅模型测试失败: {str(e)}"

    def test_technical_indicators_api(self) -> Tuple[bool, str]:
        """测试技术指标API端点"""
        try:
            # 首先尝试直接数据库查询
            from app import app
            from models import db
            import psycopg2
            
            with app.app_context():
                conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM technical_indicators")
                count = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                
                if count == 0:
                    return False, f"技术指标表为空 (0条记录)"
                
                # 测试API端点响应格式
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT recorded_at, rsi_14, sma_20, sma_50, ema_12, ema_26, 
                           macd, bollinger_upper, bollinger_lower, volatility_30d
                    FROM technical_indicators 
                    ORDER BY recorded_at DESC LIMIT 1
                """)
                data = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if data:
                    # 验证数据完整性
                    non_null_fields = sum(1 for field in data[1:] if field is not None)
                    total_fields = len(data) - 1  # 减去时间戳字段
                    
                    completeness = (non_null_fields / total_fields) * 100
                    
                    return True, f"技术指标数据正常 - 记录数: {count}, 数据完整性: {completeness:.1f}%"
                else:
                    return False, "无法获取技术指标数据"
                    
        except Exception as e:
            return False, f"技术指标API测试失败: {str(e)}"

    def test_mining_calculations(self) -> Tuple[bool, str]:
        """测试挖矿计算准确性"""
        try:
            from mining_calculator import MINER_DATA, calculate_mining_profitability
            
            # 使用标准参数测试计算
            test_cases = [
                {
                    'miner': 'Antminer S21 Pro',
                    'power_cost': 0.12,
                    'btc_price': 50000,
                    'expected_range': (10, 50)  # 预期日收益范围 (USD)
                },
                {
                    'miner': 'Antminer S19 XP',
                    'power_cost': 0.08,
                    'btc_price': 60000,
                    'expected_range': (15, 60)
                }
            ]
            
            passed_tests = 0
            total_tests = len(test_cases)
            
            for i, case in enumerate(test_cases):
                if case['miner'] not in MINER_DATA:
                    continue
                    
                result = calculate_mining_profitability(
                    miner_model=case['miner'],
                    site_power_mw=10.0,
                    miner_count=1000,
                    electricity_cost=case['power_cost'],
                    btc_price=case['btc_price']
                )
                
                if result and 'daily_profit' in result:
                    daily_profit = result['daily_profit']
                    min_expected, max_expected = case['expected_range']
                    
                    if min_expected <= daily_profit <= max_expected:
                        passed_tests += 1
                        logger.info(f"计算测试 {i+1}: 日收益 ${daily_profit:.2f} ✅")
                    else:
                        logger.warning(f"计算测试 {i+1}: 日收益 ${daily_profit:.2f} 超出预期范围")
            
            accuracy = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            return accuracy >= 80, f"计算准确率: {accuracy:.1f}% ({passed_tests}/{total_tests})"
            
        except Exception as e:
            return False, f"挖矿计算测试失败: {str(e)}"

    def test_real_time_data_integration(self) -> Tuple[bool, str]:
        """测试实时数据集成"""
        try:
            from mining_calculator import get_real_time_btc_price, get_real_time_difficulty, get_real_time_btc_hashrate
            
            # 测试价格数据
            price = get_real_time_btc_price()
            if not price or price <= 0:
                return False, f"价格数据无效: {price}"
            
            # 测试难度数据
            difficulty = get_real_time_difficulty()
            if not difficulty or difficulty <= 0:
                return False, f"难度数据无效: {difficulty}"
                
            # 测试算力数据
            hashrate = get_real_time_btc_hashrate()
            if not hashrate or hashrate <= 0:
                return False, f"算力数据无效: {hashrate}"
            
            # 验证数据合理性
            reasonable_ranges = {
                'price': (20000, 200000),
                'difficulty': (1e12, 1e16),
                'hashrate': (100, 2000)  # EH/s
            }
            
            issues = []
            if not (reasonable_ranges['price'][0] <= price <= reasonable_ranges['price'][1]):
                issues.append(f"价格超出合理范围: ${price:,.2f}")
                
            if not (reasonable_ranges['difficulty'][0] <= difficulty <= reasonable_ranges['difficulty'][1]):
                issues.append(f"难度超出合理范围: {difficulty:.2e}")
                
            if not (reasonable_ranges['hashrate'][0] <= hashrate <= reasonable_ranges['hashrate'][1]):
                issues.append(f"算力超出合理范围: {hashrate:.2f} EH/s")
            
            if issues:
                return False, f"数据异常: {'; '.join(issues)}"
            
            return True, f"实时数据正常 - 价格: ${price:,.0f}, 难度: {difficulty:.2e}, 算力: {hashrate:.1f} EH/s"
            
        except Exception as e:
            return False, f"实时数据测试失败: {str(e)}"

    def test_authentication_system(self) -> Tuple[bool, str]:
        """测试认证系统"""
        try:
            from app import app
            from models import UserAccess, db
            
            with app.app_context():
                # 检查用户表
                users = UserAccess.query.all()
                user_count = len(users)
                
                if user_count == 0:
                    return False, "无用户数据"
                
                # 检查权限分配
                role_distribution = {}
                for user in users:
                    role = user.role or 'unknown'
                    role_distribution[role] = role_distribution.get(role, 0) + 1
                
                # 验证至少有一个管理员
                if 'owner' not in role_distribution:
                    return False, "无管理员用户"
                
                return True, f"认证系统正常 - 用户: {user_count}, 角色分布: {role_distribution}"
                
        except Exception as e:
            return False, f"认证系统测试失败: {str(e)}"

    def test_api_endpoints(self) -> Tuple[bool, str]:
        """测试关键API端点"""
        try:
            endpoints_to_test = [
                ('/health', 200),
                ('/api/health', 200),
                ('/status', 200),
                ('/api/analytics/data', 200),  # 需要认证但应该有合理的错误响应
            ]
            
            results = []
            for endpoint, expected_status in endpoints_to_test:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                    actual_status = response.status_code
                    
                    if endpoint in ['/health', '/api/health', '/status']:
                        # 这些端点应该直接成功
                        if actual_status == expected_status:
                            results.append(f"✅ {endpoint}: {actual_status}")
                        else:
                            results.append(f"❌ {endpoint}: {actual_status} (期望: {expected_status})")
                    else:
                        # 认证保护的端点可能返回重定向或401
                        if actual_status in [200, 302, 401, 403]:
                            results.append(f"✅ {endpoint}: {actual_status} (正常保护)")
                        else:
                            results.append(f"❌ {endpoint}: {actual_status}")
                            
                except Exception as e:
                    results.append(f"❌ {endpoint}: 连接错误 - {str(e)}")
            
            success_count = len([r for r in results if r.startswith('✅')])
            total_count = len(results)
            
            success = success_count >= (total_count * 0.8)  # 80%成功率
            return success, f"API端点测试 ({success_count}/{total_count}): {'; '.join(results)}"
            
        except Exception as e:
            return False, f"API端点测试失败: {str(e)}"

    def test_stripe_integration(self) -> Tuple[bool, str]:
        """测试Stripe集成"""
        try:
            # 检查Stripe密钥配置
            stripe_secret = os.environ.get('STRIPE_SECRET_KEY')
            if not stripe_secret:
                return False, "STRIPE_SECRET_KEY未配置"
            
            # 检查订阅路由
            from billing_routes import billing_bp
            
            # 检查计划数据
            from app import app
            from models_subscription import Plan
            
            with app.app_context():
                plans = Plan.query.all()
                if len(plans) == 0:
                    return False, "无订阅计划数据"
                
                plan_details = []
                for plan in plans:
                    plan_details.append(f"{plan.id}(${plan.price/100:.0f})")
                
                return True, f"Stripe集成就绪 - 密钥已配置, 计划: {', '.join(plan_details)}"
                
        except Exception as e:
            return False, f"Stripe集成测试失败: {str(e)}"

    def test_performance_metrics(self) -> Tuple[bool, str]:
        """测试性能指标"""
        try:
            # 测试数据库查询性能
            from app import app
            from models import db
            from sqlalchemy import text
            
            with app.app_context():
                # 测试大表查询性能
                start_time = time.time()
                
                # 测试技术指标表查询
                db.session.execute(text('SELECT COUNT(*) FROM technical_indicators')).fetchone()
                
                # 测试市场数据表查询
                db.session.execute(text('SELECT COUNT(*) FROM market_analytics')).fetchone()
                
                # 测试用户表查询
                db.session.execute(text('SELECT COUNT(*) FROM user_access')).fetchone()
                
                query_time = time.time() - start_time
                
                # 测试内存使用
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                performance_issues = []
                if query_time > 1.0:
                    performance_issues.append(f"数据库查询慢: {query_time:.2f}s")
                if memory_mb > 500:
                    performance_issues.append(f"内存使用高: {memory_mb:.1f}MB")
                
                if performance_issues:
                    return False, f"性能问题: {'; '.join(performance_issues)}"
                
                return True, f"性能正常 - 查询: {query_time:.3f}s, 内存: {memory_mb:.1f}MB"
                
        except Exception as e:
            return False, f"性能测试失败: {str(e)}"

    def run_comprehensive_tests(self):
        """运行全面测试套件"""
        logger.info("🚀 开始全面测试套件 - 目标99%准确率")
        
        # 定义测试顺序和重要性
        test_suite = [
            (self.test_server_health, "服务器健康检查", "高"),
            (self.test_database_connection, "数据库连接测试", "高"),
            (self.test_subscription_models, "订阅模型测试", "高"),
            (self.test_authentication_system, "认证系统测试", "高"),
            (self.test_technical_indicators_api, "技术指标API测试", "高"),
            (self.test_mining_calculations, "挖矿计算准确性测试", "高"),
            (self.test_real_time_data_integration, "实时数据集成测试", "中"),
            (self.test_api_endpoints, "API端点测试", "中"),
            (self.test_stripe_integration, "Stripe集成测试", "中"),
            (self.test_performance_metrics, "性能指标测试", "中"),
        ]
        
        for test_func, test_name, priority in test_suite:
            logger.info(f"▶️ 运行测试: {test_name} (优先级: {priority})")
            self.run_test_with_timer(test_func, test_name)
            
        # 生成测试报告
        self.generate_test_report()

    def generate_test_report(self):
        """生成测试报告"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 计算总执行时间
        total_execution_time = sum(r['execution_time'] for r in self.test_results)
        
        # 分类失败测试
        critical_failures = []
        warning_failures = []
        
        for result in self.test_results:
            if not result['success']:
                if any(keyword in result['test_name'].lower() for keyword in ['服务器', '数据库', '认证']):
                    critical_failures.append(result)
                else:
                    warning_failures.append(result)
        
        # 生成报告
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': round(success_rate, 2),
                'execution_time': round(total_execution_time, 3),
                'test_date': self.start_time.isoformat(),
                'target_accuracy': 99.0
            },
            'detailed_results': self.test_results,
            'critical_failures': critical_failures,
            'warning_failures': warning_failures
        }
        
        # 保存报告到文件
        report_filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印总结
        print("\n" + "="*80)
        print(f"📊 测试报告总结")
        print("="*80)
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests} ✅")
        print(f"失败测试: {failed_tests} ❌")
        print(f"成功率: {success_rate:.2f}%")
        print(f"执行时间: {total_execution_time:.3f}秒")
        print(f"报告文件: {report_filename}")
        
        # 状态评估
        if success_rate >= 99.0:
            print("🎉 状态: A++ 企业级 (99%+)")
        elif success_rate >= 95.0:
            print("🎊 状态: A+ 生产就绪 (95%+)")
        elif success_rate >= 90.0:
            print("✅ 状态: A 基本就绪 (90%+)")
        elif success_rate >= 80.0:
            print("⚠️ 状态: B 需要改进 (80%+)")
        else:
            print("❌ 状态: C 需要修复 (<80%)")
        
        print("\n关键问题:")
        if critical_failures:
            for failure in critical_failures:
                print(f"  🚨 {failure['test_name']}: {failure['details']}")
        else:
            print("  无关键问题 ✅")
        
        print("\n警告问题:")
        if warning_failures:
            for failure in warning_failures:
                print(f"  ⚠️ {failure['test_name']}: {failure['details']}")
        else:
            print("  无警告问题 ✅")
        
        print("="*80)
        
        return report


def main():
    """主函数"""
    print("🔧 初始化全面测试套件...")
    
    # 创建测试套件实例
    test_suite = ComprehensiveTestSuite()
    
    # 运行测试
    test_suite.run_comprehensive_tests()


if __name__ == "__main__":
    main()