"""统一的API客户端"""
import requests
import logging
import time
from typing import Optional, Dict, Any

class APIClient:
    """统一的外部API客户端"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 10
        
    def _make_request(self, url: str, max_retries: int = 3) -> Optional[Dict[Any, Any]]:
        """统一的API请求方法"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url)
                if response.status_code == 200:
                    return response.json() if 'application/json' in response.headers.get('content-type', '') else {'value': response.text.strip()}
                else:
                    logging.warning(f"API请求失败 {url}, 状态码: {response.status_code}")
            except Exception as e:
                logging.error(f"API请求异常 {url}, 尝试 {attempt + 1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        return None
    
    def get_btc_price(self) -> float:
        """获取BTC价格"""
        try:
            data = self._make_request("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
            if data and 'bitcoin' in data and 'usd' in data['bitcoin']:
                price = float(data['bitcoin']['usd'])
                logging.info(f"成功获取BTC价格: ${price}")
                return price
        except Exception as e:
            logging.error(f"获取BTC价格失败: {str(e)}")
        return 80000.0  # 默认价格
    
    def get_network_difficulty(self) -> float:
        """获取网络难度"""
        try:
            data = self._make_request("https://blockchain.info/q/getdifficulty")
            if data and 'value' in data:
                difficulty = float(data['value']) / 1e12  # 转换为T
                logging.info(f"成功获取网络难度: {difficulty}T")
                return difficulty
        except Exception as e:
            logging.error(f"获取网络难度失败: {str(e)}")
        return 119.12  # 默认难度
    
    def get_network_hashrate(self) -> float:
        """获取网络哈希率"""
        try:
            data = self._make_request("https://blockchain.info/q/hashrate")
            if data and 'value' in data:
                hashrate_gh = float(data['value'])
                hashrate_eh = hashrate_gh / 1e9  # 转换为EH/s
                logging.info(f"成功获取网络哈希率: {hashrate_eh}EH/s")
                return hashrate_eh
        except Exception as e:
            logging.error(f"获取网络哈希率失败: {str(e)}")
        return 900.0  # 默认哈希率
    
    def get_block_reward(self) -> float:
        """获取区块奖励"""
        try:
            data = self._make_request("https://blockchain.info/q/getblockcount")
            if data and 'value' in data:
                block_height = int(data['value'])
                # 根据区块高度计算奖励
                if block_height >= 840000:  # 第四次减半后
                    reward = 3.125
                elif block_height >= 630000:  # 第三次减半后
                    reward = 6.25
                elif block_height >= 420000:  # 第二次减半后
                    reward = 12.5
                elif block_height >= 210000:  # 第一次减半后
                    reward = 25
                else:
                    reward = 50
                logging.info(f"成功获取区块奖励: {reward} BTC")
                return reward
        except Exception as e:
            logging.error(f"获取区块奖励失败: {str(e)}")
        return 3.125  # 默认奖励
    
    def get_all_network_stats(self) -> Dict[str, float]:
        """获取所有网络统计数据"""
        return {
            'btc_price': self.get_btc_price(),
            'difficulty': self.get_network_difficulty(),
            'hashrate': self.get_network_hashrate(),
            'block_reward': self.get_block_reward()
        }