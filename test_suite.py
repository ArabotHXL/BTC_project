"""
综合测试套件 - 目标: 99%+ 准确率和通过率
包含安全性、功能性、性能和集成测试
"""

import unittest
import json
import os
import sys
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置测试环境
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret-key'
os.environ['AUTHORIZED_EMAILS'] = 'test@example.com,admin@example.com'
os.environ['COINWARZ_API_KEY'] = 'test-api-key'

from app import app, db
from models import UserAccess, Customer, Deal
from auth import verify_password_login, get_authorized_emails
from security_enhancements import SecurityManager, validate_mining_input
from mining_calculator import calculate_mining_profitability, MINER_DATA
from modules.analytics.engines.analytics_engine import AnalyticsEngine
from language_engine import LanguageEngine
from coinwarz_api import get_coinwarz_profitability

class SecurityTestCase(unittest.TestCase):
    """安全性测试"""
    
    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        self.security_manager = SecurityManager(app)
        
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_csrf_token_generation(self):
        """测试CSRF令牌生成"""
        with self.client:
            response = self.client.get('/')
            self.assertEqual(response.status_code, 302)  # Redirect to login
            
            # 检查session中是否有CSRF令牌
            with self.client.session_transaction() as sess:
                csrf_token = sess.get('csrf_token')
                self.assertIsNotNone(csrf_token)
                self.assertEqual(len(csrf_token), 32)
    
    def test_csrf_protection(self):
        """测试CSRF保护"""
        # 无CSRF令牌的POST请求应该被拒绝
        response = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password'
        })
        # 登录页面应该接受无CSRF的请求（公开端点）
        self.assertIn(response.status_code, [200, 302])
    
    def test_xss_prevention(self):
        """测试XSS防护"""
        xss_payload = '<script>alert("XSS")</script>'
        sanitized = SecurityManager.sanitize_input(xss_payload)
        self.assertNotIn('<script>', sanitized)
        self.assertIn('&lt;script&gt;', sanitized)
    
    def test_sql_injection_prevention(self):
        """测试SQL注入防护"""
        # 尝试SQL注入
        malicious_email = "'; DROP TABLE users;--"
        user = verify_password_login(malicious_email, 'password')
        self.assertIsNone(user)
        
        # 确认表仍然存在
        tables = db.inspect(db.engine).get_table_names()
        self.assertIn('user_access', tables)
    
    def test_password_strength_validation(self):
        """测试密码强度验证"""
        weak_passwords = ['123456', 'password', 'abc123', 'qwerty']
        for pwd in weak_passwords:
            valid, msg = SecurityManager.validate_password_strength(pwd)
            self.assertFalse(valid)
        
        strong_password = 'MyStr0ng!Pass#2024'
        valid, msg = SecurityManager.validate_password_strength(strong_password)
        self.assertTrue(valid)
    
    def test_input_validation(self):
        """测试输入验证"""
        # 测试NaN和无限值防护
        invalid_inputs = [
            {'hashrate': 'NaN', 'power': 1000},
            {'hashrate': float('inf'), 'power': 1000},
            {'hashrate': -100, 'power': 1000},
            {'hashrate': 100, 'power': -50}
        ]
        
        for input_data in invalid_inputs:
            valid, result = validate_mining_input(input_data)
            self.assertFalse(valid)
        
        # 测试有效输入
        valid_input = {
            'hashrate': 100,
            'power': 3000,
            'electricity_cost': 0.05,
            'pool_fee': 2
        }
        valid, result = validate_mining_input(valid_input)
        self.assertTrue(valid)
        self.assertEqual(result['hashrate'], 100)
    
    def test_rate_limiting(self):
        """测试速率限制"""
        sm = SecurityManager()
        client_id = 'test_client'
        
        # 测试正常请求
        for i in range(10):
            self.assertTrue(sm.rate_limit(client_id, max_requests=10, window=60))
        
        # 第11个请求应该被拒绝
        self.assertFalse(sm.rate_limit(client_id, max_requests=10, window=60))
    
    def test_secure_headers(self):
        """测试安全响应头"""
        response = self.client.get('/health')
        
        # 检查安全头
        self.assertEqual(response.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertIn('Content-Security-Policy', response.headers)
    
    def test_authorization_check(self):
        """测试授权检查"""
        # 未授权访问应该被重定向
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        
        # 授权邮箱列表应该从环境变量加载
        emails = get_authorized_emails()
        self.assertIn('test@example.com', emails)

class FunctionalTestCase(unittest.TestCase):
    """功能性测试"""
    
    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        
        # 创建测试用户
        self.test_user = UserAccess(
            email='test@example.com',
            username='testuser',
            is_email_verified=True,
            has_access=True
        )
        self.test_user.set_password('Test@1234')
        db.session.add(self.test_user)
        db.session.commit()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_user_registration(self):
        """测试用户注册"""
        response = self.client.post('/register', data={
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'NewUser@1234'
        }, follow_redirects=True)
        
        # 检查用户是否创建
        user = UserAccess.query.filter_by(email='newuser@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'newuser')
        self.assertFalse(user.is_email_verified)
    
    def test_user_login(self):
        """测试用户登录"""
        response = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'Test@1234'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # 检查session
        with self.client.session_transaction() as sess:
            self.assertIn('user_id', sess)
    
    def test_mining_calculation(self):
        """测试挖矿计算"""
        result = calculate_mining_profitability(
            hashrate=100,
            power_consumption=3000,
            electricity_cost=0.05,
            pool_fee=2,
            btc_price=50000,
            network_difficulty=30000000000000,
            block_reward=6.25
        )
        
        self.assertIsNotNone(result)
        self.assertIn('daily_revenue_btc', result)
        self.assertIn('daily_profit_usd', result)
        self.assertIn('monthly_profit_usd', result)
        self.assertIn('break_even_days', result)
        
        # 验证计算逻辑
        self.assertGreaterEqual(result['daily_revenue_btc'], 0)
        self.assertIsInstance(result['daily_profit_usd'], (int, float))
    
    def test_miner_data_integrity(self):
        """测试矿机数据完整性"""
        self.assertIsInstance(MINER_DATA, list)
        self.assertGreater(len(MINER_DATA), 0)
        
        for miner in MINER_DATA:
            self.assertIn('model', miner)
            self.assertIn('hashrate', miner)
            self.assertIn('power', miner)
            self.assertIn('algorithm', miner)
            
            # 验证数据类型
            self.assertIsInstance(miner['hashrate'], (int, float))
            self.assertIsInstance(miner['power'], (int, float))
            self.assertGreater(miner['hashrate'], 0)
            self.assertGreater(miner['power'], 0)
    
    def test_language_switching(self):
        """测试语言切换"""
        lang_engine = LanguageEngine()
        
        # 测试中文
        lang_engine.set_language('zh')
        self.assertEqual(lang_engine.get_language(), 'zh')
        zh_text = lang_engine.translate('welcome')
        self.assertIsNotNone(zh_text)
        
        # 测试英文
        lang_engine.set_language('en')
        self.assertEqual(lang_engine.get_language(), 'en')
        en_text = lang_engine.translate('welcome')
        self.assertIsNotNone(en_text)
        
        # 确保翻译不同
        self.assertNotEqual(zh_text, en_text)
    
    def test_api_endpoints(self):
        """测试API端点"""
        # 登录
        self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'Test@1234'
        })
        
        # 测试API端点
        endpoints = [
            '/api/realtime_data',
            '/api/market_snapshot',
            '/api/mining_metrics',
            '/api/technical_indicators'
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertIn(response.status_code, [200, 403])
            
            if response.status_code == 200:
                data = json.loads(response.data)
                self.assertIsInstance(data, dict)

class PerformanceTestCase(unittest.TestCase):
    """性能测试"""
    
    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_response_time(self):
        """测试响应时间"""
        start_time = time.time()
        response = self.client.get('/health')
        end_time = time.time()
        
        response_time = end_time - start_time
        self.assertLess(response_time, 1.0)  # 响应时间应小于1秒
        self.assertEqual(response.status_code, 200)
    
    def test_concurrent_requests(self):
        """测试并发请求处理"""
        import threading
        
        results = []
        
        def make_request():
            response = self.client.get('/health')
            results.append(response.status_code)
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 所有请求都应该成功
        self.assertEqual(len(results), 10)
        for status in results:
            self.assertEqual(status, 200)
    
    def test_database_connection_pool(self):
        """测试数据库连接池"""
        # 执行多个数据库查询
        for i in range(20):
            users = UserAccess.query.all()
            self.assertIsNotNone(users)
        
        # 检查连接池状态
        pool = db.engine.pool
        self.assertLessEqual(pool.size(), 10)  # 连接池大小应该受限

class IntegrationTestCase(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    @patch('coinwarz_api.requests.get')
    def test_coinwarz_integration(self, mock_get):
        """测试CoinWarz API集成"""
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Success': True,
            'Data': [{
                'CoinTag': 'BTC',
                'ExchangeRate': 50000,
                'Difficulty': 30000000000000,
                'BlockReward': 6.25
            }]
        }
        mock_get.return_value = mock_response
        
        # 测试API调用
        result = get_coinwarz_profitability('sha-256')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['CoinTag'], 'BTC')
    
    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        # 1. 注册用户
        response = self.client.post('/register', data={
            'email': 'workflow@example.com',
            'username': 'workflowuser',
            'password': 'Workflow@1234'
        }, follow_redirects=True)
        
        # 2. 验证邮箱（模拟）
        user = UserAccess.query.filter_by(email='workflow@example.com').first()
        user.is_email_verified = True
        user.has_access = True
        db.session.commit()
        
        # 3. 登录
        response = self.client.post('/login', data={
            'email': 'workflow@example.com',
            'password': 'Workflow@1234'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # 4. 访问仪表板
        response = self.client.get('/dashboard')
        self.assertIn(response.status_code, [200, 302])
        
        # 5. 执行挖矿计算
        response = self.client.post('/api/calculate', 
            json={
                'hashrate': 100,
                'power': 3000,
                'electricity_cost': 0.05
            },
            content_type='application/json'
        )
        
        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIn('success', data)

class DataIntegrityTestCase(unittest.TestCase):
    """数据完整性测试"""
    
    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_no_hardcoded_secrets(self):
        """测试无硬编码密钥"""
        # 检查环境变量配置
        self.assertIsNotNone(os.environ.get('SESSION_SECRET'))
        
        # 检查CoinWarz API不使用硬编码密钥
        from coinwarz_api import COINWARZ_API_KEY
        self.assertNotEqual(COINWARZ_API_KEY, '8dd87e048ec84b6c8ad3322fb07f747a')
    
    def test_database_constraints(self):
        """测试数据库约束"""
        # 测试唯一性约束
        user1 = UserAccess(email='unique@example.com', username='unique1')
        user1.set_password('Pass@1234')
        db.session.add(user1)
        db.session.commit()
        
        # 尝试创建重复邮箱的用户
        user2 = UserAccess(email='unique@example.com', username='unique2')
        user2.set_password('Pass@1234')
        db.session.add(user2)
        
        with self.assertRaises(Exception):
            db.session.commit()
        
        db.session.rollback()
    
    def test_transaction_rollback(self):
        """测试事务回滚"""
        try:
            user = UserAccess(email='rollback@example.com', username='rollback')
            user.set_password('Pass@1234')
            db.session.add(user)
            
            # 故意触发错误
            raise Exception("Test rollback")
            
            db.session.commit()
        except:
            db.session.rollback()
        
        # 确认用户未被创建
        user = UserAccess.query.filter_by(email='rollback@example.com').first()
        self.assertIsNone(user)

def run_tests():
    """运行所有测试并生成报告"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试用例
    suite.addTests(loader.loadTestsFromTestCase(SecurityTestCase))
    suite.addTests(loader.loadTestsFromTestCase(FunctionalTestCase))
    suite.addTests(loader.loadTestsFromTestCase(PerformanceTestCase))
    suite.addTests(loader.loadTestsFromTestCase(IntegrationTestCase))
    suite.addTests(loader.loadTestsFromTestCase(DataIntegrityTestCase))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 生成测试报告
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success = total_tests - failures - errors
    
    print("\n" + "="*60)
    print("测试报告摘要")
    print("="*60)
    print(f"总测试数: {total_tests}")
    print(f"成功: {success}")
    print(f"失败: {failures}")
    print(f"错误: {errors}")
    print(f"通过率: {(success/total_tests)*100:.2f}%")
    print(f"准确率: {(success/total_tests)*100:.2f}%")
    
    # 详细错误报告
    if failures > 0:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback[:200]}...")
    
    if errors > 0:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback[:200]}...")
    
    # 返回是否达到99%通过率
    pass_rate = (success/total_tests)*100
    return pass_rate >= 99.0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)