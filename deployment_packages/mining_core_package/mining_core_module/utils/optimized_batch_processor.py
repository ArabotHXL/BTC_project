"""
优化的批量数据处理器
提升数据收集频率和质量
"""

import os
import time
import json
import logging
import requests
import psycopg2
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import schedule
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedBatchProcessor:
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BTC-Mining-Calculator/2.0'
        })
        
        # 数据源配置
        self.data_sources = {
            'coingecko': {
                'url': 'https://api.coingecko.com/api/v3/simple/price',
                'params': {
                    'ids': 'bitcoin',
                    'vs_currencies': 'usd',
                    'include_24hr_vol': 'true',
                    'include_24hr_change': 'true',
                    'include_market_cap': 'true'
                },
                'priority': 1
            },
            'coinbase': {
                'url': 'https://api.coinbase.com/v2/exchange-rates',
                'params': {'currency': 'BTC'},
                'priority': 2
            },
            'blockchain_info': {
                'url': 'https://blockchain.info/ticker',
                'priority': 3
            }
        }
        
        self.collection_stats = {
            'total_collections': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'last_collection': None
        }
    
    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(self.db_url)
    
    def collect_enhanced_price_data(self) -> Optional[Dict]:
        """增强的价格数据收集，多源验证"""
        collected_data = {}
        
        # 并行收集多个数据源
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            
            # CoinGecko主要数据源
            try:
                params = self.data_sources['coingecko']['params']
                futures[executor.submit(self.session.get, 
                                      self.data_sources['coingecko']['url'], 
                                      params=params, timeout=10)] = 'coingecko'
            except Exception as e:
                logger.debug(f"CoinGecko请求提交失败: {e}")
            
            # Blockchain.info备用源
            try:
                futures[executor.submit(self.session.get, 
                                      self.data_sources['blockchain_info']['url'], 
                                      timeout=10)] = 'blockchain_info'
            except Exception as e:
                logger.debug(f"Blockchain.info请求提交失败: {e}")
            
            # 收集结果
            for future in as_completed(futures, timeout=15):
                source = futures[future]
                try:
                    response = future.result()
                    if response.status_code == 200:
                        if source == 'coingecko':
                            data = response.json()
                            if 'bitcoin' in data:
                                btc_data = data['bitcoin']
                                collected_data['coingecko'] = {
                                    'price': btc_data.get('usd', 0),
                                    'volume_24h': btc_data.get('usd_24h_vol', 0),
                                    'price_change_24h': btc_data.get('usd_24h_change', 0),
                                    'market_cap': btc_data.get('usd_market_cap', 0)
                                }
                        
                        elif source == 'blockchain_info':
                            data = response.json()
                            if 'USD' in data:
                                usd_data = data['USD']
                                collected_data['blockchain_info'] = {
                                    'price': usd_data.get('last', 0),
                                    'high': usd_data.get('high', 0),
                                    'low': usd_data.get('low', 0)
                                }
                except Exception as e:
                    logger.debug(f"{source}数据解析失败: {e}")
        
        # 数据验证和聚合
        if collected_data:
            return self.aggregate_price_data(collected_data)
        else:
            logger.warning("所有价格数据源均失败")
            return None
    
    def aggregate_price_data(self, collected_data: Dict) -> Dict:
        """聚合和验证价格数据"""
        aggregated = {
            'sources_count': len(collected_data),
            'data_quality_score': 0,
            'consensus_price': 0,
            'volume_24h': 0,
            'price_change_24h': 0,
            'market_cap': 0
        }
        
        prices = []
        volumes = []
        
        # 提取价格数据
        if 'coingecko' in collected_data:
            cg_data = collected_data['coingecko']
            if cg_data['price'] > 0:
                prices.append(cg_data['price'])
                aggregated['volume_24h'] = cg_data.get('volume_24h', 0)
                aggregated['price_change_24h'] = cg_data.get('price_change_24h', 0)
                aggregated['market_cap'] = cg_data.get('market_cap', 0)
        
        if 'blockchain_info' in collected_data:
            bi_data = collected_data['blockchain_info']
            if bi_data['price'] > 0:
                prices.append(bi_data['price'])
        
        # 计算共识价格（多源平均）
        if prices:
            aggregated['consensus_price'] = sum(prices) / len(prices)
            
            # 价格一致性检查
            if len(prices) > 1:
                price_variance = max(prices) - min(prices)
                price_consistency = 1 - (price_variance / aggregated['consensus_price'])
                aggregated['data_quality_score'] = int(price_consistency * 100)
            else:
                aggregated['data_quality_score'] = 85  # 单一数据源
        
        logger.info(f"价格数据聚合: ${aggregated['consensus_price']:,.2f} (质量分:{aggregated['data_quality_score']:.1f}%)")
        return aggregated
    
    def collect_network_stats(self) -> Optional[Dict]:
        """收集网络统计数据"""
        try:
            # 从多个API获取网络数据
            network_data = {}
            
            # Blockchain.info stats
            try:
                response = self.session.get('https://blockchain.info/stats?format=json', timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    network_data['blockchain_info'] = {
                        'difficulty': data.get('difficulty', 0),
                        'hashrate': data.get('hash_rate', 0),
                        'total_btc': data.get('totalbc', 0) / 100000000,  # satoshi to BTC
                        'blocks_count': data.get('n_blocks_total', 0)
                    }
            except Exception as e:
                logger.debug(f"Blockchain.info stats失败: {e}")
            
            # Mempool.space difficulty
            try:
                response = self.session.get('https://mempool.space/api/v1/difficulty-adjustment', timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    network_data['mempool'] = {
                        'current_difficulty': data.get('difficultyChange', 0),
                        'estimated_hashrate': data.get('currentHashrate', 0) / 1e18,  # H/s to EH/s
                        'blocks_until_adjustment': data.get('blocksUntilRetarget', 0)
                    }
            except Exception as e:
                logger.debug(f"Mempool.space difficulty失败: {e}")
            
            if network_data:
                return self.process_network_data(network_data)
            else:
                return None
                
        except Exception as e:
            logger.error(f"网络数据收集失败: {e}")
            return None
    
    def process_network_data(self, network_data: Dict) -> Dict:
        """处理网络数据"""
        processed = {
            'network_hashrate': 0,
            'network_difficulty': 0,
            'total_supply': 19700000,  # 默认当前供应量
            'data_sources': list(network_data.keys())
        }
        
        # 优先使用Blockchain.info数据
        if 'blockchain_info' in network_data:
            bi_data = network_data['blockchain_info']
            processed['network_difficulty'] = bi_data.get('difficulty', 0)
            
            # 算力处理
            hashrate_raw = bi_data.get('hashrate', 0)
            if hashrate_raw > 1e15:  # 如果是H/s
                processed['network_hashrate'] = hashrate_raw / 1e18
            elif hashrate_raw > 1e6:  # 如果是GH/s  
                processed['network_hashrate'] = hashrate_raw / 1e9
            else:  # 假设是EH/s或其他
                processed['network_hashrate'] = hashrate_raw
                
            processed['total_supply'] = bi_data.get('total_btc', 19700000)
        
        # 使用Mempool.space作为验证
        if 'mempool' in network_data:
            mp_data = network_data['mempool']
            mempool_hashrate = mp_data.get('estimated_hashrate', 0)
            
            if mempool_hashrate > 0 and processed['network_hashrate'] == 0:
                processed['network_hashrate'] = mempool_hashrate
            elif mempool_hashrate > 0:
                # 取平均值提高准确性
                processed['network_hashrate'] = (processed['network_hashrate'] + mempool_hashrate) / 2
        
        # 合理性检查
        if processed['network_hashrate'] < 500 or processed['network_hashrate'] > 1500:
            logger.warning(f"异常算力值: {processed['network_hashrate']:.2f} EH/s")
            processed['network_hashrate'] = 900  # 使用合理默认值
        
        if processed['network_difficulty'] <= 0:
            # 基于算力估算难度
            processed['network_difficulty'] = processed['network_hashrate'] * 1.4e14
        
        logger.info(f"网络数据处理: 算力={processed['network_hashrate']:.2f}EH/s, 难度={processed['network_difficulty']:.2e}")
        return processed
    
    def save_optimized_data(self, price_data: Dict, network_data: Dict):
        """保存优化后的数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 插入主数据表
            insert_sql = """
                INSERT INTO market_analytics (
                    recorded_at, btc_price, btc_market_cap, btc_volume_24h,
                    network_hashrate, network_difficulty, 
                    price_change_24h, source, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_sql, (
                datetime.now(),
                price_data['consensus_price'],
                price_data.get('market_cap', 0),
                price_data.get('volume_24h', 0),
                network_data['network_hashrate'],
                network_data['network_difficulty'],
                price_data.get('price_change_24h', 0),
                f"optimized_v2_{len(price_data.get('sources', []))}sources",
                datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # 更新统计
            self.collection_stats['successful_collections'] += 1
            self.collection_stats['last_collection'] = datetime.now()
            
            logger.info(f"优化数据已保存: ${price_data['consensus_price']:,.2f}, 质量分:{price_data.get('data_quality_score', 0):.1f}%")
            
        except Exception as e:
            self.collection_stats['failed_collections'] += 1
            logger.error(f"优化数据保存失败: {e}")
    
    def run_optimized_collection(self):
        """运行优化的数据收集"""
        logger.info("开始优化数据收集...")
        self.collection_stats['total_collections'] += 1
        
        # 并行收集价格和网络数据
        with ThreadPoolExecutor(max_workers=2) as executor:
            price_future = executor.submit(self.collect_enhanced_price_data)
            network_future = executor.submit(self.collect_network_stats)
            
            try:
                price_data = price_future.result(timeout=20)
                network_data = network_future.result(timeout=20)
                
                if price_data and network_data:
                    self.save_optimized_data(price_data, network_data)
                    return True
                else:
                    logger.warning("价格或网络数据收集失败")
                    return False
                    
            except Exception as e:
                logger.error(f"优化数据收集失败: {e}")
                return False
    
    def get_collection_statistics(self) -> Dict:
        """获取收集统计信息"""
        success_rate = 0
        if self.collection_stats['total_collections'] > 0:
            success_rate = (self.collection_stats['successful_collections'] / 
                          self.collection_stats['total_collections']) * 100
        
        return {
            'total_collections': self.collection_stats['total_collections'],
            'successful_collections': self.collection_stats['successful_collections'],
            'failed_collections': self.collection_stats['failed_collections'],
            'success_rate': success_rate,
            'last_collection': self.collection_stats['last_collection']
        }
    
    def start_optimized_scheduler(self):
        """启动优化的调度器"""
        logger.info("启动优化数据收集调度器...")
        
        # 每10分钟收集一次 (提升到144条/天)
        schedule.every(10).minutes.do(self.run_optimized_collection)
        
        # 运行调度器
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except KeyboardInterrupt:
                logger.info("调度器停止")
                break
            except Exception as e:
                logger.error(f"调度器错误: {e}")
                time.sleep(60)

def main():
    """主函数"""
    processor = OptimizedBatchProcessor()
    
    logger.info("=== 优化批量数据处理器 ===")
    
    # 运行单次收集测试
    logger.info("运行优化数据收集测试...")
    success = processor.run_optimized_collection()
    
    if success:
        print("✅ 优化数据收集测试成功！")
        
        # 显示统计信息
        stats = processor.get_collection_statistics()
        print(f"📊 收集统计：")
        print(f"   成功率: {stats['success_rate']:.1f}%")
        print(f"   总收集: {stats['total_collections']}")
        print(f"   最后收集: {stats['last_collection']}")
        
        # 询问是否启动持续调度
        try:
            start_scheduler = input("是否启动持续数据收集? (y/n): ").strip().lower()
            if start_scheduler == 'y':
                processor.start_optimized_scheduler()
        except KeyboardInterrupt:
            logger.info("用户取消")
    else:
        print("❌ 优化数据收集测试失败")

# 导出批量处理器函数供其他模块使用
def batch_processor():
    """批量数据处理器入口函数"""
    processor = OptimizedBatchProcessor()
    return processor.run_optimized_collection()

if __name__ == "__main__":
    main()