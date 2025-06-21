
# 性能优化配置
PERFORMANCE_CONFIG = {
    # API超时设置
    'API_TIMEOUT': 10,
    'API_RETRY_COUNT': 3,
    'API_RETRY_DELAY': 1,
    
    # 缓存设置
    'CACHE_DURATION': 300,  # 5分钟
    'PRICE_CACHE_DURATION': 60,  # 1分钟
    'NETWORK_CACHE_DURATION': 180,  # 3分钟
    
    # 数据库查询限制
    'DEFAULT_PAGE_SIZE': 50,
    'MAX_QUERY_LIMIT': 1000,
    
    # 文件上传限制
    'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
}
