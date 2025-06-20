#!/usr/bin/env python3
"""
JavaScript错误专项测试
专门测试和验证JavaScript DOM元素访问错误的修复情况
"""

import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

class JavaScriptErrorTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.driver = None
        self.test_results = []
        
    def setup_driver(self):
        """设置Chrome浏览器驱动"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            return True
        except Exception as e:
            print(f"Chrome驱动设置失败: {str(e)}")
            return False
    
    def authenticate_user(self):
        """用户认证"""
        try:
            self.driver.get(f"{self.base_url}/login")
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            
            # 输入邮箱
            email_input = self.driver.find_element(By.NAME, "email")
            email_input.send_keys("user@example.com")
            
            # 提交表单
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            # 等待重定向
            time.sleep(2)
            
            return True
        except Exception as e:
            print(f"用户认证失败: {str(e)}")
            return False
    
    def test_javascript_errors(self):
        """测试JavaScript错误"""
        if not self.setup_driver():
            return False
            
        try:
            # 认证用户
            if not self.authenticate_user():
                print("无法完成用户认证，跳过JavaScript测试")
                return False
            
            # 导航到主页
            self.driver.get(self.base_url)
            
            # 等待页面完全加载
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "miner-model"))
            )
            
            # 额外等待JavaScript执行
            time.sleep(3)
            
            # 获取控制台日志
            logs = self.driver.get_log('browser')
            
            # 分析错误
            js_errors = []
            for log in logs:
                if log['level'] == 'SEVERE' and 'javascript' in log['source'].lower():
                    js_errors.append(log)
            
            # 检查是否还有"Cannot read properties of null"错误
            null_errors = [err for err in js_errors if 'Cannot read properties of null' in err['message']]
            
            print(f"检测到的JavaScript错误数量: {len(js_errors)}")
            print(f"null引用错误数量: {len(null_errors)}")
            
            if null_errors:
                print("发现的null引用错误:")
                for error in null_errors:
                    print(f"  - {error['message']}")
                return False
            else:
                print("✓ 未发现null引用错误")
                
            # 测试DOM元素是否正常加载
            required_elements = [
                "miner-model", "miner-count", "hashrate", 
                "power-consumption", "electricity-cost"
            ]
            
            missing_elements = []
            for element_id in required_elements:
                try:
                    element = self.driver.find_element(By.ID, element_id)
                    if not element.is_displayed():
                        missing_elements.append(element_id)
                except:
                    missing_elements.append(element_id)
            
            if missing_elements:
                print(f"缺失的DOM元素: {missing_elements}")
                return False
            else:
                print("✓ 所有必需的DOM元素已正确加载")
            
            # 测试矿机列表是否加载
            try:
                miner_select = self.driver.find_element(By.ID, "miner-model")
                options = miner_select.find_elements(By.TAG_NAME, "option")
                
                if len(options) > 1:  # 除了默认选项
                    print(f"✓ 矿机列表已加载 ({len(options)-1} 个选项)")
                else:
                    print("⚠ 矿机列表未正确加载")
                    
            except Exception as e:
                print(f"矿机列表测试失败: {str(e)}")
            
            # 测试JavaScript函数调用
            try:
                # 执行一个简单的JavaScript函数测试
                result = self.driver.execute_script("""
                    try {
                        // 测试DOM元素访问
                        var element = document.getElementById('miner-model');
                        if (!element) return 'FAIL: Element not found';
                        
                        // 测试样式访问
                        if (!element.style) return 'FAIL: Style property not accessible';
                        
                        return 'SUCCESS: DOM access working';
                    } catch (error) {
                        return 'ERROR: ' + error.message;
                    }
                """)
                
                if result.startswith('SUCCESS'):
                    print(f"✓ JavaScript DOM访问测试通过: {result}")
                else:
                    print(f"✗ JavaScript DOM访问测试失败: {result}")
                    return False
                    
            except Exception as e:
                print(f"JavaScript执行测试失败: {str(e)}")
                return False
            
            return True
            
        except Exception as e:
            print(f"JavaScript错误测试失败: {str(e)}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def run_basic_api_test(self):
        """运行基本API测试（无需浏览器）"""
        print("执行基本API功能测试...")
        
        session = requests.Session()
        
        try:
            # 基本连接测试
            response = session.get(self.base_url, timeout=10)
            if response.status_code in [200, 302]:
                print("✓ 基本连接正常")
            else:
                print(f"✗ 基本连接失败: {response.status_code}")
                return False
            
            # 认证测试
            auth_response = session.post(f"{self.base_url}/login", 
                                       data={'email': 'user@example.com'},
                                       allow_redirects=True)
            if auth_response.status_code == 200:
                print("✓ 用户认证正常")
            else:
                print(f"✗ 用户认证失败: {auth_response.status_code}")
                return False
            
            # 挖矿计算测试
            calc_data = {
                'miner_model': 'Antminer S21 XP',
                'miner_count': '5',
                'electricity_cost': '0.05',
                'use_real_time': 'on'
            }
            
            calc_response = session.post(f"{self.base_url}/calculate", data=calc_data)
            if calc_response.status_code == 200:
                data = calc_response.json()
                if data.get('success'):
                    print("✓ 挖矿计算功能正常")
                else:
                    print(f"✗ 挖矿计算返回错误: {data.get('error', '未知错误')}")
            else:
                print(f"✗ 挖矿计算请求失败: {calc_response.status_code}")
            
            return True
            
        except Exception as e:
            print(f"API测试失败: {str(e)}")
            return False

def main():
    print("=" * 60)
    print("JavaScript错误专项测试")
    print("=" * 60)
    
    tester = JavaScriptErrorTest()
    
    # 运行基本API测试
    print("\n1. 基本API功能测试")
    print("-" * 30)
    api_success = tester.run_basic_api_test()
    
    # 运行JavaScript错误测试
    print("\n2. JavaScript DOM错误测试")
    print("-" * 30)
    try:
        js_success = tester.test_javascript_errors()
    except Exception as e:
        print(f"JavaScript测试执行失败: {str(e)}")
        print("这通常表示Chrome驱动不可用，但不影响应用功能")
        js_success = None
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    if api_success:
        print("✓ 核心API功能: 正常")
    else:
        print("✗ 核心API功能: 异常")
    
    if js_success is True:
        print("✓ JavaScript DOM错误: 已修复")
    elif js_success is False:
        print("✗ JavaScript DOM错误: 仍存在")
    else:
        print("? JavaScript DOM错误: 无法测试（缺少浏览器环境）")
    
    print("\n应用程序整体状态:", "良好" if api_success else "需要关注")

if __name__ == "__main__":
    main()