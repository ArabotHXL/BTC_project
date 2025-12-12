"""
CRM-Hosting Integration Service
通过 email 关联 CRM Customer 与 Hosting UserMiner 数据
"""
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy import func

logger = logging.getLogger(__name__)


class CRMHostingIntegrationService:
    """CRM与Hosting模块集成服务"""
    
    def __init__(self):
        self.btc_price = 95000  # 默认BTC价格，会被实时更新
        self.network_difficulty = 100e12  # 默认网络难度
    
    def get_linked_user_access(self, customer) -> Optional[Any]:
        """
        通过email查找与Customer关联的UserAccess账户
        
        Args:
            customer: CRM Customer对象
            
        Returns:
            UserAccess对象或None
        """
        from models import UserAccess
        
        if not customer or not customer.email:
            return None
        
        try:
            user_access = UserAccess.query.filter(
                func.lower(UserAccess.email) == func.lower(customer.email)
            ).first()
            return user_access
        except Exception as e:
            logger.error(f"查找关联UserAccess失败: {e}")
            return None
    
    def get_customer_hosting_stats(self, customer_id: int) -> Dict[str, Any]:
        """
        获取客户的托管统计数据
        
        Args:
            customer_id: CRM客户ID
            
        Returns:
            包含矿机统计的字典
        """
        from models import Customer, UserAccess, UserMiner, MinerModel
        from app import db
        
        result = {
            'has_hosting': False,
            'user_access_id': None,
            'miners_count': 0,
            'total_hashrate': 0.0,  # TH/s
            'total_power': 0,  # W
            'total_power_mw': 0.0,  # MW
            'active_miners': 0,
            'offline_miners': 0,
            'maintenance_miners': 0,
            'estimated_daily_btc': 0.0,
            'estimated_daily_usd': 0.0,
            'avg_efficiency': 0.0,  # W/TH
            'miners': [],
            'by_model': {},
            'by_status': {},
            'electricity_cost_daily': 0.0,
            'net_profit_daily': 0.0,
        }
        
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                logger.warning(f"Customer {customer_id} not found")
                return result
            
            user_access = self.get_linked_user_access(customer)
            if not user_access:
                logger.info(f"Customer {customer_id} ({customer.email}) has no linked UserAccess")
                return result
            
            result['has_hosting'] = True
            result['user_access_id'] = user_access.id
            
            miners = UserMiner.query.filter_by(user_id=user_access.id).all()
            
            if not miners:
                return result
            
            total_hashrate = 0.0
            total_power = 0
            active_count = 0
            offline_count = 0
            maintenance_count = 0
            total_electricity_cost = 0.0
            by_model = {}
            by_status = {'active': 0, 'offline': 0, 'maintenance': 0, 'sold': 0}
            miners_data = []
            
            for miner in miners:
                qty = miner.quantity or 1
                hashrate = (miner.actual_hashrate or 0) * qty
                power = (miner.actual_power or 0) * qty
                
                total_hashrate += hashrate
                total_power += power
                
                status = miner.status or 'active'
                if status == 'active':
                    active_count += qty
                elif status == 'offline':
                    offline_count += qty
                elif status == 'maintenance':
                    maintenance_count += qty
                
                by_status[status] = by_status.get(status, 0) + qty
                
                model_name = miner.miner_model.model_name if miner.miner_model else 'Unknown'
                if model_name not in by_model:
                    by_model[model_name] = {'count': 0, 'hashrate': 0, 'power': 0}
                by_model[model_name]['count'] += qty
                by_model[model_name]['hashrate'] += hashrate
                by_model[model_name]['power'] += power
                
                elec_cost = miner.electricity_cost or 0.05
                daily_kwh = (power / 1000) * 24
                daily_elec_cost = daily_kwh * elec_cost
                total_electricity_cost += daily_elec_cost
                
                miners_data.append({
                    'id': miner.id,
                    'name': miner.custom_name or model_name,
                    'model': model_name,
                    'quantity': qty,
                    'hashrate': miner.actual_hashrate,
                    'total_hashrate': hashrate,
                    'power': miner.actual_power,
                    'total_power': power,
                    'status': status,
                    'location': miner.location,
                    'electricity_cost': elec_cost,
                    'daily_electricity_cost': round(daily_elec_cost, 2),
                })
            
            self._update_market_data()
            daily_btc = self._calculate_daily_btc(total_hashrate)
            daily_usd = daily_btc * self.btc_price
            
            avg_efficiency = (total_power / total_hashrate) if total_hashrate > 0 else 0
            
            result.update({
                'miners_count': sum(m.quantity or 1 for m in miners),
                'total_hashrate': round(total_hashrate, 2),
                'total_power': total_power,
                'total_power_mw': round(total_power / 1_000_000, 3),
                'active_miners': active_count,
                'offline_miners': offline_count,
                'maintenance_miners': maintenance_count,
                'estimated_daily_btc': round(daily_btc, 8),
                'estimated_daily_usd': round(daily_usd, 2),
                'avg_efficiency': round(avg_efficiency, 2),
                'miners': miners_data,
                'by_model': by_model,
                'by_status': by_status,
                'electricity_cost_daily': round(total_electricity_cost, 2),
                'net_profit_daily': round(daily_usd - total_electricity_cost, 2),
                'btc_price': self.btc_price,
            })
            
            return result
            
        except Exception as e:
            logger.error(f"获取客户托管统计失败: {e}", exc_info=True)
            return result
    
    def _update_market_data(self):
        """更新市场数据（BTC价格、网络难度）"""
        try:
            from services.bitcoin_data_service import BitcoinDataService
            btc_service = BitcoinDataService()
            data = btc_service.get_current_data()
            if data:
                self.btc_price = data.get('btc_price', 95000)
                self.network_difficulty = data.get('difficulty', 100e12)
        except Exception as e:
            logger.debug(f"更新市场数据失败，使用默认值: {e}")
    
    def _calculate_daily_btc(self, hashrate_th: float) -> float:
        """
        计算日均BTC产出
        
        Args:
            hashrate_th: 总算力 (TH/s)
            
        Returns:
            日均BTC产出
        """
        if hashrate_th <= 0:
            return 0.0
        
        hashrate_h = hashrate_th * 1e12
        block_reward = 3.125
        blocks_per_day = 144
        network_hashrate = self.network_difficulty * 2**32 / 600
        
        if network_hashrate <= 0:
            return 0.0
        
        daily_btc = (hashrate_h / network_hashrate) * block_reward * blocks_per_day
        return daily_btc
    
    def sync_customer_from_hosting(self, customer_id: int) -> bool:
        """
        从Hosting数据同步更新Customer的矿机统计字段
        
        Args:
            customer_id: CRM客户ID
            
        Returns:
            是否同步成功
        """
        from models import Customer
        from app import db
        
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                return False
            
            stats = self.get_customer_hosting_stats(customer_id)
            
            if stats['has_hosting']:
                customer.miners_count = stats['miners_count']
                customer.mining_capacity = stats['total_power_mw']
                
                if stats['by_model']:
                    primary_model = max(stats['by_model'].items(), key=lambda x: x[1]['count'])
                    customer.primary_miner_model = primary_model[0]
                
                db.session.commit()
                logger.info(f"已同步Customer {customer_id} 的托管数据: {stats['miners_count']}台矿机, {stats['total_power_mw']}MW")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"同步客户托管数据失败: {e}")
            db.session.rollback()
            return False
    
    def sync_all_customers(self) -> Dict[str, int]:
        """
        同步所有客户的托管数据
        
        Returns:
            同步结果统计
        """
        from models import Customer
        
        results = {'total': 0, 'synced': 0, 'no_hosting': 0, 'errors': 0}
        
        try:
            customers = Customer.query.filter(Customer.email.isnot(None)).all()
            results['total'] = len(customers)
            
            for customer in customers:
                try:
                    if self.sync_customer_from_hosting(customer.id):
                        results['synced'] += 1
                    else:
                        results['no_hosting'] += 1
                except Exception as e:
                    logger.error(f"同步Customer {customer.id} 失败: {e}")
                    results['errors'] += 1
            
            logger.info(f"批量同步完成: {results}")
            return results
            
        except Exception as e:
            logger.error(f"批量同步失败: {e}")
            return results
    
    def get_customer_miners_list(self, customer_id: int, status: str = None) -> List[Dict]:
        """
        获取客户的矿机列表
        
        Args:
            customer_id: CRM客户ID
            status: 可选的状态过滤 (active/offline/maintenance/sold)
            
        Returns:
            矿机列表
        """
        from models import Customer, UserMiner
        
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                return []
            
            user_access = self.get_linked_user_access(customer)
            if not user_access:
                return []
            
            query = UserMiner.query.filter_by(user_id=user_access.id)
            if status:
                query = query.filter_by(status=status)
            
            miners = query.order_by(UserMiner.created_at.desc()).all()
            
            return [miner.to_dict() for miner in miners]
            
        except Exception as e:
            logger.error(f"获取客户矿机列表失败: {e}")
            return []
    
    def link_customer_to_user_access(self, customer_id: int, user_access_id: int) -> bool:
        """
        手动关联Customer与UserAccess（当email不匹配时）
        
        Args:
            customer_id: CRM客户ID
            user_access_id: UserAccess账户ID
            
        Returns:
            是否关联成功
        """
        from models import Customer, UserAccess
        from app import db
        
        try:
            customer = Customer.query.get(customer_id)
            user_access = UserAccess.query.get(user_access_id)
            
            if not customer or not user_access:
                return False
            
            customer.email = user_access.email
            db.session.commit()
            
            self.sync_customer_from_hosting(customer_id)
            
            logger.info(f"已关联Customer {customer_id} 与 UserAccess {user_access_id}")
            return True
            
        except Exception as e:
            logger.error(f"关联失败: {e}")
            db.session.rollback()
            return False


    def get_sync_status(self) -> Dict[str, Any]:
        """
        获取CRM-Hosting同步状态
        
        Returns:
            同步状态信息
        """
        from models import Customer, UserAccess
        from sqlalchemy import func
        
        try:
            total_customers = Customer.query.filter(Customer.email.isnot(None)).count()
            
            linked_count = 0
            if total_customers > 0:
                customer_emails = [c.email.lower() for c in Customer.query.filter(Customer.email.isnot(None)).all() if c.email]
                user_emails = [u.email.lower() for u in UserAccess.query.filter(UserAccess.email.isnot(None)).all() if u.email]
                linked_count = len(set(customer_emails) & set(user_emails))
            
            unlinked = total_customers - linked_count
            link_rate = (linked_count / total_customers * 100) if total_customers > 0 else 0
            
            issues = []
            sync_health = 'healthy'
            
            if link_rate < 10 and total_customers > 5:
                issues.append('Low link rate: fewer than 10% of customers have linked hosting accounts')
                sync_health = 'warning'
            
            if total_customers > 0 and linked_count == 0:
                issues.append('No customers are linked to hosting accounts')
                sync_health = 'critical'
            
            return {
                'total_customers': total_customers,
                'linked_customers': linked_count,
                'unlinked_customers': unlinked,
                'link_rate': round(link_rate, 2),
                'last_sync': None,
                'sync_health': sync_health,
                'issues': issues,
            }
            
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            return {
                'total_customers': 0,
                'linked_customers': 0,
                'unlinked_customers': 0,
                'link_rate': 0,
                'last_sync': None,
                'sync_health': 'error',
                'issues': [str(e)],
            }


crm_hosting_service = CRMHostingIntegrationService()
