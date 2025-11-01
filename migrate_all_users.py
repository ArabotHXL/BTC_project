#!/usr/bin/env python3
"""
完整用户迁移脚本 - 从旧数据库迁移所有16个用户到新数据库
"""
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import UserAccess

# 从旧数据库导出的所有用户数据
ALL_USERS = [
    {
        'id': 2,
        'name': 'test_free@test.com',
        'email': 'test_free@test.com',
        'username': None,
        'password_hash': 'scrypt:32768:8:1$jEsH5a7xpKlYXszT$a469d2405178ec76ac8464b076a06bc64237737c11fa5e98dc2a381ae32aa87c4980e34fb76ca1caa4f0e3ae17f2f4a71416efddca3f714970c9568d903982f5',
        'is_email_verified': True,
        'role': 'guest',
        'subscription_plan': 'free',
        'access_days': 365,
        'created_at': datetime(2025, 8, 13, 3, 42, 33, 941000),
        'expires_at': datetime(2026, 10, 7, 21, 4, 29, 521257),
    },
    {
        'id': 3,
        'name': 'test_basic@test.com',
        'email': 'test_basic@test.com',
        'username': None,
        'password_hash': 'scrypt:32768:8:1$CpA1WhhPst0Xkxp8$3d234f5bb96703327ba27da98cda848bee29a8060f80e80487b1ec089895de12dd243f2d630bae26e130ff31de9692345e99266c305000de1cd1ae94942aab02',
        'is_email_verified': True,
        'role': 'guest',
        'subscription_plan': 'free',
        'access_days': 365,
        'created_at': datetime(2025, 8, 13, 3, 42, 33, 941000),
        'expires_at': datetime(2026, 10, 7, 21, 4, 29, 521257),
    },
    {
        'id': 4,
        'name': 'test_pro@test.com',
        'email': 'test_pro@test.com',
        'username': None,
        'password_hash': 'scrypt:32768:8:1$BDjMHp8sHGggv2gz$c6d3a1c14f2efef3e251a41f0527afa07d9962e409051fa03311c4e3c8cb1e53aa2c5660b9c359d65a9667d337e194ba5d5a0b52443a8fec0ce18b90e8e40687',
        'is_email_verified': True,
        'role': 'guest',
        'subscription_plan': 'free',
        'access_days': 365,
        'created_at': datetime(2025, 8, 13, 3, 42, 33, 941000),
        'expires_at': datetime(2026, 10, 7, 21, 4, 29, 521257),
    },
    {
        'id': 5,
        'name': 'test@test.com',
        'email': 'test@test.com',
        'username': None,
        'password_hash': 'scrypt:32768:8:1$EJfUK5imrBK84Oxq$e4805fdd2ca79dd3e218938b0503be6286a3b429c8a0e17b5da125e85a32302a04ef2f55f2bbf12a79506fc7fa62335be589d97463d34e87f13cfae14dc441e3',
        'is_email_verified': True,
        'role': 'admin',
        'subscription_plan': 'free',
        'access_days': 365,
        'created_at': datetime(2025, 10, 7, 21, 4, 29, 521257),
        'expires_at': datetime(2026, 12, 31, 0, 0, 0),
        'last_login': datetime(2025, 10, 9, 22, 5, 47, 927676),
    },
    {
        'id': 6,
        'name': 'test@example.com',
        'email': 'test@example.com',
        'username': None,
        'password_hash': 'dummy_hash_for_testpass',
        'is_email_verified': True,
        'role': 'guest',
        'subscription_plan': 'free',
        'access_days': 365,
        'created_at': datetime(2025, 10, 7, 21, 4, 29, 521257),
        'expires_at': datetime(2026, 10, 7, 21, 4, 29, 521257),
    },
    {
        'id': 7,
        'name': 'Owner',
        'email': 'hxl2022hao@gmail.com',
        'username': None,
        'password_hash': 'scrypt:32768:8:1$MPsG5GJrSleLCii9$7c703137309b5950aea82ca99b616402df9b3ae71730700b8bffa3e40ea88f958d7134db497e74c0caf5a9b0291c8108c62de27595597e59df1a93c4f2be7410',
        'is_email_verified': True,
        'role': 'owner',
        'subscription_plan': 'pro',
        'access_days': 365,
        'created_at': datetime(2025, 10, 7, 21, 4, 29, 521257),
        'expires_at': datetime(2026, 10, 7, 21, 4, 29, 521257),
        'last_login': datetime(2025, 10, 25, 21, 23, 36, 717662),
    },
    {
        'id': 8,
        'name': 'Savy Sophie',
        'email': 'savysofie@yahoo.com',
        'username': None,
        'password_hash': 'scrypt:32768:8:1$J62kfOp36eYdJxxc$fa577fc9708e5926cbdb67eb05ff4b8932929feea478689a9f6ccb29ca12958d12674c7b348312c6cf46105fb8e69af12bf166e433fb74187c6bfde18f6275dd',
        'is_email_verified': True,
        'role': 'guest',
        'subscription_plan': 'free',
        'access_days': 90,
        'created_at': datetime(2025, 10, 7, 21, 23, 36, 531677),
        'expires_at': datetime(2026, 1, 5, 21, 23, 36, 531677),
    },
    {
        'id': 9,
        'name': 'Sebastian Less',
        'email': 'sebless001@gmail.com',
        'username': None,
        'password_hash': 'scrypt:32768:8:1$J62kfOp36eYdJxxc$fa577fc9708e5926cbdb67eb05ff4b8932929feea478689a9f6ccb29ca12958d12674c7b348312c6cf46105fb8e69af12bf166e433fb74187c6bfde18f6275dd',
        'is_email_verified': True,
        'role': 'guest',
        'subscription_plan': 'free',
        'access_days': 90,
        'created_at': datetime(2025, 10, 7, 21, 23, 36, 531677),
        'expires_at': datetime(2026, 1, 5, 21, 23, 36, 531677),
    },
    {
        'id': 10,
        'name': 'BTC Test LtpxyC',
        'email': 'testNyB1@example.com',
        'username': None,
        'password_hash': None,
        'is_email_verified': False,
        'role': 'customer',
        'subscription_plan': 'free',
        'access_days': 30,
        'created_at': datetime(2025, 10, 9, 4, 2, 50, 579720),
        'expires_at': datetime(2025, 11, 8, 4, 2, 50, 577689),
    },
    {
        'id': 12,
        'name': 'CRM Test User',
        'email': 'crm_test@test.com',
        'username': 'crm_test',
        'password_hash': 'scrypt:32768:8:1$3cAqANCCSADuCGvW$a545b3544f000ec6cb4de0f986f7ec30cee7d52f82a9b7f8cd494b23acb8998c84528d0b57549c198435b4fb6c7ba4e19963b8675b5e1df5ff890d1cc80c1ff2',
        'is_email_verified': True,
        'role': 'admin',
        'subscription_plan': 'pro',
        'access_days': 365,
        'created_at': datetime(2025, 10, 9, 13, 23, 38, 824530),
        'expires_at': datetime(2026, 10, 9, 13, 23, 38, 824530),
        'last_login': datetime(2025, 10, 9, 15, 33, 20, 507540),
    },
    {
        'id': 14,
        'name': 'John Doe',
        'email': 'client1@example.com',
        'username': None,
        'password_hash': None,
        'is_email_verified': True,
        'role': 'client',
        'subscription_plan': 'free',
        'access_days': 365,
        'company': 'Bitcoin Mining Co.',
        'created_at': datetime(2025, 10, 19, 3, 30, 20, 200331),
        'expires_at': datetime(2026, 10, 19, 3, 30, 20, 200331),
    },
    {
        'id': 15,
        'name': 'Jane Smith',
        'email': 'client2@example.com',
        'username': None,
        'password_hash': None,
        'is_email_verified': True,
        'role': 'client',
        'subscription_plan': 'free',
        'access_days': 365,
        'company': 'Crypto Farm LLC',
        'created_at': datetime(2025, 10, 19, 3, 30, 20, 200331),
        'expires_at': datetime(2026, 10, 19, 3, 30, 20, 200331),
    },
    {
        'id': 16,
        'name': 'Bob Johnson',
        'email': 'client3@example.com',
        'username': None,
        'password_hash': None,
        'is_email_verified': True,
        'role': 'client',
        'subscription_plan': 'free',
        'access_days': 365,
        'company': 'Digital Mining Inc.',
        'created_at': datetime(2025, 10, 19, 3, 30, 20, 200331),
        'expires_at': datetime(2026, 10, 19, 3, 30, 20, 200331),
    },
    {
        'id': 17,
        'name': 'Alice Wang',
        'email': 'alice.wang@cryptomining.cn',
        'username': None,
        'password_hash': None,
        'is_email_verified': True,
        'role': 'client',
        'subscription_plan': 'free',
        'access_days': 365,
        'company': '加密矿业公司',
        'created_at': datetime(2025, 10, 19, 3, 30, 20, 200331),
        'expires_at': datetime(2026, 10, 19, 3, 30, 20, 200331),
    },
    {
        'id': 19,
        'name': 'pixel',
        'email': 'pixelphotovision@gmail.com',
        'username': 'pixel',
        'password_hash': 'scrypt:32768:8:1$Z82lu9jiCvItw4Df$48ad1d797976a6363ef59de9222ca148b7d9ff97fe466f938873efb77a98156ac14209469958ddf01ca517f2cb27dccaaf760a480b7864003769977e7b7d39a9',
        'is_email_verified': True,
        'role': 'owner',
        'subscription_plan': 'free',
        'access_days': 7,
        'created_at': datetime(2025, 10, 25, 21, 21, 47, 586189),
        'expires_at': datetime(2025, 11, 1, 21, 21, 47, 463228),
    },
]

