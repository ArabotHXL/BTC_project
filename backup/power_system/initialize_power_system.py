#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
电力管理系统快速数据初始化工具
用于快速创建测试数据和电力削减计划
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000/api"

def print_status(message):
    """打印状态信息"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def initialize_system():
    """初始化系统数据"""
    print_status("开始初始化电力管理系统数据...")
    
    # 步骤1: 初始化矿机数据
    print_status("正在创建测试矿机数据...")
    response = requests.post(f"{BASE_URL}/initialize-miners", json={"count": 100})
    if response.status_code == 200:
        data = response.json()
        print_status(f"成功创建 {data.get('count', 0)} 台矿机数据")
    else:
        print_status(f"初始化矿机数据失败: {response.text}")
        return False
    
    # 步骤2: 获取系统状态
    print_status("获取系统状态...")
    response = requests.get(f"{BASE_URL}/system-status")
    if response.status_code == 200:
        status = response.json()
        print_status(f"系统状态: 总矿机数: {status.get('total_miners')}, "
                    f"总算力: {status.get('total_hashrate')} TH/s, "
                    f"总功耗: {status.get('total_power')} W")
    else:
        print_status(f"获取系统状态失败: {response.text}")
    
    # 步骤3: 创建电力削减计划
    print_status("创建电力削减计划...")
    plans = [
        {"name": "轻度削减计划", "description": "削减10%电力", "reduction_percentage": 10, 
         "target_categories": ["D"], "active": False},
        {"name": "中度削减计划", "description": "削减25%电力", "reduction_percentage": 25, 
         "target_categories": ["C", "D"], "active": False},
        {"name": "重度削减计划", "description": "削减50%电力", "reduction_percentage": 50, 
         "target_categories": ["B", "C", "D"], "active": False}
    ]
    
    for plan in plans:
        response = requests.post(f"{BASE_URL}/create-reduction-plan", json=plan)
        if response.status_code == 200:
            plan_data = response.json()
            print_status(f"成功创建削减计划: {plan['name']}, ID: {plan_data.get('id')}")
        else:
            print_status(f"创建削减计划失败: {response.text}")
    
    # 步骤4: 创建性能快照
    print_status("创建性能快照...")
    response = requests.post(f"{BASE_URL}/create-snapshot")
    if response.status_code == 200:
        snapshot = response.json()
        print_status(f"成功创建性能快照: ID: {snapshot.get('id')}")
    else:
        print_status(f"创建性能快照失败: {response.text}")
    
    print_status("初始化完成! 现在可以访问电力管理系统仪表盘来查看数据。")
    return True

def apply_power_reduction(percentage=10):
    """应用电力削减"""
    print_status(f"正在应用{percentage}%电力削减...")
    response = requests.post(f"{BASE_URL}/apply-reduction", json={"percentage": percentage})
    if response.status_code == 200:
        result = response.json()
        print_status(f"削减成功: 关闭了 {result.get('shutdown_count')} 台矿机, "
                    f"节省了 {result.get('power_saved')} W电力")
    else:
        print_status(f"应用削减失败: {response.text}")

def generate_rotation():
    """生成轮换计划"""
    print_status("正在生成轮换计划...")
    response = requests.post(f"{BASE_URL}/generate-rotation")
    if response.status_code == 200:
        result = response.json()
        print_status(f"轮换计划生成成功: 计划ID: {result.get('id')}, "
                    f"涉及 {len(result.get('miners_to_shutdown', []))} 台关闭矿机和 "
                    f"{len(result.get('miners_to_start', []))} 台启动矿机")
        return result.get('id')
    else:
        print_status(f"生成轮换计划失败: {response.text}")
        return None

def execute_rotation(plan_id):
    """执行轮换计划"""
    if not plan_id:
        print_status("无法执行轮换计划: 计划ID为空")
        return
    
    print_status(f"正在执行轮换计划 ID: {plan_id}...")
    response = requests.post(f"{BASE_URL}/execute-rotation", json={"plan_id": plan_id})
    if response.status_code == 200:
        result = response.json()
        print_status(f"轮换计划执行成功: {result.get('message')}")
    else:
        print_status(f"执行轮换计划失败: {response.text}")

def activate_reduction_plan(plan_id):
    """激活电力削减计划"""
    print_status(f"正在激活削减计划 ID: {plan_id}...")
    response = requests.post(f"{BASE_URL}/activate-reduction-plan", json={"plan_id": plan_id})
    if response.status_code == 200:
        result = response.json()
        print_status(f"削减计划激活成功: {result.get('message')}")
    else:
        print_status(f"激活削减计划失败: {response.text}")

def demo_workflow():
    """演示完整工作流程"""
    print_status("开始演示电力管理系统工作流程...")
    
    # 初始化系统
    if not initialize_system():
        print_status("初始化失败，无法继续演示")
        return
    
    # 等待2秒
    time.sleep(2)
    
    # 应用10%的电力削减
    apply_power_reduction(10)
    
    # 等待2秒
    time.sleep(2)
    
    # 生成轮换计划
    plan_id = generate_rotation()
    
    # 等待2秒
    time.sleep(2)
    
    # 执行轮换计划
    if plan_id:
        execute_rotation(plan_id)
    
    # 获取削减计划
    print_status("获取所有削减计划...")
    response = requests.get(f"{BASE_URL}/reduction-plans")
    if response.status_code == 200:
        plans = response.json()
        if plans:
            # 激活第一个削减计划
            activate_reduction_plan(plans[0]['id'])
    
    print_status("演示完成! 请访问电力管理系统仪表盘查看结果。")

if __name__ == "__main__":
    print("电力管理系统快速初始化工具")
    print("=======================")
    print("1. 初始化系统数据 (创建矿机和削减计划)")
    print("2. 应用10%电力削减")
    print("3. 应用25%电力削减") 
    print("4. 应用50%电力削减")
    print("5. 生成并执行轮换计划")
    print("6. 运行完整演示流程")
    print("0. 退出")
    print("=======================")
    
    choice = input("请选择操作 (0-6): ")
    
    if choice == "1":
        initialize_system()
    elif choice == "2":
        apply_power_reduction(10)
    elif choice == "3":
        apply_power_reduction(25)
    elif choice == "4":
        apply_power_reduction(50)
    elif choice == "5":
        plan_id = generate_rotation()
        if plan_id:
            execute_rotation(plan_id)
    elif choice == "6":
        demo_workflow()
    elif choice == "0":
        print("退出程序")
    else:
        print("无效选择")