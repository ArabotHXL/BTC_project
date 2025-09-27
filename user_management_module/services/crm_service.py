"""
CRM Service
CRM服务 - 客户关系管理相关的业务逻辑
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import func
try:
    from ..models import Customer, Contact, Lead, Deal, Activity, UserAccess
    from ..database import db
except ImportError:
    from models import Customer, Contact, Lead, Deal, Activity, UserAccess
    from database import db

logger = logging.getLogger(__name__)

class CRMService:
    """CRM服务类"""
    
    @staticmethod
    def create_customer(name, company=None, email=None, phone=None, address=None,
                       customer_type='企业', tags=None, notes=None, created_by_id=None):
        """创建客户"""
        try:
            customer = Customer(
                name=name,
                company=company,
                email=email.lower().strip() if email else None,
                phone=phone,
                address=address,
                customer_type=customer_type,
                tags=tags,
                notes=notes,
                created_by_id=created_by_id
            )
            
            db.session.add(customer)
            db.session.commit()
            
            logger.info(f"成功创建客户: {name}")
            return customer
            
        except Exception as e:
            logger.error(f"创建客户失败: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def update_customer(customer_id, **kwargs):
        """更新客户信息"""
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                logger.warning(f"更新客户失败: 客户ID {customer_id} 不存在")
                return None
            
            # 更新可修改的字段
            updatable_fields = [
                'name', 'company', 'email', 'phone', 'address',
                'customer_type', 'tags', 'notes'
            ]
            
            for field, value in kwargs.items():
                if field in updatable_fields and hasattr(customer, field):
                    if field == 'email' and value:
                        value = value.lower().strip()
                    setattr(customer, field, value)
            
            customer.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"成功更新客户: {customer.name}")
            return customer
            
        except Exception as e:
            logger.error(f"更新客户失败: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def delete_customer(customer_id):
        """删除客户"""
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                logger.warning(f"删除客户失败: 客户ID {customer_id} 不存在")
                return False
            
            name = customer.name
            db.session.delete(customer)
            db.session.commit()
            
            logger.info(f"成功删除客户: {name}")
            return True
            
        except Exception as e:
            logger.error(f"删除客户失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def create_contact(customer_id, name, position=None, email=None, phone=None,
                      notes=None, created_by_id=None):
        """创建联系人"""
        try:
            contact = Contact(
                customer_id=customer_id,
                name=name,
                position=position,
                email=email.lower().strip() if email else None,
                phone=phone,
                notes=notes,
                created_by_id=created_by_id
            )
            
            db.session.add(contact)
            db.session.commit()
            
            logger.info(f"成功创建联系人: {name}")
            return contact
            
        except Exception as e:
            logger.error(f"创建联系人失败: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def create_lead(title, description=None, customer_id=None, source=None,
                   estimated_value=None, assigned_to_id=None, created_by_id=None):
        """创建线索"""
        try:
            lead = Lead(
                title=title,
                description=description,
                customer_id=customer_id,
                source=source,
                estimated_value=float(estimated_value) if estimated_value else None,
                assigned_to_id=assigned_to_id,
                created_by_id=created_by_id
            )
            
            db.session.add(lead)
            db.session.commit()
            
            logger.info(f"成功创建线索: {title}")
            return lead
            
        except Exception as e:
            logger.error(f"创建线索失败: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def update_lead_status(lead_id, status, notes=None):
        """更新线索状态"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                logger.warning(f"更新线索状态失败: 线索ID {lead_id} 不存在")
                return False
            
            lead.status = status
            lead.updated_at = datetime.utcnow()
            
            # 记录状态变更活动
            if notes:
                CRMService.create_activity(
                    customer_id=lead.customer_id,
                    activity_type='状态更新',
                    title=f'线索状态更新为: {status.value}',
                    description=notes,
                    lead_id=lead_id
                )
            
            db.session.commit()
            
            logger.info(f"成功更新线索 {lead.title} 状态为: {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新线索状态失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def create_deal(customer_id, title, amount, description=None, currency='USD',
                   assigned_to_id=None, created_by_id=None):
        """创建交易"""
        try:
            deal = Deal(
                customer_id=customer_id,
                title=title,
                amount=float(amount),
                description=description,
                currency=currency,
                assigned_to_id=assigned_to_id,
                created_by_id=created_by_id
            )
            
            db.session.add(deal)
            db.session.commit()
            
            logger.info(f"成功创建交易: {title}")
            return deal
            
        except Exception as e:
            logger.error(f"创建交易失败: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def update_deal_status(deal_id, status, notes=None):
        """更新交易状态"""
        try:
            deal = Deal.query.get(deal_id)
            if not deal:
                logger.warning(f"更新交易状态失败: 交易ID {deal_id} 不存在")
                return False
            
            deal.status = status
            deal.updated_at = datetime.utcnow()
            
            # 如果交易完成，设置实际关闭日期
            if status.value in ['已完成', '已取消']:
                deal.actual_close_date = datetime.utcnow().date()
            
            # 记录状态变更活动
            if notes:
                CRMService.create_activity(
                    customer_id=deal.customer_id,
                    activity_type='状态更新',
                    title=f'交易状态更新为: {status.value}',
                    description=notes,
                    deal_id=deal_id
                )
            
            db.session.commit()
            
            logger.info(f"成功更新交易 {deal.title} 状态为: {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新交易状态失败: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def create_activity(customer_id, activity_type, title, description=None,
                       lead_id=None, deal_id=None, performed_by_id=None):
        """创建活动记录"""
        try:
            activity = Activity(
                customer_id=customer_id,
                activity_type=activity_type,
                title=title,
                description=description,
                lead_id=lead_id,
                deal_id=deal_id,
                performed_by_id=performed_by_id
            )
            
            db.session.add(activity)
            db.session.commit()
            
            logger.info(f"成功创建活动记录: {title}")
            return activity
            
        except Exception as e:
            logger.error(f"创建活动记录失败: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_customer_by_id(customer_id):
        """根据ID获取客户"""
        try:
            return Customer.query.get(customer_id)
        except Exception as e:
            logger.error(f"获取客户失败: {str(e)}")
            return None
    
    @staticmethod
    def search_customers(search_term, page=1, per_page=20):
        """搜索客户"""
        try:
            search_pattern = f"%{search_term}%"
            return Customer.query.filter(
                (Customer.name.like(search_pattern)) |
                (Customer.company.like(search_pattern)) |
                (Customer.email.like(search_pattern))
            ).paginate(page=page, per_page=per_page, error_out=False)
        except Exception as e:
            logger.error(f"搜索客户失败: {str(e)}")
            return None
    
    @staticmethod
    def get_customer_activities(customer_id, page=1, per_page=20):
        """获取客户活动记录"""
        try:
            return Activity.query.filter_by(customer_id=customer_id).order_by(
                Activity.created_at.desc()
            ).paginate(page=page, per_page=per_page, error_out=False)
        except Exception as e:
            logger.error(f"获取客户活动记录失败: {str(e)}")
            return None
    
    @staticmethod
    def get_dashboard_stats():
        """获取CRM仪表盘统计"""
        try:
            # 基本统计
            total_customers = Customer.query.count()
            total_leads = Lead.query.count()
            total_deals = Deal.query.count()
            
            # 本月新增
            current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            new_customers_this_month = Customer.query.filter(
                Customer.created_at >= current_month
            ).count()
            new_leads_this_month = Lead.query.filter(
                Lead.created_at >= current_month
            ).count()
            
            # 线索状态分布
            lead_status_stats = {}
            from ..models import LeadStatus
            for status in LeadStatus:
                count = Lead.query.filter_by(status=status).count()
                lead_status_stats[status.value] = count
            
            # 交易状态分布
            deal_status_stats = {}
            from ..models import DealStatus
            for status in DealStatus:
                count = Deal.query.filter_by(status=status).count()
                deal_status_stats[status.value] = count
            
            # 交易金额统计
            total_deal_value = db.session.query(func.sum(Deal.amount)).scalar() or 0
            completed_deals_value = db.session.query(func.sum(Deal.amount)).filter(
                Deal.status == DealStatus.COMPLETED
            ).scalar() or 0
            
            # 最近活动
            recent_activities = Activity.query.order_by(
                Activity.created_at.desc()
            ).limit(10).all()
            
            return {
                'total_customers': total_customers,
                'total_leads': total_leads,
                'total_deals': total_deals,
                'new_customers_this_month': new_customers_this_month,
                'new_leads_this_month': new_leads_this_month,
                'lead_status_stats': lead_status_stats,
                'deal_status_stats': deal_status_stats,
                'total_deal_value': float(total_deal_value),
                'completed_deals_value': float(completed_deals_value),
                'recent_activities': [activity.to_dict() for activity in recent_activities]
            }
            
        except Exception as e:
            logger.error(f"获取CRM仪表盘统计失败: {str(e)}")
            return {}
    
    @staticmethod
    def get_sales_pipeline():
        """获取销售漏斗数据"""
        try:
            from ..models import LeadStatus, DealStatus
            
            pipeline = {
                'leads_by_status': {},
                'deals_by_status': {},
                'conversion_rates': {}
            }
            
            # 线索漏斗
            for status in LeadStatus:
                count = Lead.query.filter_by(status=status).count()
                pipeline['leads_by_status'][status.value] = count
            
            # 交易漏斗
            for status in DealStatus:
                count = Deal.query.filter_by(status=status).count()
                value = db.session.query(func.sum(Deal.amount)).filter_by(status=status).scalar() or 0
                pipeline['deals_by_status'][status.value] = {
                    'count': count,
                    'value': float(value)
                }
            
            # 转化率计算
            total_leads = Lead.query.count()
            won_leads = Lead.query.filter_by(status=LeadStatus.WON).count()
            if total_leads > 0:
                pipeline['conversion_rates']['lead_to_won'] = (won_leads / total_leads) * 100
            
            return pipeline
            
        except Exception as e:
            logger.error(f"获取销售漏斗数据失败: {str(e)}")
            return {}
    
    @staticmethod
    def get_customer_value_analysis():
        """获取客户价值分析"""
        try:
            # 客户交易价值排序
            customer_values = db.session.query(
                Customer.id,
                Customer.name,
                Customer.company,
                func.sum(Deal.amount).label('total_value'),
                func.count(Deal.id).label('deal_count')
            ).outerjoin(Deal).group_by(Customer.id).order_by(
                func.sum(Deal.amount).desc()
            ).limit(20).all()
            
            top_customers = []
            for customer_value in customer_values:
                top_customers.append({
                    'id': customer_value.id,
                    'name': customer_value.name,
                    'company': customer_value.company,
                    'total_value': float(customer_value.total_value or 0),
                    'deal_count': customer_value.deal_count
                })
            
            return {
                'top_customers': top_customers
            }
            
        except Exception as e:
            logger.error(f"获取客户价值分析失败: {str(e)}")
            return {}
    
    @staticmethod
    def get_activity_summary(days=30):
        """获取活动摘要"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            activities = Activity.query.filter(
                Activity.created_at >= start_date
            ).all()
            
            # 按类型统计
            activity_types = {}
            for activity in activities:
                activity_type = activity.activity_type
                if activity_type not in activity_types:
                    activity_types[activity_type] = 0
                activity_types[activity_type] += 1
            
            # 按日期统计
            daily_activities = {}
            for activity in activities:
                date_key = activity.created_at.strftime('%Y-%m-%d')
                if date_key not in daily_activities:
                    daily_activities[date_key] = 0
                daily_activities[date_key] += 1
            
            return {
                'total_activities': len(activities),
                'activity_types': activity_types,
                'daily_activities': daily_activities
            }
            
        except Exception as e:
            logger.error(f"获取活动摘要失败: {str(e)}")
            return {}