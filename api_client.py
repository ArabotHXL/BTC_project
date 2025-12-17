"""
优化的API客户端 - 带重试和缓存机制
"""
import time
import logging
import requests
from typing import Optional, Dict, Any
from cache_manager import cache, CacheKeys
# from performance_monitor import measure_performance  # 暂时注释掉，不存在此函数

logger = logging.getLogger(__name__)

class APIClient:
    """统一的API客户端"""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BTC-Mining-Calculator/1.0'
        })
    
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[Dict]:
        """发起HTTP请求，带重试机制"""
        for attempt in range(self.max_retries):
            try:
                kwargs.setdefault('timeout', self.timeout)
                
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                
                return response.json()
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {e}")
                break
        
        return None
    
    def get_btc_price(self) -> Optional[float]:
        """获取BTC价格"""
        # 先检查缓存
        cached_price = cache.get(CacheKeys.BTC_PRICE)
        if cached_price:
            return cached_price
        
        # CoinGecko API
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'bitcoin',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        
        data = self._make_request(url, params=params)
        if data and 'bitcoin' in data:
            price = data['bitcoin']['usd']
            # 缓存60秒
            cache.set(CacheKeys.BTC_PRICE, price, ttl=60)
            return price
        
        # 备用：Blockchain.info
        url = "https://blockchain.info/ticker"
        data = self._make_request(url)
        if data and 'USD' in data:
            price = data['USD']['last']
            cache.set(CacheKeys.BTC_PRICE, price, ttl=60)
            return price
        
        return None
    
    def get_network_hashrate(self) -> Optional[float]:
        """获取网络算力"""
        # 先检查缓存
        cached_hashrate = cache.get(CacheKeys.NETWORK_HASHRATE)
        if cached_hashrate:
            return cached_hashrate
        
        # Blockchain.info API
        url = "https://blockchain.info/q/hashrate"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                # 返回的是GH/s，转换为EH/s
                hashrate_gh = float(response.text)
                hashrate_eh = hashrate_gh / 1_000_000_000
                
                # 缓存5分钟
                cache.set(CacheKeys.NETWORK_HASHRATE, hashrate_eh, ttl=300)
                return hashrate_eh
        except Exception as e:
            logger.error(f"Failed to get network hashrate: {e}")
        
        return None
    
    def get_network_difficulty(self) -> Optional[float]:
        """获取网络难度"""
        # 先检查缓存
        cached_difficulty = cache.get(CacheKeys.NETWORK_DIFFICULTY)
        if cached_difficulty:
            return cached_difficulty
        
        # Blockchain.info API
        url = "https://blockchain.info/q/getdifficulty"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                difficulty = float(response.text)
                
                # 缓存10分钟
                cache.set(CacheKeys.NETWORK_DIFFICULTY, difficulty, ttl=600)
                return difficulty
        except Exception as e:
            logger.error(f"Failed to get network difficulty: {e}")
        
        return None
    
    def get_fear_greed_index(self) -> Optional[Dict]:
        """获取恐惧贪婪指数"""
        # 先检查缓存
        cached_index = cache.get(CacheKeys.FEAR_GREED_INDEX)
        if cached_index:
            return cached_index
        
        # Alternative.me API
        url = "https://api.alternative.me/fng/"
        params = {'limit': 1}
        
        data = self._make_request(url, params=params)
        if data and 'data' in data and len(data['data']) > 0:
            index_data = {
                'value': int(data['data'][0]['value']),
                'classification': data['data'][0]['value_classification']
            }
            
            # 缓存1小时
            cache.set(CacheKeys.FEAR_GREED_INDEX, index_data, ttl=3600)
            return index_data
        
        return None
    
    def get_market_data(self) -> Dict[str, Any]:
        """获取完整的市场数据"""
        market_data = {
            'btc_price': self.get_btc_price() or 0,
            'network_hashrate': self.get_network_hashrate() or 0,
            'network_difficulty': self.get_network_difficulty() or 0,
            'timestamp': time.time()
        }
        
        # 尝试获取恐惧贪婪指数
        fear_greed = self.get_fear_greed_index()
        if fear_greed:
            market_data['fear_greed_index'] = fear_greed['value']
            market_data['fear_greed_label'] = fear_greed['classification']
        
        return market_data
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'session'):
            self.session.close()

# 全局API客户端实例
api_client = APIClient()

# 兼容性函数 - 为批量计算器路由提供
def get_btc_price_with_fallback() -> float:
    """获取BTC价格，带备用方案"""
    price = api_client.get_btc_price()
    return price or 80000.0  # 默认价格

def get_network_stats_with_fallback() -> Dict[str, Any]:
    """获取网络统计数据，带备用方案"""
    market_data = api_client.get_market_data()
    return {
        'btc_price': market_data.get('btc_price', 80000.0),
        'network_hashrate': market_data.get('network_hashrate', 900.0),
        'network_difficulty': market_data.get('network_difficulty', 119.12),
        'timestamp': market_data.get('timestamp', time.time())
    }