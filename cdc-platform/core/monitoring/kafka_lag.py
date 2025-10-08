"""
HashInsight CDC Platform - Kafka Consumer Lag Monitoring
Kafka消费者延迟监控

功能：
1. 监控Kafka消费者组延迟（Consumer Lag）
2. 获取每个分区的offset信息
3. 计算总体延迟和趋势
4. 集成到Health API

Author: HashInsight Team
Version: 1.0.0
"""
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from kafka import KafkaAdminClient  # type: ignore
    from kafka.structs import TopicPartition  # type: ignore
    from kafka.errors import KafkaError  # type: ignore
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("kafka-python not installed, lag monitoring disabled")

logger = logging.getLogger(__name__)

class KafkaLagMonitor:
    """
    Kafka消费者延迟监控器
    
    功能：
    - 获取消费者组的offset信息
    - 计算每个分区的lag
    - 提供总体延迟统计
    """
    
    def __init__(self, bootstrap_servers: Optional[str] = None):
        """
        初始化Kafka延迟监控器
        
        参数:
            bootstrap_servers: Kafka broker地址（默认从环境变量读取）
        """
        if not KAFKA_AVAILABLE:
            logger.warning("⚠️ Kafka monitoring unavailable (kafka-python not installed)")
            self.enabled = False
            return
        
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            'KAFKA_BOOTSTRAP_SERVERS',
            'localhost:9092'
        )
        
        self.enabled = True
        self.admin_client = None
        
        try:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id='hashinsight-lag-monitor'
            )
            logger.info(f"✅ KafkaLagMonitor initialized: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kafka admin client: {e}")
            self.enabled = False
    
    def get_consumer_lag(
        self,
        group_id: str,
        topics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        获取消费者组的延迟信息
        
        参数:
            group_id: 消费者组ID
            topics: 主题列表（可选，不指定则获取所有）
        
        返回:
            延迟信息字典
        """
        if not self.enabled or not self.admin_client:
            return {
                'status': 'unavailable',
                'message': 'Kafka monitoring not available'
            }
        
        try:
            from kafka import KafkaConsumer  # type: ignore
            
            # 创建临时consumer获取offset信息
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                enable_auto_commit=False
            )
            
            # 获取消费者组订阅的主题和分区
            if topics:
                topic_partitions = []
                for topic in topics:
                    partitions = consumer.partitions_for_topic(topic)
                    if partitions:
                        topic_partitions.extend([
                            TopicPartition(topic, p) for p in partitions
                        ])
            else:
                # 获取消费者组已提交offset的所有分区
                topic_partitions = list(consumer.committed({}).keys())
            
            if not topic_partitions:
                consumer.close()
                return {
                    'status': 'no_data',
                    'group_id': group_id,
                    'message': 'No topic partitions found for consumer group'
                }
            
            # 获取当前offset（消费者位置）
            committed_offsets = consumer.committed(topic_partitions)
            
            # 获取最新offset（分区末尾位置）
            consumer.assign(topic_partitions)
            end_offsets = consumer.end_offsets(topic_partitions)
            
            # 计算lag
            partition_lags = []
            total_lag = 0
            
            for tp in topic_partitions:
                committed = committed_offsets.get(tp, 0) or 0
                end = end_offsets.get(tp, 0)
                lag = max(0, end - committed)
                
                partition_lags.append({
                    'topic': tp.topic,
                    'partition': tp.partition,
                    'current_offset': committed,
                    'log_end_offset': end,
                    'lag': lag
                })
                
                total_lag += lag
            
            consumer.close()
            
            # 计算平均lag
            avg_lag = total_lag / len(partition_lags) if partition_lags else 0
            
            # 确定健康状态
            status = 'healthy'
            if total_lag > 10000:
                status = 'critical'
            elif total_lag > 1000:
                status = 'warning'
            
            return {
                'status': status,
                'group_id': group_id,
                'total_lag': total_lag,
                'avg_lag': round(avg_lag, 2),
                'partition_count': len(partition_lags),
                'partitions': partition_lags,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get consumer lag: {e}")
            return {
                'status': 'error',
                'group_id': group_id,
                'error': str(e)
            }
    
    def get_all_consumer_groups(self) -> List[str]:
        """
        获取所有消费者组列表
        
        返回:
            消费者组ID列表
        """
        if not self.enabled or not self.admin_client:
            return []
        
        try:
            groups = self.admin_client.list_consumer_groups()
            return [group[0] for group in groups]
        except Exception as e:
            logger.error(f"❌ Failed to list consumer groups: {e}")
            return []
    
    def get_multi_group_lag(
        self,
        group_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        获取多个消费者组的延迟信息
        
        参数:
            group_ids: 消费者组ID列表（不指定则获取所有）
        
        返回:
            多个消费者组的延迟信息
        """
        if not self.enabled:
            return {
                'status': 'unavailable',
                'message': 'Kafka monitoring not available'
            }
        
        # 如果未指定，获取所有消费者组
        if not group_ids:
            group_ids = self.get_all_consumer_groups()
        
        if not group_ids:
            return {
                'status': 'no_groups',
                'message': 'No consumer groups found'
            }
        
        # 获取每个组的lag
        group_lags = {}
        total_lag_all = 0
        
        for group_id in group_ids:
            lag_info = self.get_consumer_lag(group_id)
            group_lags[group_id] = lag_info
            
            if lag_info.get('status') not in ['unavailable', 'error', 'no_data']:
                total_lag_all += lag_info.get('total_lag', 0)
        
        # 确定总体健康状态
        overall_status = 'healthy'
        for lag_info in group_lags.values():
            if lag_info.get('status') == 'critical':
                overall_status = 'critical'
                break
            elif lag_info.get('status') == 'warning' and overall_status != 'critical':
                overall_status = 'warning'
        
        return {
            'status': overall_status,
            'total_lag_all_groups': total_lag_all,
            'group_count': len(group_ids),
            'groups': group_lags,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_topic_info(self, topic: str) -> Dict[str, Any]:
        """
        获取主题信息
        
        参数:
            topic: 主题名称
        
        返回:
            主题信息字典
        """
        if not self.enabled or not self.admin_client:
            return {
                'status': 'unavailable',
                'message': 'Kafka monitoring not available'
            }
        
        try:
            from kafka import KafkaConsumer  # type: ignore
            
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers
            )
            
            partitions = consumer.partitions_for_topic(topic)
            
            if not partitions:
                consumer.close()
                return {
                    'status': 'not_found',
                    'topic': topic,
                    'message': 'Topic not found'
                }
            
            topic_partitions = [TopicPartition(topic, p) for p in partitions]
            end_offsets = consumer.end_offsets(topic_partitions)
            
            partition_info = []
            total_messages = 0
            
            for tp in topic_partitions:
                end = end_offsets.get(tp, 0)
                partition_info.append({
                    'partition': tp.partition,
                    'log_end_offset': end
                })
                total_messages += end
            
            consumer.close()
            
            return {
                'status': 'success',
                'topic': topic,
                'partition_count': len(partitions),
                'total_messages': total_messages,
                'partitions': partition_info
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get topic info: {e}")
            return {
                'status': 'error',
                'topic': topic,
                'error': str(e)
            }
    
    def close(self):
        """关闭Kafka连接"""
        if self.admin_client:
            try:
                self.admin_client.close()
                logger.info("✅ Kafka admin client closed")
            except Exception as e:
                logger.error(f"❌ Error closing Kafka admin client: {e}")

# 全局实例
kafka_lag_monitor = KafkaLagMonitor()

# 便捷函数
def get_consumer_lag_summary() -> Dict[str, Any]:
    """
    获取所有消费者组的延迟摘要
    
    返回:
        延迟摘要字典
    """
    # HashInsight消费者组列表
    consumer_groups = [
        'portfolio-recalc-group',
        'intel-group',
        'ops-group',
        'crm-sync-group'
    ]
    
    return kafka_lag_monitor.get_multi_group_lag(consumer_groups)
