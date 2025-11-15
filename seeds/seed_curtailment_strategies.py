"""
限电策略种子数据脚本
Curtailment Strategies Seed Data Script

为HashPower MegaFarm (site_id=5) 创建默认限电策略
Creates default curtailment strategies for HashPower MegaFarm (site_id=5)

Usage:
    python seeds/seed_curtailment_strategies.py
    
或者从Python代码调用:
    from seeds.seed_curtailment_strategies import seed_megafarm_strategies
    seed_megafarm_strategies()
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, app
from models import CurtailmentStrategy, StrategyType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_megafarm_strategies(site_id=5, force=False):
    """
    为HashPower MegaFarm创建默认限电策略
    Create default curtailment strategies for HashPower MegaFarm
    
    Args:
        site_id: 站点ID (默认为5, HashPower MegaFarm)
        force: 是否强制重新创建 (默认False，会跳过已存在的策略)
    
    Returns:
        int: 创建的策略数量
    """
    try:
        existing_count = CurtailmentStrategy.query.filter_by(site_id=site_id).count()
        
        if existing_count > 0 and not force:
            logger.info(f"⏭️  Site {site_id} 已有 {existing_count} 个策略，跳过创建")
            logger.info(f"   如需强制重新创建，请使用 force=True 参数")
            return 0
        
        if force and existing_count > 0:
            logger.warning(f"🗑️  强制模式: 删除现有的 {existing_count} 个策略")
            CurtailmentStrategy.query.filter_by(site_id=site_id).delete()
            db.session.commit()
        
        strategies = [
            {
                'site_id': site_id,
                'name': 'Performance Priority - MegaFarm',
                'strategy_type': StrategyType.PERFORMANCE_PRIORITY,
                'performance_weight': 0.70,
                'power_efficiency_weight': 0.20,
                'uptime_weight': 0.10,
                'vip_customer_protection': False,
                'min_uptime_threshold': 0.80,
                'is_active': True
            },
            {
                'site_id': site_id,
                'name': 'Customer Priority - MegaFarm',
                'strategy_type': StrategyType.CUSTOMER_PRIORITY,
                'performance_weight': 0.40,
                'power_efficiency_weight': 0.20,
                'uptime_weight': 0.40,
                'vip_customer_protection': True,
                'min_uptime_threshold': 0.85,
                'is_active': True
            },
            {
                'site_id': site_id,
                'name': 'Fair Distribution - MegaFarm',
                'strategy_type': StrategyType.FAIR_DISTRIBUTION,
                'performance_weight': 0.33,
                'power_efficiency_weight': 0.33,
                'uptime_weight': 0.34,
                'vip_customer_protection': False,
                'min_uptime_threshold': 0.75,
                'is_active': True
            },
            {
                'site_id': site_id,
                'name': 'Custom Rules - MegaFarm',
                'strategy_type': StrategyType.CUSTOM,
                'performance_weight': 0.50,
                'power_efficiency_weight': 0.30,
                'uptime_weight': 0.20,
                'vip_customer_protection': False,
                'min_uptime_threshold': 0.80,
                'is_active': True
            }
        ]
        
        logger.info(f"📝 开始创建 {len(strategies)} 个限电策略...")
        
        created_strategies = []
        for s_data in strategies:
            strategy = CurtailmentStrategy(**s_data)
            db.session.add(strategy)
            created_strategies.append(strategy)
            logger.info(f"   ✓ {s_data['name']} ({s_data['strategy_type'].value})")
        
        db.session.commit()
        
        logger.info(f"✅ 成功为site {site_id} 创建 {len(strategies)} 个限电策略")
        
        logger.info(f"\n📊 策略详情:")
        for strategy in created_strategies:
            logger.info(f"   ID: {strategy.id}")
            logger.info(f"   名称: {strategy.name}")
            logger.info(f"   类型: {strategy.strategy_type.value}")
            logger.info(f"   权重: 性能={strategy.performance_weight}, "
                       f"能效={strategy.power_efficiency_weight}, "
                       f"运行时间={strategy.uptime_weight}")
            logger.info(f"   VIP保护: {strategy.vip_customer_protection}")
            logger.info(f"   最低在线阈值: {strategy.min_uptime_threshold}")
            logger.info(f"   ---")
        
        return len(strategies)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ 创建策略失败: {e}")
        import traceback
        traceback.print_exc()
        return 0


def verify_strategies(site_id=5):
    """
    验证限电策略是否正确创建
    Verify that curtailment strategies were created correctly
    
    Args:
        site_id: 站点ID
    
    Returns:
        bool: 验证是否通过
    """
    try:
        strategies = CurtailmentStrategy.query.filter_by(site_id=site_id).all()
        
        if len(strategies) == 0:
            logger.error(f"❌ 验证失败: Site {site_id} 没有找到任何策略")
            return False
        
        logger.info(f"\n🔍 验证结果:")
        logger.info(f"   站点ID: {site_id}")
        logger.info(f"   策略数量: {len(strategies)}")
        
        expected_types = {
            StrategyType.PERFORMANCE_PRIORITY,
            StrategyType.CUSTOMER_PRIORITY,
            StrategyType.FAIR_DISTRIBUTION,
            StrategyType.CUSTOM
        }
        
        actual_types = {s.strategy_type for s in strategies}
        
        if actual_types == expected_types:
            logger.info(f"   ✅ 所有策略类型完整")
        else:
            missing = expected_types - actual_types
            extra = actual_types - expected_types
            if missing:
                logger.warning(f"   ⚠️  缺少策略类型: {missing}")
            if extra:
                logger.warning(f"   ⚠️  额外策略类型: {extra}")
        
        active_count = sum(1 for s in strategies if s.is_active)
        logger.info(f"   活跃策略: {active_count}/{len(strategies)}")
        
        for strategy in strategies:
            total_weight = (
                float(strategy.performance_weight) +
                float(strategy.power_efficiency_weight) +
                float(strategy.uptime_weight)
            )
            
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(f"   ⚠️  策略 '{strategy.name}' 权重总和不是1.0: {total_weight}")
            else:
                logger.info(f"   ✓ 策略 '{strategy.name}' 权重配置正确")
        
        logger.info(f"✅ 验证完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 验证过程出错: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='为HashPower MegaFarm创建限电策略种子数据'
    )
    parser.add_argument(
        '--site-id',
        type=int,
        default=5,
        help='站点ID (默认: 5 - HashPower MegaFarm)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新创建（删除现有策略）'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='仅验证现有策略，不创建新策略'
    )
    
    args = parser.parse_args()
    
    with app.app_context():
        if args.verify_only:
            logger.info("🔍 验证模式: 仅检查现有策略")
            verify_strategies(args.site_id)
        else:
            logger.info(f"🚀 开始为site_id={args.site_id} 创建限电策略种子数据")
            logger.info(f"   强制模式: {'是' if args.force else '否'}")
            logger.info("")
            
            created_count = seed_megafarm_strategies(
                site_id=args.site_id,
                force=args.force
            )
            
            if created_count > 0:
                logger.info("")
                verify_strategies(args.site_id)