def migrate_all_users():
    """迁移所有用户账户到新数据库"""
    with app.app_context():
        print("=" * 80)
        print("HashInsight Enterprise - 完整用户数据库迁移")
        print("=" * 80)
        print(f"\n发现 {len(ALL_USERS)} 个用户账户需要迁移\n")
        
        success_count = 0
        update_count = 0
        skip_count = 0
        error_count = 0
        
        for user_data in ALL_USERS:
            try:
                email = user_data['email']
                
                # 检查用户是否已存在
                existing_user = UserAccess.query.filter_by(email=email).first()
                
                if existing_user:
                    # 更新现有用户
                    print(f"⚠️  更新用户: {email} (ID: {user_data['id']})")
                    existing_user.name = user_data.get('name')
                    existing_user.username = user_data.get('username')
                    if user_data.get('password_hash'):
                        existing_user.password_hash = user_data['password_hash']
                    existing_user.is_email_verified = user_data.get('is_email_verified', False)
                    existing_user.role = user_data.get('role', 'guest')
                    existing_user.subscription_plan = user_data.get('subscription_plan', 'free')
                    existing_user.access_days = user_data.get('access_days', 30)
                    existing_user.expires_at = user_data.get('expires_at')
                    existing_user.company = user_data.get('company')
                    if user_data.get('last_login'):
                        existing_user.last_login = user_data['last_login']
                    update_count += 1
                else:
                    # 创建新用户
                    print(f"✅ 创建用户: {email} (ID: {user_data['id']}, 角色: {user_data.get('role', 'guest')})")
                    new_user = UserAccess(
                        name=user_data.get('name'),
                        email=email,
                        username=user_data.get('username'),
                        password_hash=user_data.get('password_hash'),
                        is_email_verified=user_data.get('is_email_verified', False),
                        role=user_data.get('role', 'guest'),
                        subscription_plan=user_data.get('subscription_plan', 'free'),
                        access_days=user_data.get('access_days', 30),
                        created_at=user_data.get('created_at'),
                        expires_at=user_data.get('expires_at'),
                        last_login=user_data.get('last_login'),
                        company=user_data.get('company'),
                    )
                    db.session.add(new_user)
                    success_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"❌ 迁移失败 {email}: {e}")
                continue
        
        # 提交所有更改
        try:
            db.session.commit()
            print("\n" + "=" * 80)
            print("✅ 数据库迁移完成！")
            print("=" * 80)
            print(f"新建用户: {success_count}")
            print(f"更新用户: {update_count}")
            print(f"失败: {error_count}")
            print(f"总计: {len(ALL_USERS)} 个用户")
            print("=" * 80)
            
            # 显示关键用户信息
            print("\n🔑 关键账户信息:")
            print("-" * 80)
            print(f"Owner账户 #1: hxl2022hao@gmail.com (角色: owner, 订阅: pro)")
            print(f"Owner账户 #2: pixelphotovision@gmail.com (角色: owner, 订阅: free)")
            print(f"Admin账户 #1: test@test.com (角色: admin)")
            print(f"Admin账户 #2: crm_test@test.com (角色: admin, 用户名: crm_test)")
            print("-" * 80)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ 提交失败: {e}")
            return False

if __name__ == "__main__":
    print("\n⚠️  开始迁移前，请确保：")
    print("1. 新数据库已在Replit中创建")
    print("2. DATABASE_URL已更新到新数据库")
    print("3. Flask应用已重启并成功连接新数据库\n")
    
    input("按Enter键继续迁移，或Ctrl+C取消...")
    
    success = migrate_all_users()
    
    if success:
        print("\n✨ 迁移完成！所有用户现在可以使用原密码登录。")
        print("\n📝 测试建议:")
        print("   1. 访问 /login")
        print("   2. 使用 hxl2022hao@gmail.com + 原密码登录")
        print("   3. 验证所有功能正常")
    else:
        print("\n⚠️  迁移失败，请检查：")
        print("   1. 数据库连接是否正常")
        print("   2. 查看上方错误信息")
        print("   3. 确认数据库表结构已初始化")
