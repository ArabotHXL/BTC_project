"""
CRM地理位置服务
CRM Geographic Location Services

提供城市坐标和地理位置相关功能
Provides city coordinates and geographic location features
"""

CITY_COORDINATES = {
    'Beijing': [39.9042, 116.4074],
    'Shanghai': [31.2304, 121.4737],
    'Shenzhen': [22.5431, 114.0579],
    'Guangzhou': [23.1291, 113.2644],
    'Chengdu': [30.5728, 104.0668],
    'Hangzhou': [30.2741, 120.1551],
    'Nanjing': [32.0603, 118.7969],
    'Wuhan': [30.5928, 114.3055],
    'Chongqing': [29.4316, 106.9123],
    'Xi\'an': [34.3416, 108.9398],
    'Tianjin': [39.3434, 117.3616],
    'Suzhou': [31.2989, 120.5853],
    'Dalian': [38.9140, 121.6147],
    'Qingdao': [36.0671, 120.3826],
    'Xiamen': [24.4798, 118.0894],
    'Hong Kong': [22.3193, 114.1694],
    'Taipei': [25.0330, 121.5654],
    'Singapore': [1.3521, 103.8198],
    'Tokyo': [35.6762, 139.6503],
    'Seoul': [37.5665, 126.9780],
    'New York': [40.7128, -74.0060],
    'London': [51.5074, -0.1278],
    'Paris': [48.8566, 2.3522],
    'Dubai': [25.2048, 55.2708],
    'San Francisco': [37.7749, -122.4194],
    'Los Angeles': [34.0522, -118.2437],
    'Sydney': [-33.8688, 151.2093],
    'Toronto': [43.6532, -79.3832],
    'Vancouver': [49.2827, -123.1207]
}

CHINA_CENTER = [35.0, 105.0]


def get_city_coordinates(city_name):
    """
    获取城市坐标
    Get city coordinates
    
    Args:
        city_name (str): 城市名称
        
    Returns:
        list: [纬度, 经度] 或默认中国中心坐标
    """
    if not city_name:
        return CHINA_CENTER
    
    coords = CITY_COORDINATES.get(city_name)
    if coords:
        return coords
    
    city_lower = city_name.lower()
    for city, latlon in CITY_COORDINATES.items():
        if city.lower() == city_lower:
            return latlon
    
    return CHINA_CENTER


def get_all_cities():
    """
    获取所有支持的城市列表
    Get all supported cities
    
    Returns:
        list: 城市名称列表
    """
    return list(CITY_COORDINATES.keys())


def get_city_count():
    """
    获取支持的城市总数
    Get total number of supported cities
    
    Returns:
        int: 城市数量
    """
    return len(CITY_COORDINATES)


def is_city_supported(city_name):
    """
    检查城市是否被支持
    Check if city is supported
    
    Args:
        city_name (str): 城市名称
        
    Returns:
        bool: 是否支持
    """
    if not city_name:
        return False
    
    if city_name in CITY_COORDINATES:
        return True
    
    city_lower = city_name.lower()
    return any(city.lower() == city_lower for city in CITY_COORDINATES.keys())


def get_region_cities(region='china'):
    """
    按区域获取城市列表
    Get cities by region
    
    Args:
        region (str): 区域名称 ('china', 'asia', 'international')
        
    Returns:
        list: 城市名称列表
    """
    china_cities = ['Beijing', 'Shanghai', 'Shenzhen', 'Guangzhou', 'Chengdu', 
                   'Hangzhou', 'Nanjing', 'Wuhan', 'Chongqing', 'Xi\'an', 
                   'Tianjin', 'Suzhou', 'Dalian', 'Qingdao', 'Xiamen']
    
    asia_cities = ['Hong Kong', 'Taipei', 'Singapore', 'Tokyo', 'Seoul', 'Dubai']
    
    international_cities = ['New York', 'London', 'Paris', 'San Francisco', 
                           'Los Angeles', 'Sydney', 'Toronto', 'Vancouver']
    
    region_map = {
        'china': china_cities,
        'asia': asia_cities,
        'international': international_cities,
        'all': china_cities + asia_cities + international_cities
    }
    
    return region_map.get(region.lower(), [])
