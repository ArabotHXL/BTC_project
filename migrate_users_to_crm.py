"""
将用户访问权限数据迁移到CRM系统的脚本
此脚本将user_access表中的所有用户迁移为CRM系统中的客户
"""

from datetime import datetime
from flask import Flask
from models import UserAccess, Customer, Contact, Lead, db

def migrate_users_to_crm():
    """
    将UserAccess表中的用户迁移到CRM系统中
    1. 将每个UserAccess记录转换为Customer记录
    2. 将用户个人信息创建为主要联系人
    3. 为每个客户创建一个初始的"用户访问"商机
    4. 记录迁移活动
    """
    print("开始迁移用户数据到CRM系统...")
    
    # 获取所有用户记录
    users = UserAccess.query.all()
    print(f"找到 {len(users)} 个用户记录需要迁移")
    
    # 迁移计数器
    migrated_count = 0
    already_exists_count = 0
    
    # 遍历每个用户并迁移
    for user in users:
        # 检查是否已经存在同名/同邮箱的客户
        existing_customer = Customer.query.filter(
            (Customer.email == user.email) | 
            ((Customer.name == user.name) & (Customer.company == user.company))
        ).first()
        
        if existing_customer:
            print(f"客户已存在: {user.name} ({user.email})")
            already_exists_count += 1
            continue
        
        # 创建新客户记录
        customer = Customer(
            name=user.name,
            company=user.company,
            email=user.email,
            customer_type="企业" if user.company else "个人",
            tags="已迁移用户,授权用户",
            created_at=user.created_at
        )
        db.session.add(customer)
        db.session.flush()  # 获取ID而不提交事务
        
        # 创建主要联系人
        contact = Contact(
            customer_id=customer.id,
            name=user.name,
            email=user.email,
            position=user.position,
            primary=True,
            notes=f"从用户访问系统迁移 - 角色: {user.role}"
        )
        db.session.add(contact)
        
        # 创建一个初始商机记录用户访问权限
        lead = Lead(
            customer_id=customer.id,
            title=f"{user.name} 访问授权",
            status="QUALIFIED" if user.has_access() else "LOST",  # 根据当前访问状态设置
            source="系统迁移",
            estimated_value=0.0,  # 授权访问没有直接价值
            assigned_to="系统管理员",
            description=f"用户访问授权信息 - 创建于 {user.created_at.strftime('%Y-%m-%d')}, "
                      f"过期于 {user.expires_at.strftime('%Y-%m-%d')}。"
                      f"\n备注: {user.notes if user.notes else '无'}"
        )
        db.session.add(lead)
        
        # 提交到数据库
        db.session.commit()
        
        print(f"成功迁移用户: {user.name} ({user.email}) -> 客户ID: {customer.id}")
        migrated_count += 1
    
    print("迁移完成!")
    print(f"总计: {len(users)} 个用户")
    print(f"成功迁移: {migrated_count} 个用户")
    print(f"已存在 (跳过): {already_exists_count} 个用户")

if __name__ == "__main__":
    # 创建一个临时应用上下文
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instance/database.db"  # 根据实际情况修改
    db.init_app(app)
    
    with app.app_context():
        migrate_users_to_crm()