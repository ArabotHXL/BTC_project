"""
多交易所数据收集器 - 提升成交量数据完整性
集成衍生品和资金费率数据
"""

import os
import time
import json
import logging
import requests
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import concurrent.futures

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiExchangeCollector:
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BTC-Mining-Calculator/1.0'
        })
        
        # 交易所API配置
        self.exchanges = {
            'binance': {
                'spot_url': 'https://api.binance.com/api/v3',
                'futures_url': 'https://fapi.binance.com/fapi/v1',
                'symbol': 'BTCUSDT'
            },
            'okx': {
                'spot_url': 'https://www.okx.com/api/v5',
                'futures_url': 'https://www.okx.com/api/v5',
                'symbol': 'BTC-USDT'
            },
            'deribit': {
                'url': 'https://www.deribit.com/api/v2/public',
                'symbol': 'BTC-PERPETUAL'
            },
            'bybit': {
                'spot_url': 'https://api.bybit.com/v5',
                'futures_url': 'https://api.bybit.com/v5',
                'symbol': 'BTCUSDT'
            }
        }
        
        # 自动创建数据表
        self.create_enhanced_table()
    
    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(self.db_url)
    
    def collect_binance_data(self) -> Dict:
        """收集币安现货和合约数据"""
        try:
            data = {}
            
            # 现货数据
            spot_url = f"{self.exchanges['binance']['spot_url']}/ticker/24hr"
            params = {'symbol': self.exchanges['binance']['symbol']}
            
            response = self.session.get(spot_url, params=params, timeout=10)
            if response.status_code == 200:
                spot_data = response.json()
                data['spot'] = {
                    'price': float(spot_data['lastPrice']),
                    'volume_24h': float(spot_data['quoteVolume']),
                    'price_change_24h': float(spot_data['priceChangePercent']),
                    'high_24h': float(spot_data['highPrice']),
                    'low_24h': float(spot_data['lowPrice'])
                }
            
            # 合约数据
            futures_url = f"{self.exchanges['binance']['futures_url']}/ticker/24hr"
            params = {'symbol': self.exchanges['binance']['symbol']}
            
            response = self.session.get(futures_url, params=params, timeout=10)
            if response.status_code == 200:
                futures_data = response.json()
                data['futures'] = {
                    'price': float(futures_data['lastPrice']),
                    'volume_24h': float(futures_data['quoteVolume']),
                    'open_interest': 0  # 需要额外API调用
                }
            
            # 资金费率
            funding_url = f"{self.exchanges['binance']['futures_url']}/premiumIndex"
            params = {'symbol': self.exchanges['binance']['symbol']}
            
            response = self.session.get(funding_url, params=params, timeout=10)
            if response.status_code == 200:
                funding_data = response.json()
                data['funding_rate'] = float(funding_data['lastFundingRate'])
                data['mark_price'] = float(funding_data['markPrice'])
            
            data['exchange'] = 'binance'
            data['timestamp'] = datetime.now()
            logger.info(f"币安数据收集成功: 现货量={data.get('spot', {}).get('volume_24h', 0):,.0f}")
            
            return data
            
        except Exception as e:
            logger.error(f"币安数据收集失败: {e}")
            return {'exchange': 'binance', 'error': str(e)}
    
    def collect_okx_data(self) -> Dict:
        """收集OKX数据"""
        try:
            data = {}
            
            # 现货行情
            spot_url = f"{self.exchanges['okx']['spot_url']}/market/ticker"
            params = {'instId': self.exchanges['okx']['symbol']}
            
            response = self.session.get(spot_url, params=params, timeout=10)
            if response.status_code == 200:
                okx_data = response.json()
                if okx_data['code'] == '0' and okx_data['data']:
                    spot_data = okx_data['data'][0]
                    data['spot'] = {
                        'price': float(spot_data.get('last', 0)),
                        'volume_24h': float(spot_data.get('volCcy24h', 0)),
                        'price_change_24h': float(spot_data.get('chg24h', 0)) * 100,
                        'high_24h': float(spot_data.get('high24h', 0)),
                        'low_24h': float(spot_data.get('low24h', 0))
                    }
            
            # 永续合约数据
            futures_params = {'instId': 'BTC-USDT-SWAP'}
            response = self.session.get(spot_url, params=futures_params, timeout=10)
            if response.status_code == 200:
                okx_data = response.json()
                if okx_data['code'] == '0' and okx_data['data']:
                    futures_data = okx_data['data'][0]
                    data['futures'] = {
                        'price': float(futures_data['last']),
                        'volume_24h': float(futures_data['volCcy24h'])
                    }
            
            # 资金费率
            funding_url = f"{self.exchanges['okx']['futures_url']}/public/funding-rate"
            params = {'instId': 'BTC-USDT-SWAP'}
            
            response = self.session.get(funding_url, params=params, timeout=10)
            if response.status_code == 200:
                funding_data = response.json()
                if funding_data['code'] == '0' and funding_data['data']:
                    data['funding_rate'] = float(funding_data['data'][0]['fundingRate'])
            
            data['exchange'] = 'okx'
            data['timestamp'] = datetime.now()
            logger.info(f"OKX数据收集成功: 现货量={data.get('spot', {}).get('volume_24h', 0):,.0f}")
            
            return data
            
        except Exception as e:
            logger.error(f"OKX数据收集失败: {e}")
            return {'exchange': 'okx', 'error': str(e)}
    
    def collect_deribit_data(self) -> Dict:
        """收集Deribit衍生品数据"""
        try:
            data = {}
            
            # 永续合约数据
            url = f"{self.exchanges['deribit']['url']}/get_ticker"
            params = {'instrument_name': self.exchanges['deribit']['symbol']}
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    ticker = result['result']
                    data['futures'] = {
                        'price': float(ticker['last_price']),
                        'volume_24h': float(ticker['stats']['volume_usd']),
                        'open_interest': float(ticker['open_interest']),
                        'mark_price': float(ticker['mark_price'])
                    }
                    data['funding_rate'] = float(ticker.get('funding_8h', 0))
            
            # 期权数据
            options_url = f"{self.exchanges['deribit']['url']}/get_book_summary_by_currency"
            params = {'currency': 'BTC', 'kind': 'option'}
            
            response = self.session.get(options_url, params=params, timeout=10)
            if response.status_code == 200:
                options_data = response.json()
                if 'result' in options_data:
                    options = options_data['result']
                    total_options_volume = sum(float(opt.get('volume_usd', 0)) for opt in options[:10])  # 前10个期权
                    data['options_volume'] = total_options_volume
            
            data['exchange'] = 'deribit'
            data['timestamp'] = datetime.now()
            logger.info(f"Deribit数据收集成功: 合约量={data.get('futures', {}).get('volume_24h', 0):,.0f}")
            
            return data
            
        except Exception as e:
            logger.error(f"Deribit数据收集失败: {e}")
            return {'exchange': 'deribit', 'error': str(e)}
    
    def collect_bybit_data(self) -> Dict:
        """收集Bybit数据"""
        try:
            data = {}
            
            # 现货数据
            spot_url = f"{self.exchanges['bybit']['spot_url']}/market/tickers"
            params = {'category': 'spot', 'symbol': self.exchanges['bybit']['symbol']}
            
            response = self.session.get(spot_url, params=params, timeout=10)
            if response.status_code == 200:
                bybit_data = response.json()
                if bybit_data['retCode'] == 0 and bybit_data['result']['list']:
                    spot_data = bybit_data['result']['list'][0]
                    data['spot'] = {
                        'price': float(spot_data['lastPrice']),
                        'volume_24h': float(spot_data['turnover24h']),
                        'price_change_24h': float(spot_data['price24hPcnt']) * 100
                    }
            
            # 合约数据
            futures_params = {'category': 'linear', 'symbol': self.exchanges['bybit']['symbol']}
            response = self.session.get(spot_url, params=futures_params, timeout=10)
            if response.status_code == 200:
                bybit_data = response.json()
                if bybit_data['retCode'] == 0 and bybit_data['result']['list']:
                    futures_data = bybit_data['result']['list'][0]
                    data['futures'] = {
                        'price': float(futures_data['lastPrice']),
                        'volume_24h': float(futures_data['turnover24h'])
                    }
            
            data['exchange'] = 'bybit'
            data['timestamp'] = datetime.now()
            logger.info(f"Bybit数据收集成功: 现货量={data.get('spot', {}).get('volume_24h', 0):,.0f}")
            
            return data
            
        except Exception as e:
            logger.error(f"Bybit数据收集失败: {e}")
            return {'exchange': 'bybit', 'error': str(e)}
    
    def collect_all_exchanges(self) -> List[Dict]:
        """并行收集所有交易所数据"""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # 提交所有任务
            futures = {
                executor.submit(self.collect_binance_data): 'binance',
                executor.submit(self.collect_okx_data): 'okx', 
                executor.submit(self.collect_deribit_data): 'deribit',
                executor.submit(self.collect_bybit_data): 'bybit'
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(futures):
                exchange = futures[future]
                try:
                    result = future.result(timeout=15)
                    results.append(result)
                except Exception as e:
                    logger.error(f"{exchange}数据收集超时或失败: {e}")
                    results.append({'exchange': exchange, 'error': str(e)})
        
        return results
    
    def aggregate_volume_data(self, exchange_data: List[Dict]) -> Dict:
        """聚合成交量数据提升完整性"""
        aggregated = {
            'total_spot_volume': 0,
            'total_futures_volume': 0,
            'total_options_volume': 0,
            'weighted_avg_price': 0,
            'funding_rates': [],
            'exchange_count': 0,
            'data_completeness': 0
        }
        
        valid_exchanges = 0
        total_volume = 0
        price_sum = 0
        
        for data in exchange_data:
            if 'error' in data:
                continue
                
            valid_exchanges += 1
            
            # 现货成交量
            if 'spot' in data and 'volume_24h' in data['spot']:
                spot_volume = data['spot']['volume_24h']
                aggregated['total_spot_volume'] += spot_volume
                total_volume += spot_volume
                
                # 价格加权平均
                if 'price' in data['spot']:
                    price_sum += data['spot']['price'] * spot_volume
            
            # 合约成交量
            if 'futures' in data and 'volume_24h' in data['futures']:
                futures_volume = data['futures']['volume_24h']
                aggregated['total_futures_volume'] += futures_volume
                total_volume += futures_volume
            
            # 期权成交量
            if 'options_volume' in data:
                aggregated['total_options_volume'] += data['options_volume']
            
            # 资金费率
            if 'funding_rate' in data:
                aggregated['funding_rates'].append({
                    'exchange': data['exchange'],
                    'rate': data['funding_rate']
                })
        
        # 计算加权平均价格
        if total_volume > 0:
            aggregated['weighted_avg_price'] = price_sum / total_volume
        
        # 数据完整性评分
        aggregated['exchange_count'] = valid_exchanges
        aggregated['data_completeness'] = (valid_exchanges / len(self.exchanges)) * 100
        
        logger.info(f"数据聚合完成: {valid_exchanges}个交易所, 总量={total_volume:,.0f}, 完整性={aggregated['data_completeness']:.1f}%")
        
        return aggregated
    
    def save_enhanced_data(self, aggregated_data: Dict):
        """保存增强的数据到数据库"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 更新或插入增强数据
            insert_sql = """
                INSERT INTO market_analytics_enhanced (
                    recorded_at, total_spot_volume, total_futures_volume, 
                    total_options_volume, weighted_avg_price, avg_funding_rate,
                    data_completeness, exchange_count, source_detail
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (recorded_at) 
                DO UPDATE SET 
                    total_spot_volume = EXCLUDED.total_spot_volume,
                    total_futures_volume = EXCLUDED.total_futures_volume,
                    data_completeness = EXCLUDED.data_completeness,
                    updated_at = NOW()
            """
            
            # 计算平均资金费率
            avg_funding = 0
            if aggregated_data['funding_rates']:
                avg_funding = sum(fr['rate'] for fr in aggregated_data['funding_rates']) / len(aggregated_data['funding_rates'])
            
            cursor.execute(insert_sql, (
                datetime.now(),
                aggregated_data['total_spot_volume'],
                aggregated_data['total_futures_volume'], 
                aggregated_data['total_options_volume'],
                aggregated_data['weighted_avg_price'],
                avg_funding,
                aggregated_data['data_completeness'],
                aggregated_data['exchange_count'],
                json.dumps(aggregated_data['funding_rates'])
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("增强数据已保存到数据库")
            
        except Exception as e:
            logger.error(f"数据保存失败: {e}")
    
    def create_enhanced_table(self):
        """创建增强数据表"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS market_analytics_enhanced (
                    id SERIAL PRIMARY KEY,
                    recorded_at TIMESTAMP NOT NULL UNIQUE,
                    total_spot_volume BIGINT,
                    total_futures_volume BIGINT,
                    total_options_volume BIGINT,
                    weighted_avg_price DECIMAL(12,2),
                    avg_funding_rate DECIMAL(8,6),
                    data_completeness DECIMAL(5,2),
                    exchange_count INTEGER,
                    source_detail JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_enhanced_recorded_at 
                ON market_analytics_enhanced(recorded_at);
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("增强数据表创建完成")
            
        except Exception as e:
            logger.error(f"创建增强数据表失败: {e}")

def main():
    """运行多交易所数据收集"""
    collector = MultiExchangeCollector()
    
    logger.info("=== 启动多交易所数据收集器 ===")
    
    # 创建表
    collector.create_enhanced_table()
    
    # 收集数据
    exchange_data = collector.collect_all_exchanges()
    
    # 聚合数据
    aggregated = collector.aggregate_volume_data(exchange_data)
    
    # 保存数据
    collector.save_enhanced_data(aggregated)
    
    # 输出结果
    print(f"\n✅ 多交易所数据收集完成！")
    print(f"📊 数据统计：")
    print(f"   有效交易所: {aggregated['exchange_count']}/4")
    print(f"   数据完整性: {aggregated['data_completeness']:.1f}%")
    print(f"   现货总量: ${aggregated['total_spot_volume']:,.0f}")
    print(f"   合约总量: ${aggregated['total_futures_volume']:,.0f}")
    print(f"   期权总量: ${aggregated['total_options_volume']:,.0f}")
    print(f"   加权价格: ${aggregated['weighted_avg_price']:,.2f}")
    
    if aggregated['funding_rates']:
        print(f"   资金费率:")
        for fr in aggregated['funding_rates']:
            print(f"     {fr['exchange']}: {fr['rate']:.4f}%")

if __name__ == "__main__":
    main()