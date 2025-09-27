#!/usr/bin/env python3
"""
独立数据分析引擎
实时抓取加密货币数据，自动生成分析报告
"""

import os
import time
import json
import logging
import requests
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
from dataclasses import dataclass
import schedule
import pytz

# 延迟导入高级算法引擎，避免循环依赖
advanced_engine = None
try:
    from .advanced_algorithm_engine import advanced_engine
except ImportError as e:
    logging.warning(f"高级算法引擎暂不可用: {e}")
    advanced_engine = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """市场数据结构"""
    timestamp: datetime
    btc_price: float
    btc_market_cap: float
    btc_volume_24h: float
    network_hashrate: float
    network_difficulty: float
    block_reward: float
    fear_greed_index: Optional[int] = None
    source: str = "multiple"

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.connection = None
        self.setup_tables()
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = psycopg2.connect(self.db_url)
            return self.connection
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None
    
    def setup_tables(self):
        """创建分析数据表"""
        conn = self.connect()
        if not conn:
            return
        
        cursor = None
        try:
            cursor = conn.cursor()
            
            # 创建市场数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_analytics (
                    id SERIAL PRIMARY KEY,
                    recorded_at TIMESTAMP NOT NULL,
                    btc_price DECIMAL(12,2) NOT NULL,
                    btc_market_cap BIGINT,
                    btc_volume_24h BIGINT,
                    network_hashrate DECIMAL(15,2),
                    network_difficulty DECIMAL(20,2),
                    block_reward DECIMAL(8,4),
                    fear_greed_index INTEGER,
                    price_change_1h DECIMAL(5,2),
                    price_change_24h DECIMAL(5,2),
                    price_change_7d DECIMAL(5,2),
                    source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 创建技术指标表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS technical_indicators (
                    id SERIAL PRIMARY KEY,
                    recorded_at TIMESTAMP NOT NULL,
                    sma_20 DECIMAL(12,2),
                    sma_50 DECIMAL(12,2),
                    ema_12 DECIMAL(12,2),
                    ema_26 DECIMAL(12,2),
                    rsi_14 DECIMAL(5,2),
                    macd DECIMAL(8,4),
                    bollinger_upper DECIMAL(12,2),
                    bollinger_lower DECIMAL(12,2),
                    volatility_30d DECIMAL(5,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 创建挖矿指标表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mining_metrics (
                    id SERIAL PRIMARY KEY,
                    recorded_at TIMESTAMP NOT NULL,
                    hashrate_change_24h DECIMAL(5,2),
                    difficulty_adjustment DECIMAL(5,2),
                    next_difficulty_estimate DECIMAL(20,2),
                    mempool_size INTEGER,
                    avg_block_time DECIMAL(6,2),
                    mining_revenue_per_th DECIMAL(10,6),
                    network_value_to_transactions DECIMAL(8,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 创建分析报告表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    id SERIAL PRIMARY KEY,
                    report_type VARCHAR(50) NOT NULL,
                    generated_at TIMESTAMP NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    summary TEXT,
                    key_findings JSON,
                    recommendations JSON,
                    risk_assessment JSON,
                    data_period_start TIMESTAMP,
                    data_period_end TIMESTAMP,
                    confidence_score DECIMAL(3,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 创建索引提高查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_recorded_at ON market_analytics(recorded_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_technical_recorded_at ON technical_indicators(recorded_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mining_recorded_at ON mining_metrics(recorded_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_type_date ON analysis_reports(report_type, generated_at);")
            
            conn.commit()
            logger.info("数据表创建完成")
            
        except Exception as e:
            logger.error(f"创建数据表失败: {e}")
            conn.rollback()
        finally:
            if cursor:
                cursor.close()
            conn.close()

class DataCollector:
    """数据收集器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BTC-Analytics-Engine/1.0'
        })
    
    def collect_coingecko_data(self) -> Optional[Dict]:
        """从CoinGecko收集数据"""
        try:
            # 获取比特币基础数据
            btc_url = "https://api.coingecko.com/api/v3/coins/bitcoin"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            }
            
            response = self.session.get(btc_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            market_data = data['market_data']
            
            return {
                'price': market_data['current_price']['usd'],
                'market_cap': market_data['market_cap']['usd'],
                'volume_24h': market_data['total_volume']['usd'],
                'price_change_1h': market_data['price_change_percentage_1h_in_currency']['usd'],
                'price_change_24h': market_data['price_change_percentage_24h_in_currency']['usd'],
                'price_change_7d': market_data['price_change_percentage_7d_in_currency']['usd']
            }
            
        except Exception as e:
            logger.error(f"CoinGecko数据收集失败: {e}")
            return None
    
    def collect_mempool_data(self) -> Optional[Dict]:
        """从Mempool.space收集数据"""
        try:
            # Mempool.space API - 最新区块数据
            blocks_url = "https://mempool.space/api/v1/blocks"
            
            response = self.session.get(blocks_url, timeout=15)
            response.raise_for_status()
            blocks = response.json()
            
            if blocks and len(blocks) > 0:
                latest_block = blocks[0]
                
                # 计算区块奖励（satoshi转换为BTC）
                block_reward_satoshi = latest_block.get('extras', {}).get('reward', 0)
                block_reward_btc = block_reward_satoshi / 100000000  # satoshi to BTC
                
                return {
                    'block_height': latest_block.get('height', 0),
                    'block_timestamp': latest_block.get('timestamp', 0),
                    'network_difficulty': latest_block.get('difficulty', 0),
                    'tx_count': latest_block.get('tx_count', 0),
                    'block_reward': block_reward_btc,
                    'total_fees': latest_block.get('extras', {}).get('totalFees', 0) / 100000000,  # satoshi to BTC
                    'source': 'mempool'
                }
            return None
                
        except requests.exceptions.Timeout:
            logger.warning("Mempool.space请求超时，跳过数据收集")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Mempool.space网络请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"Mempool.space数据收集失败: {e}")
            return None

    def collect_blockchain_hashrate_data(self) -> Optional[Dict]:
        """从多个数据源收集算力数据，优先使用Blockchain.info stats接口 (875 EH/s)"""
        try:
            # 方法1: 优先使用Blockchain.info stats接口 (875 EH/s)
            try:
                blockchain_response = self.session.get('https://blockchain.info/stats?format=json', timeout=15)
                if blockchain_response.status_code == 200:
                    data = blockchain_response.json()
                    # blockchain.info/stats返回的hash_rate字段实际上需要特殊处理
                    hashrate_raw = float(data.get('hash_rate', 0))
                    
                    # 检查hash_rate字段是否有效
                    if hashrate_raw == 0:
                        logger.warning(f"Blockchain.info hash_rate字段为0，尝试使用难度计算算力")
                        # 使用难度计算算力: hashrate = difficulty * 2^32 / 600
                        difficulty = float(data.get('difficulty', 0))
                        if difficulty > 0:
                            hashrate_eh = (difficulty * (2**32)) / 600 / 1e18  # 转换为EH/s
                            logger.info(f"✅ Blockchain.info基于难度计算算力: {hashrate_eh:.2f} EH/s (难度: {difficulty:.0f})")
                        else:
                            logger.warning("Blockchain.info难度数据也不可用")
                            return None
                    else:
                        # hash_rate字段有效，进行转换 (实际测试表明需要除以1e9)
                        hashrate_eh = hashrate_raw / 1e9  # 转换为EH/s
                        difficulty = float(data.get('difficulty', 0))
                        logger.info(f"✅ Blockchain.info主要算力数据: {hashrate_eh:.2f} EH/s (hash_rate字段)")
                    
                    # 验证算力值是否合理 (当前应该在700-1200 EH/s范围)
                    if hashrate_eh < 500 or hashrate_eh > 1500:
                        logger.warning(f"Blockchain.info算力值异常: {hashrate_eh:.2f} EH/s，尝试备用数据源")
                        return None
                    
                    return {
                        'network_hashrate': hashrate_eh,
                        'network_difficulty': difficulty if 'difficulty' in locals() else float(data.get('difficulty', 0)),
                        'hashrate_timestamp': int(time.time()),
                        'source': 'blockchain.info'
                    }
            except Exception as e:
                logger.warning(f"Blockchain.info stats接口获取失败，回退至Minerstat: {e}")
            
            # 方法2: 备用Minerstat API
            try:
                minerstat_response = self.session.get('https://api.minerstat.com/v2/coins?list=BTC', timeout=15)
                if minerstat_response.status_code == 200:
                    data = minerstat_response.json()
                    if data and len(data) > 0:
                        btc_data = data[0]
                        # minerstat返回的是H/s格式的科学记数法
                        hashrate_hs = float(btc_data.get('network_hashrate', 0))
                        hashrate_eh = hashrate_hs / 1e18  # H/s to EH/s
                        difficulty = float(btc_data.get('difficulty', 0))
                        
                        logger.info(f"⚠️ Minerstat备用算力数据: {hashrate_eh:.2f} EH/s (Blockchain.info不可用)")
                        return {
                            'network_hashrate': hashrate_eh,
                            'network_difficulty': difficulty,
                            'hashrate_timestamp': int(time.time()),
                            'source': 'minerstat'
                        }
            except Exception as e:
                logger.warning(f"Minerstat算力获取失败: {e}")
            
            # 方法3: 最后备用CoinWarz API (专业挖矿数据)
            try:
                coinwarz_response = self.session.get('https://www.coinwarz.com/v1/api/nethash?apikey=Free&coin=btc', timeout=15)
                if coinwarz_response.status_code == 200:
                    data = coinwarz_response.json()
                    if data and data.get('Success') and 'Data' in data:
                        # CoinWarz返回的可能是H/s或GH/s
                        hashrate_value = float(data['Data']['NetHash'])
                        hashrate_unit = data['Data'].get('Unit', 'H/s')
                        
                        # 根据单位转换为EH/s
                        if 'EH/s' in hashrate_unit:
                            hashrate_eh = hashrate_value
                        elif 'TH/s' in hashrate_unit:
                            hashrate_eh = hashrate_value / 1000  # TH/s to EH/s
                        elif 'GH/s' in hashrate_unit:
                            hashrate_eh = hashrate_value / 1000000  # GH/s to EH/s
                        else:
                            hashrate_eh = hashrate_value / 1e18  # H/s to EH/s
                        
                        logger.warning(f"⚠️ CoinWarz最后备用算力: {hashrate_eh:.2f} EH/s")
                        return {
                            'network_hashrate': hashrate_eh,
                            'hashrate_timestamp': int(time.time()),
                            'source': 'coinwarz'
                        }
            except Exception as e:
                logger.debug(f"CoinWarz算力获取失败: {e}")
            
            # 方法2: 尝试从mempool.space获取最新算力数据
            try:
                mempool_response = self.session.get('https://mempool.space/api/v1/difficulty-adjustment', timeout=15)
                if mempool_response.status_code == 200:
                    mempool_data = mempool_response.json()
                    if 'currentHashrate' in mempool_data:
                        # mempool.space返回的算力已经是H/s单位
                        hashrate_hs = mempool_data['currentHashrate']
                        hashrate_eh = hashrate_hs / 1e18  # H/s to EH/s
                        
                        logger.info(f"Mempool.space算力数据: {hashrate_eh:.2f} EH/s")
                        return {
                            'network_hashrate': hashrate_eh,
                            'hashrate_timestamp': int(time.time()),
                            'source': 'mempool_space'
                        }
            except Exception as e:
                logger.debug(f"Mempool.space算力获取失败: {e}")
            
            # 方法3: 从blockchain.info获取最新难度并计算算力
            difficulty_response = self.session.get('https://blockchain.info/q/getdifficulty', timeout=15)
            if difficulty_response.status_code == 200:
                difficulty = float(difficulty_response.text.strip())
                
                # 使用与计算器相同的公式: hashrate = difficulty * 2^32 / 600
                hashrate_from_difficulty = (difficulty * (2**32)) / 600
                hashrate_eh = hashrate_from_difficulty / 1e18  # 转换为EH/s
                
                logger.info(f"基于难度计算的网络算力: {hashrate_eh:.2f} EH/s (难度: {difficulty:.2f}T)")
                return {
                    'network_hashrate': hashrate_eh,
                    'network_difficulty': difficulty,
                    'hashrate_timestamp': int(time.time()),
                    'source': 'difficulty_calculation'
                }
            
            # 方法4: 备用 - 直接从blockchain.info的hashrate API获取
            hashrate_response = self.session.get('https://blockchain.info/q/hashrate', timeout=15)
            if hashrate_response.status_code == 200:
                hashrate_gh = float(hashrate_response.text.strip())
                # 转换GH/s到EH/s
                hashrate_eh = hashrate_gh / 1e9  # GH/s to EH/s
                
                logger.info(f"Blockchain.info直接算力数据: {hashrate_eh:.2f} EH/s")
                return {
                    'network_hashrate': hashrate_eh,
                    'hashrate_timestamp': int(time.time()),
                    'source': 'blockchain_info_direct'
                }
            
            return None
                
        except Exception as e:
            logger.error(f"所有算力数据源收集失败: {e}")
            return None

    def collect_bitcoin_rpc_data(self) -> Optional[Dict]:
        """从Bitcoin RPC节点收集数据"""
        try:
            from bitcoin_rpc_client import BitcoinRPCClient
            
            client = BitcoinRPCClient()
            if not client.is_rpc_available():
                logger.debug("Bitcoin RPC不可用，跳过RPC数据收集")
                return None
                
            rpc_data = client.get_comprehensive_mining_data()
            if rpc_data:
                logger.info(f"RPC数据收集成功: 区块{rpc_data.get('current_block_height', 0)}")
                return rpc_data
            else:
                logger.warning("RPC数据收集失败")
                return None
                
        except ImportError:
            logger.debug("bitcoin_rpc_client模块不可用")
            return None
        except Exception as e:
            logger.debug(f"Bitcoin RPC数据收集失败: {e}")
            return None

    def collect_blockchain_info_data(self) -> Optional[Dict]:
        """从Blockchain.info收集网络数据 - 备用方法"""
        try:
            # 网络难度
            difficulty_response = self.session.get("https://blockchain.info/q/getdifficulty", timeout=15)
            difficulty = float(difficulty_response.text)
            
            # 区块奖励 (当前固定为3.125)
            block_reward = 3.125
            
            # 计算网络算力 (基于难度)
            network_hashrate = (difficulty * (2**32)) / (10 * 60) / 1e18  # EH/s
            
            return {
                'network_difficulty': difficulty,
                'network_hashrate': network_hashrate,
                'block_reward': block_reward
            }
            
        except Exception as e:
            logger.error(f"Blockchain.info数据收集失败: {e}")
            return None

    def collect_coingecko_simple_data(self) -> Optional[Dict]:
        """从CoinGecko收集简单价格数据 - 较少限制"""
        try:
            # 简单价格API（限制较少）
            price_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
            
            response = self.session.get(price_url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            bitcoin_data = data.get('bitcoin', {})
            
            return {
                'btc_price': bitcoin_data.get('usd', 0),
                'source': 'coingecko_simple'
            }
                
        except requests.exceptions.Timeout:
            logger.warning("CoinGecko API请求超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"CoinGecko API网络请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"CoinGecko简单API数据收集失败: {e}")
            return None
    
    def collect_fear_greed_index(self) -> Optional[int]:
        """收集恐惧贪婪指数"""
        try:
            url = "https://api.alternative.me/fng/?limit=1"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            return int(data['data'][0]['value'])
            
        except requests.exceptions.Timeout:
            logger.warning("恐惧贪婪指数API请求超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"恐惧贪婪指数API网络请求失败: {e}")
            return None  
        except Exception as e:
            logger.error(f"恐惧贪婪指数收集失败: {e}")
            return None
    
    def collect_all_data(self) -> Optional[MarketData]:
        """收集所有数据 - 使用新的可靠API源"""
        logger.info("开始收集市场数据...")
        
        # 优先使用Mempool.space获取最新区块数据
        mempool_data = self.collect_mempool_data()
        
        # 优先使用本地Bitcoin RPC，备用Blockchain.info算力数据
        rpc_data = self.collect_bitcoin_rpc_data()
        hashrate_data = self.collect_blockchain_hashrate_data()
        logger.info(f"算力数据收集结果: {hashrate_data}")
        
        # ✅ 优先使用完整CoinGecko API获取价格和量能数据
        price_data = self.collect_coingecko_data()
        
        # 如果完整API失败，使用简单API（但会缺少量能数据）
        if not price_data:
            logger.info("完整CoinGecko API失败，尝试简单API（量能数据不可用）")
            price_data = self.collect_coingecko_simple_data()
        
        # 收集恐惧贪婪指数
        fear_greed = self.collect_fear_greed_index()
        
        # 如果主要数据源失败，使用备用源
        if not mempool_data:
            logger.info("Mempool.space失败，使用备用Blockchain.info数据")
            blockchain_data = self.collect_blockchain_info_data()
        else:
            blockchain_data = None
        
        # 如果仍然没有价格数据，从数据库获取最新数据
        if not price_data:
            logger.warning("所有价格API受限，使用数据库最新价格")
            try:
                conn = self.db_manager.connect()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT btc_price, btc_market_cap, btc_volume_24h 
                        FROM market_analytics 
                        WHERE btc_price > 0
                        ORDER BY recorded_at DESC 
                        LIMIT 1
                    """)
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        price_data = {
                            'btc_price': float(result[0]),
                            'market_cap': int(result[1]) if result[1] else 2120000000000,
                            'volume_24h': int(result[2]) if result[2] else 20000000000
                        }
                        logger.info(f"使用数据库最新价格: ${price_data['btc_price']:,.2f}")
            except Exception as e:
                logger.error(f"数据库价格获取失败: {e}")
        
        # 确保至少有基础网络数据
        if not mempool_data and not blockchain_data:
            logger.error("所有网络数据源都失败")
            return None
        
        # 整合数据 - 使用EST时区
        est_tz = pytz.timezone('US/Eastern')
        current_time = datetime.now(est_tz)
        
        # 优先使用RPC数据（最准确），其次使用mempool数据
        if rpc_data and rpc_data.get('difficulty', 0) > 0:
            difficulty = rpc_data.get('difficulty', 0)
            block_reward = 3.125  # 当前区块奖励
            current_block_height = rpc_data.get('current_block_height', 0)
            median_time = rpc_data.get('median_time', 0)
            blocks_until_adjustment = rpc_data.get('blocks_until_difficulty_adjustment', 0)
            source_name = rpc_data.get('source', 'bitcoin_rpc')
            logger.info(f"使用{source_name}数据: 区块{current_block_height}, 难度={difficulty:.0f}")
        elif mempool_data:
            difficulty = mempool_data.get('network_difficulty', 0)
            block_reward = mempool_data.get('block_reward', 3.125)
            logger.info(f"使用Mempool数据: 难度={difficulty:.0f}, 奖励={block_reward}")
        else:
            difficulty = blockchain_data.get('network_difficulty', 0) if blockchain_data else 0
            block_reward = blockchain_data.get('block_reward', 3.125) if blockchain_data else 3.125
            logger.info(f"使用Blockchain.info数据: 难度={difficulty:.0f}, 奖励={block_reward}")
        
        # 算力数据优先级: Minerstat > CoinWarz > RPC > Blockchain.info  
        if hashrate_data and hashrate_data.get('source') == 'minerstat':
            network_hashrate = hashrate_data.get('network_hashrate', 0)
            hashrate_source = 'minerstat'
            logger.info(f"使用Minerstat实时算力: {network_hashrate:.2f} EH/s")
        elif hashrate_data and hashrate_data.get('source') == 'coinwarz':
            network_hashrate = hashrate_data.get('network_hashrate', 0)
            hashrate_source = 'coinwarz'
            logger.info(f"使用CoinWarz算力: {network_hashrate:.2f} EH/s")
        elif rpc_data and rpc_data.get('network_hashrate_eh'):
            network_hashrate = rpc_data['network_hashrate_eh']
            hashrate_source = rpc_data.get('source', 'bitcoin_rpc')
            logger.info(f"使用RPC算力数据: {network_hashrate:.2f} EH/s (来源: {hashrate_source})")
        elif hashrate_data:
            potential_hashrate = hashrate_data.get('network_hashrate', 0)
            # 验证算力值合理性 (当前范围应该在700-1000 EH/s)
            if 100 <= potential_hashrate <= 2000:
                network_hashrate = potential_hashrate
                hashrate_source = hashrate_data.get('source', 'unknown')
                logger.info(f"使用备用算力源: {network_hashrate:.2f} EH/s")
            else:
                # 算力值异常，使用从难度计算的值
                network_hashrate = (difficulty * (2**32)) / (10 * 60) / 1e18 if difficulty else 850.0
                hashrate_source = 'difficulty_calculation'
                logger.warning(f"算力数据异常({potential_hashrate:.2f} EH/s)，使用难度计算: {network_hashrate:.2f} EH/s")
        elif mempool_data:
            # 如果没有专用算力数据，从难度计算
            network_hashrate = (difficulty * (2**32)) / (10 * 60) / 1e18 if difficulty else 0
            hashrate_source = 'difficulty_calculation'
            logger.info(f"从难度计算算力: {network_hashrate:.2f} EH/s")
        else:
            network_hashrate = blockchain_data.get('network_hashrate', 0) if blockchain_data else 850.0
            hashrate_source = 'fallback'
        
        # 价格数据
        if price_data:
            btc_price = price_data.get('btc_price', 0) or price_data.get('price', 0)
            market_cap = price_data.get('market_cap', 0)
            volume_24h = price_data.get('volume_24h', 0)
            logger.info(f"使用价格数据: ${btc_price:,.2f}, 量能={volume_24h:,}")
        else:
            logger.error("无法获取任何价格数据")
            return None
        
        # 创建市场数据对象
        market_data = MarketData(
            timestamp=current_time,
            btc_price=btc_price,
            btc_market_cap=market_cap,
            btc_volume_24h=volume_24h,
            network_hashrate=network_hashrate,
            network_difficulty=difficulty,
            block_reward=block_reward,
            fear_greed_index=fear_greed,
            source="mempool+blockchain" if mempool_data else "blockchain_fallback"
        )
        
        logger.info(f"数据收集完成: BTC=${market_data.btc_price:,.2f}, 算力={market_data.network_hashrate:.2f}EH/s")
        return market_data
    
    def save_market_data(self, data: MarketData):
        """保存市场数据"""
        conn = self.db_manager.connect()
        if not conn:
            return
        
        cursor = None
        try:
            cursor = conn.cursor()
            
            # 获取CoinGecko的价格变化数据
            coingecko_data = self.collect_coingecko_data()
            price_change_1h = coingecko_data.get('price_change_1h') if coingecko_data else None
            price_change_24h = coingecko_data.get('price_change_24h') if coingecko_data else None
            price_change_7d = coingecko_data.get('price_change_7d') if coingecko_data else None
            
            cursor.execute("""
                INSERT INTO market_analytics (
                    recorded_at, btc_price, btc_market_cap, btc_volume_24h,
                    network_hashrate, network_difficulty, block_reward,
                    fear_greed_index, price_change_1h, price_change_24h, 
                    price_change_7d, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.timestamp, data.btc_price, data.btc_market_cap, data.btc_volume_24h,
                data.network_hashrate, data.network_difficulty, data.block_reward,
                data.fear_greed_index, price_change_1h, price_change_24h,
                price_change_7d, data.source
            ))
            
            conn.commit()
            logger.info(f"市场数据已保存: {data.timestamp}")
            
        except Exception as e:
            logger.error(f"保存市场数据失败: {e}")
            conn.rollback()
        finally:
            if cursor:
                cursor.close()
            conn.close()

class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_recent_prices(self, days: int = 30) -> pd.DataFrame:
        """获取最近价格数据 - 优化内存使用"""
        conn = self.db_manager.connect()
        if not conn:
            return pd.DataFrame()
        
        try:
            # 减少数据量以避免内存问题
            query = """
                SELECT recorded_at, btc_price 
                FROM market_analytics 
                WHERE recorded_at >= %s AND btc_price > 0
                ORDER BY recorded_at DESC
                LIMIT 200
            """
            start_date = datetime.now() - timedelta(days=days)
            
            # 使用cursor避免pandas警告
            cursor = conn.cursor()
            cursor.execute(query, [start_date])
            results = cursor.fetchall()
            cursor.close()
            
            if results:
                # Ensure proper DataFrame construction with explicit column names
                df = pd.DataFrame(results)
                df.columns = ['recorded_at', 'btc_price']
                df['recorded_at'] = pd.to_datetime(df['recorded_at'])
                df.set_index('recorded_at', inplace=True)
                df = df.sort_index()
                return df
            else:
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取价格数据失败: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def calculate_technical_indicators(self) -> Optional[Dict]:
        """计算技术指标 - 内存优化版本"""
        df = self.get_recent_prices(30)  # 减少数据量
        if df.empty:
            logger.warning("没有足够的价格数据进行技术分析")
            return None
        
        try:
            # Ensure prices is a pandas Series
            prices = pd.Series(df['btc_price'].values, index=df.index, name='btc_price')
            latest_timestamp = df.index[-1]
            
            # 简单移动平均线
            sma_20_series = prices.rolling(window=20).mean() if len(prices) >= 20 else None
            sma_20 = float(sma_20_series.iloc[-1]) if sma_20_series is not None and hasattr(sma_20_series, 'iloc') and len(sma_20_series) > 0 else None
            sma_50_series = prices.rolling(window=50).mean() if len(prices) >= 50 else None
            sma_50 = float(sma_50_series.iloc[-1]) if sma_50_series is not None and hasattr(sma_50_series, 'iloc') and len(sma_50_series) > 0 else None
            
            # 指数移动平均线
            ema_12_series = prices.ewm(span=12).mean() if len(prices) >= 12 else None
            ema_12 = float(ema_12_series.iloc[-1]) if ema_12_series is not None and len(ema_12_series) > 0 else None
            ema_26_series = prices.ewm(span=26).mean() if len(prices) >= 26 else None
            ema_26 = float(ema_26_series.iloc[-1]) if ema_26_series is not None and len(ema_26_series) > 0 else None
            
            # RSI - ensure we pass a pandas Series
            rsi_14 = self.calculate_rsi(prices, 14) if len(prices) >= 15 else None
            
            # 布林带 - ensure we pass a pandas Series
            bollinger_upper, bollinger_lower = self.calculate_bollinger_bands(prices, 20, 2) if len(prices) >= 20 else (None, None)
            
            # 波动率
            volatility_series = prices.pct_change().rolling(window=30).std() if len(prices) >= 30 else None
            volatility_30d = float(volatility_series.iloc[-1]) * 100 if volatility_series is not None and len(volatility_series) > 0 else None
            
            # MACD
            macd = (ema_12 - ema_26) if ema_12 and ema_26 else None
            
            # Convert NumPy types to Python types for PostgreSQL compatibility
            # 将时间戳转换为EST时区
            est_tz = pytz.timezone('US/Eastern')
            est_timestamp = datetime.now(est_tz)
            
            return {
                'recorded_at': est_timestamp,
                'sma_20': float(sma_20) if sma_20 is not None and not pd.isna(sma_20) else None,
                'sma_50': float(sma_50) if sma_50 is not None and not pd.isna(sma_50) else None,
                'ema_12': float(ema_12) if ema_12 is not None and not pd.isna(ema_12) else None,
                'ema_26': float(ema_26) if ema_26 is not None and not pd.isna(ema_26) else None,
                'rsi_14': float(rsi_14) if rsi_14 is not None and not pd.isna(rsi_14) else None,
                'macd': float(macd) if macd is not None and not pd.isna(macd) else None,
                'bollinger_upper': float(bollinger_upper) if bollinger_upper is not None and not pd.isna(bollinger_upper) else None,
                'bollinger_lower': float(bollinger_lower) if bollinger_lower is not None and not pd.isna(bollinger_lower) else None,
                'volatility_30d': float(volatility_30d) if volatility_30d is not None and not pd.isna(volatility_30d) else None
            }
            
        except Exception as e:
            logger.error(f"技术指标计算失败: {e}")
            return None
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """计算RSI"""
        if len(prices) < period + 1:
            return None
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Ensure we get a float value from the Series
        if isinstance(rsi, pd.Series) and len(rsi) > 0:
            return float(rsi.iloc[-1])
        elif isinstance(rsi, (int, float)):
            return float(rsi)
        else:
            return None
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2):
        """计算布林带"""
        if len(prices) < period:
            return None, None
        
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        # Ensure we get float values from the Series
        if isinstance(upper_band, pd.Series) and len(upper_band) > 0:
            upper_val = float(upper_band.iloc[-1])
        else:
            upper_val = None
            
        if isinstance(lower_band, pd.Series) and len(lower_band) > 0:
            lower_val = float(lower_band.iloc[-1])
        else:
            lower_val = None
            
        return upper_val, lower_val
    
    def save_technical_indicators(self, indicators: Dict):
        """保存技术指标"""
        conn = self.db_manager.connect()
        if not conn:
            return
        
        cursor = None
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO technical_indicators (
                    recorded_at, sma_20, sma_50, ema_12, ema_26,
                    rsi_14, macd, bollinger_upper, bollinger_lower, volatility_30d
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                indicators['recorded_at'], indicators.get('sma_20'), indicators.get('sma_50'),
                indicators.get('ema_12'), indicators.get('ema_26'), indicators.get('rsi_14'),
                indicators.get('macd'), indicators.get('bollinger_upper'), 
                indicators.get('bollinger_lower'), indicators.get('volatility_30d')
            ))
            
            conn.commit()
            logger.info(f"技术指标已保存: {indicators['recorded_at']}")
            
        except Exception as e:
            logger.error(f"保存技术指标失败: {e}")
            conn.rollback()
        finally:
            if cursor:
                cursor.close()
            conn.close()

class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def generate_daily_report(self) -> Dict:
        """生成日报"""
        conn = self.db_manager.connect()
        if not conn:
            return {}
        
        cursor = None
        try:
            # 获取最近24小时数据
            cursor = conn.cursor()
            
            # 市场数据分析
            cursor.execute("""
                SELECT 
                    AVG(btc_price) as avg_price,
                    MIN(btc_price) as min_price,
                    MAX(btc_price) as max_price,
                    AVG(network_hashrate) as avg_hashrate,
                    AVG(fear_greed_index) as avg_fear_greed,
                    COUNT(*) as data_points
                FROM market_analytics 
                WHERE recorded_at >= NOW() - INTERVAL '24 hours'
            """)
            
            market_stats = cursor.fetchone()
            
            if not market_stats or market_stats[5] == 0:
                logger.warning("没有足够的24小时数据生成报告")
                return {}
            
            # 技术分析
            cursor.execute("""
                SELECT rsi_14, volatility_30d
                FROM technical_indicators 
                ORDER BY recorded_at DESC 
                LIMIT 1
            """)
            
            tech_data = cursor.fetchone()
            
            # 生成报告 - 使用EST时区
            est_tz = pytz.timezone('US/Eastern')
            est_now = datetime.now(est_tz)
            
            report = {
                'report_type': 'daily',
                'generated_at': est_now,
                'title': f'Bitcoin Daily Analysis - {est_now.strftime("%Y-%m-%d")}',
                'summary': self._generate_daily_summary(market_stats, tech_data),
                'key_findings': {
                    'price_range': f"${market_stats[1]:,.2f} - ${market_stats[2]:,.2f}",
                    'avg_price': f"${market_stats[0]:,.2f}",
                    'avg_hashrate': f"{market_stats[3]:.2f} EH/s",
                    'market_sentiment': self._interpret_fear_greed(market_stats[4]),
                    'rsi_signal': self._interpret_rsi(tech_data[0] if tech_data else None)
                },
                'recommendations': self._generate_recommendations(market_stats, tech_data),
                'risk_assessment': self._assess_risk(market_stats, tech_data),
                'data_period_start': est_now - timedelta(days=1),
                'data_period_end': est_now,
                'confidence_score': 0.85
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成日报失败: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()
            conn.close()
    
    def _generate_daily_summary(self, market_stats, tech_data) -> str:
        """生成日报摘要"""
        avg_price = market_stats[0]
        price_range = market_stats[2] - market_stats[1]
        volatility = price_range / avg_price * 100
        
        summary = f"Bitcoin在过去24小时内交易于${market_stats[1]:,.2f}-${market_stats[2]:,.2f}区间，"
        summary += f"平均价格${avg_price:,.2f}，日内波动率{volatility:.1f}%。"
        
        if market_stats[3]:
            summary += f"网络算力维持在{market_stats[3]:.1f} EH/s水平。"
        
        if tech_data and tech_data[0]:
            rsi = tech_data[0]
            if rsi > 70:
                summary += "技术指标显示超买状态。"
            elif rsi < 30:
                summary += "技术指标显示超卖状态。"
            else:
                summary += "技术指标处于中性区间。"
        
        return summary
    
    def _interpret_fear_greed(self, index: Optional[float]) -> str:
        """解释恐惧贪婪指数"""
        if not index:
            return "数据不足"
        
        if index <= 25:
            return "极度恐惧"
        elif index <= 45:
            return "恐惧"
        elif index <= 55:
            return "中性"
        elif index <= 75:
            return "贪婪"
        else:
            return "极度贪婪"
    
    def _interpret_rsi(self, rsi: Optional[float]) -> str:
        """解释RSI"""
        if not rsi:
            return "数据不足"
        
        if rsi > 70:
            return "超买 - 考虑卖出"
        elif rsi < 30:
            return "超卖 - 考虑买入"
        else:
            return "中性 - 保持观望"
    
    def _generate_recommendations(self, market_stats, tech_data) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 基于价格波动的建议
        price_range = market_stats[2] - market_stats[1]
        volatility = price_range / market_stats[0] * 100
        
        if volatility > 5:
            recommendations.append("高波动环境，建议分批建仓降低风险")
        elif volatility < 2:
            recommendations.append("低波动环境，适合长期持有策略")
        
        # 基于RSI的建议
        if tech_data and tech_data[0]:
            rsi = tech_data[0]
            if rsi > 70:
                recommendations.append("RSI超买，谨慎追涨")
            elif rsi < 30:
                recommendations.append("RSI超卖，可考虑逢低买入")
        
        # 基于算力的建议
        if market_stats[3] and market_stats[3] > 800:
            recommendations.append("网络算力强劲，网络安全性高")
        
        return recommendations
    
    def _assess_risk(self, market_stats, tech_data) -> Dict:
        """风险评估"""
        risk_score = 50  # 基础风险分数
        
        # 基于波动率调整风险
        price_range = market_stats[2] - market_stats[1]
        volatility = price_range / market_stats[0] * 100
        
        if volatility > 10:
            risk_score += 30
        elif volatility > 5:
            risk_score += 15
        elif volatility < 2:
            risk_score -= 10
        
        # 基于技术指标调整风险
        if tech_data and tech_data[0]:
            rsi = tech_data[0]
            if rsi > 80 or rsi < 20:
                risk_score += 20
        
        risk_level = "低" if risk_score < 40 else "中" if risk_score < 70 else "高"
        
        return {
            'risk_score': min(100, max(0, risk_score)),
            'risk_level': risk_level,
            'factors': ['价格波动率', '技术指标', '市场情绪']
        }
    
    def save_report(self, report: Dict):
        """保存报告"""
        conn = self.db_manager.connect()
        if not conn:
            return
        
        cursor = None
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO analysis_reports (
                    report_type, generated_at, title, summary,
                    key_findings, recommendations, risk_assessment,
                    data_period_start, data_period_end, confidence_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                report['report_type'], report['generated_at'], report['title'],
                report['summary'], json.dumps(report['key_findings']),
                json.dumps(report['recommendations']), json.dumps(report['risk_assessment']),
                report['data_period_start'], report['data_period_end'],
                report['confidence_score']
            ))
            
            conn.commit()
            logger.info(f"分析报告已保存: {report['title']}")
            
        except Exception as e:
            logger.error(f"保存分析报告失败: {e}")
            conn.rollback()
        finally:
            if cursor:
                cursor.close()
            conn.close()

class AnalyticsEngine:
    """分析引擎主类"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.data_collector = DataCollector(self.db_manager)
        self.technical_analyzer = TechnicalAnalyzer(self.db_manager)
        self.report_generator = ReportGenerator(self.db_manager)
        self.running = False
    
    def collect_and_analyze(self):
        """收集数据并分析 - 由统一数据管道调度控制每30分钟执行"""
        try:
            # 使用EST时区获取当前时间
            est_tz = pytz.timezone('US/Eastern')
            now = datetime.now(est_tz)
            
            logger.info(f"开始数据收集和分析 - {now.strftime('%Y-%m-%d %H:%M')}")
            
            # 收集市场数据
            market_data = self.data_collector.collect_all_data()
            if market_data:
                self.data_collector.save_market_data(market_data)
                logger.info(f"市场数据已保存: BTC=${market_data.btc_price:,.0f}, 算力={market_data.network_hashrate:.2f}EH/s")
            
            # 计算技术指标
            tech_indicators = self.technical_analyzer.calculate_technical_indicators()
            if tech_indicators:
                self.technical_analyzer.save_technical_indicators(tech_indicators)
                logger.info("技术指标已更新")
            
            logger.info(f"数据收集和分析完成 - {now.strftime('%Y-%m-%d %H:%M')}")
            
        except Exception as e:
            logger.error(f"数据收集分析失败: {e}")
    
    def generate_daily_report(self):
        """生成日报"""
        try:
            report = self.report_generator.generate_daily_report()
            if report:
                self.report_generator.save_report(report)
                logger.info("日报生成完成")
            else:
                logger.warning("日报生成失败 - 数据不足")
                
        except Exception as e:
            logger.error(f"日报生成失败: {e}")
    
    def start_scheduler(self):
        """启动调度器"""
        self.running = True
        
        # 每15分钟收集一次数据
        schedule.every(15).minutes.do(self.collect_and_analyze)
        
        # 每天早上8点生成日报
        schedule.every().day.at("08:00").do(self.generate_daily_report)
        
        # 每天晚上8点生成日报
        schedule.every().day.at("20:00").do(self.generate_daily_report)
        
        logger.info("分析引擎调度器已启动")
        logger.info("数据收集频率: 每15分钟")
        logger.info("报告生成: 每天8:00和20:00")
        
        # 立即执行一次
        self.collect_and_analyze()
        
        # 调度循环
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def stop(self):
        """停止引擎"""
        self.running = False
        logger.info("分析引擎已停止")

def main():
    """主函数"""
    logger.info("启动Bitcoin分析引擎...")
    
    engine = AnalyticsEngine()
    
    try:
        engine.start_scheduler()
    except KeyboardInterrupt:
        logger.info("接收到停止信号...")
        engine.stop()
    except Exception as e:
        logger.error(f"引擎运行异常: {e}")
    
    logger.info("Bitcoin分析引擎已关闭")

if __name__ == "__main__":
    main()