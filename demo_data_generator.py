"""
演示数据生成器 - Sprint 1 要求
生成2个站点、若干矿机、近7天遥测数据、2条公告
"""
import random
from datetime import datetime, timedelta
from models import (
    HostingSite, HostingMiner, MinerTelemetry, HostingIncident, 
    HostingTicket, HostingBill, UserAccess, MinerModel, db
)
import logging

logger = logging.getLogger(__name__)

def generate_demo_data():
    """生成演示数据"""
    try:
        logger.info("开始生成演示数据...")
        
        # 创建演示用户
        demo_users = create_demo_users()
        
        # 创建矿机型号
        miner_models = create_miner_models()
        
        # 创建演示站点
        demo_sites = create_demo_sites()
        
        # 创建演示矿机
        demo_miners = create_demo_miners(demo_sites, demo_users, miner_models)
        
        # 生成遥测数据（近7天）
        create_telemetry_data(demo_miners)
        
        # 创建事件和公告
        create_demo_incidents(demo_sites)
        
        # 创建演示工单
        create_demo_tickets(demo_sites, demo_users)
        
        # 创建演示账单
        create_demo_bills(demo_sites, demo_users)
        
        db.session.commit()
        logger.info("演示数据生成完成")
        
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"演示数据生成失败: {e}")
        return False

def create_demo_users():
    """创建演示用户"""
    users = []
    
    # 检查是否已存在演示用户
    if UserAccess.query.filter_by(email='demo.host@hashinsight.net').first():
        logger.info("演示用户已存在，跳过创建")
        return UserAccess.query.filter(UserAccess.email.like('demo.%@hashinsight.net')).all()
    
    demo_user_data = [
        {
            'email': 'demo.host@hashinsight.net',
            'name': '演示托管方',
            'role': 'mining_site',
            'has_access': True
        },
        {
            'email': 'demo.client1@hashinsight.net', 
            'name': '演示客户A',
            'role': 'client',
            'has_access': True
        },
        {
            'email': 'demo.client2@hashinsight.net',
            'name': '演示客户B', 
            'role': 'client',
            'has_access': True
        }
    ]
    
    for user_data in demo_user_data:
        user = UserAccess(
            email=user_data['email'],
            role=user_data['role']
        )
        db.session.add(user)
        users.append(user)
        logger.info(f"创建演示用户: {user_data['email']}")
    
    return users

def create_miner_models():
    """创建矿机型号"""
    models = []
    
    if MinerModel.query.first():
        logger.info("矿机型号已存在，跳过创建")
        return MinerModel.query.all()
    
    miner_model_data = [
        {
            'manufacturer': 'Bitmain',
            'model_name': 'Antminer S21',
            'algorithm': 'SHA-256',
            'rated_hashrate': 200.0,  # TH/s
            'rated_power': 3550,      # W
            'efficiency': 17.75       # J/TH
        },
        {
            'manufacturer': 'Bitmain', 
            'model_name': 'Antminer S19j Pro',
            'algorithm': 'SHA-256',
            'rated_hashrate': 104.0,
            'rated_power': 3068,
            'efficiency': 29.5
        },
        {
            'manufacturer': 'MicroBT',
            'model_name': 'Whatsminer M50S',
            'algorithm': 'SHA-256', 
            'rated_hashrate': 126.0,
            'rated_power': 3276,
            'efficiency': 26.0
        }
    ]
    
    for model_data in miner_model_data:
        model = MinerModel(**model_data)
        db.session.add(model)
        models.append(model)
        logger.info(f"创建矿机型号: {model_data['model_name']}")
    
    return models

def create_demo_sites():
    """创建演示站点"""
    sites = []
    
    if HostingSite.query.first():
        logger.info("演示站点已存在，跳过创建")
        return HostingSite.query.all()
    
    site_data = [
        {
            'name': 'HashInsight 德州数据中心',
            'slug': 'texas-dc-01',
            'location': '德克萨斯州奥斯汀',
            'operator_name': 'HashInsight Mining LLC',
            'capacity_mw': 50.0,
            'used_capacity_mw': 32.5,
            'electricity_rate': 0.045,  # $0.045/kWh
            'status': 'online',
            'description': '50MW大型挖矿设施，配备先进冷却系统'
        },
        {
            'name': 'HashInsight 蒙大拿矿场',
            'slug': 'montana-mine-01', 
            'location': '蒙大拿州大瀑布',
            'operator_name': 'BigSky Mining Corp',
            'capacity_mw': 25.0,
            'used_capacity_mw': 18.7,
            'electricity_rate': 0.038,
            'status': 'online',
            'description': '绿色能源驱动，水电站直供'
        }
    ]
    
    for site_info in site_data:
        # 计算利用率
        site_info['utilization_rate'] = round(
            (site_info['used_capacity_mw'] / site_info['capacity_mw']) * 100, 1
        )
        
        site = HostingSite(**site_info)
        db.session.add(site)
        sites.append(site)
        logger.info(f"创建演示站点: {site_info['name']}")
    
    return sites

