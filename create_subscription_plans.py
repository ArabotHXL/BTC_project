#!/usr/bin/env python3
"""
创建订阅计划数据 - 直接数据库操作避免SQLAlchemy问题
"""
import os
import psycopg2
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_subscription_plans():
    """直接在数据库中创建订阅计划"""
    try:
        # 连接数据库
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        # 检查plans表是否存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'plans'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.info("创建plans表...")
            cursor.execute("""
                CREATE TABLE plans (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    price INTEGER NOT NULL,
                    currency VARCHAR(3) DEFAULT 'USD',
                    max_miners INTEGER DEFAULT 0,
                    allow_api BOOLEAN DEFAULT FALSE,
                    allow_scenarios BOOLEAN DEFAULT FALSE,
                    allow_historical_data BOOLEAN DEFAULT FALSE,
                    allow_advanced_analytics BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
        # 检查subscriptions表是否存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'subscriptions'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.info("创建subscriptions表...")
            cursor.execute("""
                CREATE TABLE subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL,
                    plan_id INTEGER REFERENCES plans(id),
                    stripe_subscription_id VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                );
            """)
        
        # 检查是否已有计划数据
        cursor.execute("SELECT COUNT(*) FROM plans")
        plan_count = cursor.fetchone()[0]
        
        if plan_count == 0:
            logger.info("插入订阅计划数据...")
            
            plans_data = [
                {
                    'id': 1,
                    'name': 'Free',
                    'price': 0,
                    'max_miners': 10,
                    'allow_api': False,
                    'allow_scenarios': False,
                    'allow_historical_data': False,
                    'allow_advanced_analytics': False
                },
                {
                    'id': 2,
                    'name': 'Basic',
                    'price': 2900,  # $29.00 in cents
                    'max_miners': 100,
                    'allow_api': True,
                    'allow_scenarios': True,
                    'allow_historical_data': True,
                    'allow_advanced_analytics': False
                },
                {
                    'id': 3,
                    'name': 'Pro',
                    'price': 9900,  # $99.00 in cents
                    'max_miners': 1000,
                    'allow_api': True,
                    'allow_scenarios': True,
                    'allow_historical_data': True,
                    'allow_advanced_analytics': True
                }
            ]
            
            for plan in plans_data:
                cursor.execute("""
                    INSERT INTO plans (id, name, price, max_miners, allow_api, allow_scenarios)
                    VALUES (%(id)s, %(name)s, %(price)s, %(max_miners)s, %(allow_api)s, %(allow_scenarios)s)
                    ON CONFLICT (id) DO NOTHING
                """, plan)
            
            logger.info(f"成功插入 {len(plans_data)} 个订阅计划")
        else:
            logger.info(f"订阅计划已存在，共 {plan_count} 个")
        
        # 提交更改
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("订阅计划创建完成")
        return True
        
    except Exception as e:
        logger.error(f"创建订阅计划失败: {e}")
        return False

if __name__ == "__main__":
    create_subscription_plans()