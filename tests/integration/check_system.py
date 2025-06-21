#!/usr/bin/env python3
"""系统完整性检查脚本"""

import sys
import os
sys.path.append('.')

from app import app
from models import *
from db import db

def check_system():
    """检查系统完整性"""
    with app.app_context():
        print("=== 系统完整性检查 ===")
        
        # 1. 检查用户访问权限
        print("\n1. 用户访问权限检查:")
        user_access = UserAccess.query.filter_by(email='hxl2022hao@gmail.com').first()
        if user_access:
            print(f"   ✓ 用户: {user_access.email}")
            print(f"   ✓ 角色: {user_access.role}")
            print(f"   ✓ 状态: {'激活' if user_access.is_active else '未激活'}")
            print(f"   ✓ 访问期限: {user_access.access_end_date}")
        else:
            print("   ✗ 未找到用户访问记录")
        
        # 2. 检查CRM客户数据
        print("\n2. CRM客户数据检查:")
        customer_count = Customer.query.count()
        print(f"   ✓ 客户总数: {customer_count}")
        
        if customer_count > 0:
            customers = Customer.query.limit(3).all()
            for customer in customers:
                print(f"   - 客户: {customer.company_name}")
                print(f"     联系人: {customer.primary_contact}")
                print(f"     状态: {customer.status}")
        
        # 3. 检查交易记录
        print("\n3. 交易记录检查:")
        deal_count = Deal.query.count()
        print(f"   ✓ 交易总数: {deal_count}")
        
        if deal_count > 0:
            deals = Deal.query.limit(3).all()
            for deal in deals:
                print(f"   - 交易: {deal.title}")
                print(f"     金额: ${deal.amount:,.2f}")
                print(f"     状态: {deal.status}")
        
        # 4. 检查佣金记录
        print("\n4. 佣金记录检查:")
        commission_count = BrokerCommissionRecord.query.count()
        print(f"   ✓ 佣金记录总数: {commission_count}")
        
        if commission_count > 0:
            commissions = BrokerCommissionRecord.query.limit(3).all()
            for comm in commissions:
                customer = Customer.query.get(comm.customer_id)
                customer_name = customer.company_name if customer else "未知客户"
                print(f"   - 客户: {customer_name}")
                print(f"     佣金金额: ${comm.commission_amount:,.2f}")
                print(f"     支付状态: {comm.payment_status}")
                print(f"     记录时间: {comm.record_date}")
        
        # 5. 检查商机记录
        print("\n5. 商机记录检查:")
        lead_count = Lead.query.count()
        print(f"   ✓ 商机总数: {lead_count}")
        
        if lead_count > 0:
            leads = Lead.query.limit(3).all()
            for lead in leads:
                customer = Customer.query.get(lead.customer_id)
                customer_name = customer.company_name if customer else "未知客户"
                print(f"   - 商机: {lead.title}")
                print(f"     客户: {customer_name}")
                print(f"     状态: {lead.status}")
                print(f"     价值: ${lead.value:,.2f}")
        
        # 6. 检查活动记录
        print("\n6. 活动记录检查:")
        activity_count = Activity.query.count()
        print(f"   ✓ 活动记录总数: {activity_count}")
        
        # 7. 检查编辑历史记录
        print("\n7. 编辑历史检查:")
        try:
            edit_history_count = CommissionEditHistory.query.count()
            print(f"   ✓ 佣金编辑历史记录: {edit_history_count}")
        except Exception as e:
            print(f"   - 佣金编辑历史检查失败: {e}")
        
        print("\n=== 检查完成 ===")

if __name__ == "__main__":
    check_system()