def create_demo_miners(sites, users, models):
    """创建演示矿机"""
    miners = []
    
    if HostingMiner.query.first():
        logger.info("演示矿机已存在，跳过创建")
        return HostingMiner.query.all()
    
    # 每个站点创建矿机
    for site in sites:
        for i in range(10):  # 每站点10台矿机
            model = random.choice(models)
            customer = random.choice([u for u in users if u.role == 'client'])
            
            # 添加一些随机变动
            actual_hashrate = model.rated_hashrate * random.uniform(0.95, 1.05)
            actual_power = model.rated_power * random.uniform(0.98, 1.02)
            
            miner = HostingMiner(
                serial_number=f"{site.slug.upper()}-{model.model_name.replace(' ', '')}-{i+1:03d}",
                customer_id=customer.id,
                site_id=site.id,
                miner_model_id=model.id,
                status=random.choice(['active', 'active', 'active', 'offline']),  # 大部分在线
                location=f"机架-{i//2 + 1}-位置-{i%2 + 1}",
                rated_hashrate=model.rated_hashrate,
                rated_power=model.rated_power,
                actual_hashrate=actual_hashrate,
                actual_power=actual_power,
                deployed_at=datetime.now() - timedelta(days=random.randint(30, 180))
            )
            
            db.session.add(miner)
            miners.append(miner)
    
    logger.info(f"创建了 {len(miners)} 台演示矿机")
    return miners

def create_telemetry_data(miners):
    """生成近7天的遥测数据"""
    if MinerTelemetry.query.first():
        logger.info("遥测数据已存在，跳过创建")
        return
    
    now = datetime.now()
    
    for miner in miners:
        if miner.status != 'active':
            continue
            
        # 生成7天的数据，每小时一个点
        for day in range(7):
            for hour in range(24):
                timestamp = now - timedelta(days=day, hours=hour)
                
                # 模拟正常变动
                base_hashrate = miner.actual_hashrate
                hashrate_variation = random.uniform(0.95, 1.05)
                
                base_power = miner.actual_power
                power_variation = random.uniform(0.98, 1.02)
                
                telemetry = MinerTelemetry(
                    miner_id=miner.id,
                    hashrate=base_hashrate * hashrate_variation,
                    power_consumption=base_power * power_variation,
                    temperature=random.uniform(65, 85),  # 摄氏度
                    fan_speed=random.uniform(3000, 6000),  # RPM
                    recorded_at=timestamp
                )
                
                db.session.add(telemetry)
    
    logger.info("创建了7天的遥测数据")

def create_demo_incidents(sites):
    """创建演示事件和公告"""
    if HostingIncident.query.first():
        logger.info("演示事件已存在，跳过创建")
        return
    
    now = datetime.now()
    
    # 为每个站点创建一些历史事件
    incident_templates = [
        {
            'title': '计划维护通知',
            'description': '将于本周末进行电力系统升级维护，预计影响时间2小时',
            'severity': 'medium',
            'status': 'resolved'
        },
        {
            'title': '冷却系统优化完成',
            'description': '新增冗余冷却设备安装完成，设施可靠性进一步提升',
            'severity': 'low',
            'status': 'resolved'
        }
    ]
    
    for site in sites:
        for template in incident_templates:
            incident = HostingIncident(
                site_id=site.id,
                title=template['title'],
                description=template['description'],
                severity=template['severity'],
                status=template['status'],
                created_at=now - timedelta(days=random.randint(1, 5)),
                resolved_at=now - timedelta(hours=random.randint(1, 24))
            )
            db.session.add(incident)
    
    logger.info("创建了演示事件和公告")

def create_demo_tickets(sites, users):
    """创建演示工单"""
    if HostingTicket.query.first():
        logger.info("演示工单已存在，跳过创建") 
        return
    
    now = datetime.now()
    clients = [u for u in users if u.role == 'client']
    
    ticket_templates = [
        {
            'title': '矿机掉线问题',
            'description': '设备序列号 TX-S21-005 从昨天开始无法连接',
            'priority': 'high',
            'category': 'hardware'
        },
        {
            'title': '算力下降咨询',
            'description': '近期算力有所下降，希望了解具体原因',
            'priority': 'medium', 
            'category': 'performance'
        }
    ]
    
    for i, site in enumerate(sites):
        template = ticket_templates[i % len(ticket_templates)]
        customer = random.choice(clients)
        
        # 模拟SLA时间
        created_time = now - timedelta(hours=random.randint(1, 48))
        first_response_time = created_time + timedelta(minutes=random.randint(5, 30))
        
        ticket = HostingTicket(
            customer_id=customer.id,
            site_id=site.id,
            title=template['title'],
            description=template['description'],
            priority=template['priority'],
            category=template['category'],
            status='resolved',
            created_at=created_time,
            first_response_at=first_response_time,
            resolved_at=now - timedelta(hours=1),
            response_time_minutes=int((first_response_time - created_time).total_seconds() / 60),
            resolution_time_hours=int((now - created_time).total_seconds() / 3600)
        )
        
        db.session.add(ticket)
    
    logger.info("创建了演示工单")

def create_demo_bills(sites, users):
    """创建演示账单（仅用于展示，不涉及实际支付）"""
    if HostingBill.query.first():
        logger.info("演示账单已存在，跳过创建")
        return
    
    now = datetime.now()
    clients = [u for u in users if u.role == 'client']
    
    for site in sites:
        for client in clients:
            # 创建上月账单
            period_start = (now - timedelta(days=30)).date()
            period_end = (now - timedelta(days=1)).date()
            
            bill = HostingBill(
                bill_number=f"DEMO-{now.strftime('%Y%m')}-{client.id:04d}-{site.id:02d}",
                customer_id=client.id,
                site_id=site.id,
                billing_period_start=period_start,
                billing_period_end=period_end,
                electricity_cost=random.uniform(800, 1200),
                hosting_fee=random.uniform(200, 300),
                maintenance_cost=random.uniform(50, 100),
                total_amount=0,  # 会在下面计算
                status='paid',
                due_date=(now + timedelta(days=30)).date()
            )
            
            # 计算总金额
            bill.total_amount = bill.electricity_cost + bill.hosting_fee + bill.maintenance_cost
            
            db.session.add(bill)
    
    logger.info("创建了演示账单（仅展示用途）")