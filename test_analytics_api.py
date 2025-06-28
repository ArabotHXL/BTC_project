#!/usr/bin/env python3
"""
分析系统API测试
"""

import requests
import json
import time

def test_analytics_apis():
    """测试分析系统API端点"""
    
    # 创建会话并登录
    session = requests.Session()
    login_data = {'email': 'hxl2022hao@gmail.com'}
    login_response = session.post('http://localhost:5000/login', data=login_data)
    
    print('=== 分析系统API状态检查 ===')
    print(f'登录状态: {login_response.status_code}')
    
    # 测试分析API端点
    endpoints = [
        ('/api/analytics/market-data', '市场数据API'),
        ('/api/analytics/latest-report', '最新报告API'), 
        ('/api/analytics/technical-indicators', '技术指标API'),
        ('/api/analytics/price-history', '价格历史API')
    ]
    
    results = []
    
    for endpoint, name in endpoints:
        try:
            start_time = time.time()
            response = session.get(f'http://localhost:5000{endpoint}', timeout=10)
            response_time = time.time() - start_time
            
            print(f'\n{name} ({endpoint}):')
            print(f'  状态码: {response.status_code}')
            print(f'  响应时间: {response_time:.2f}秒')
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        if 'error' in data:
                            print(f'  错误: {data["error"]}')
                            results.append(('FAIL', name, data["error"]))
                        else:
                            keys = list(data.keys())
                            print(f'  成功: 包含 {len(keys)} 个字段')
                            print(f'  字段: {keys[:5]}{"..." if len(keys) > 5 else ""}')
                            
                            # 显示关键数据
                            if 'btc_price' in data and data['btc_price']:
                                print(f'  BTC价格: ${data["btc_price"]:,.2f}')
                            if 'network_hashrate' in data and data['network_hashrate']:
                                print(f'  网络算力: {data["network_hashrate"]:.1f} EH/s')
                            if 'rsi_14' in data and data['rsi_14']:
                                print(f'  RSI(14): {data["rsi_14"]:.1f}')
                            if 'title' in data:
                                print(f'  报告标题: {data["title"]}')
                            
                            results.append(('PASS', name, f'{len(keys)}个字段'))
                    else:
                        print(f'  数据类型: {type(data)}')
                        results.append(('WARN', name, f'非预期数据类型: {type(data)}'))
                        
                except json.JSONDecodeError as e:
                    print(f'  JSON解析错误: {str(e)}')
                    print(f'  原始响应: {response.text[:200]}...')
                    results.append(('FAIL', name, 'JSON解析失败'))
                    
            elif response.status_code == 403:
                print(f'  权限错误: 需要拥有者权限')
                results.append(('FAIL', name, '权限不足'))
            elif response.status_code == 500:
                print(f'  服务器错误: {response.text[:100]}...')
                results.append(('FAIL', name, '服务器内部错误'))
            else:
                print(f'  HTTP错误: {response.status_code}')
                print(f'  响应: {response.text[:100]}...')
                results.append(('FAIL', name, f'HTTP {response.status_code}'))
                
        except Exception as e:
            print(f'\n{name} ({endpoint}):')
            print(f'  连接异常: {str(e)}')
            results.append(('FAIL', name, f'连接异常: {str(e)}'))
    
    # 汇总结果
    print(f'\n=== API测试结果汇总 ===')
    passed = len([r for r in results if r[0] == 'PASS'])
    warned = len([r for r in results if r[0] == 'WARN'])
    failed = len([r for r in results if r[0] == 'FAIL'])
    
    print(f'总测试: {len(results)}')
    print(f'✅ 通过: {passed}')
    print(f'⚠️ 警告: {warned}') 
    print(f'❌ 失败: {failed}')
    
    if passed >= 2:
        print(f'\n🎉 API状态: 良好 - 主要端点可用')
    elif passed >= 1:
        print(f'\n⚠️ API状态: 部分可用 - 需要检查失败端点')
    else:
        print(f'\n❌ API状态: 需要修复 - 无可用端点')
    
    return results

if __name__ == "__main__":
    test_analytics_apis()