
import time
from functools import wraps

def cache_result(duration=300):
    """简单的内存缓存装饰器"""
    def decorator(func):
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            current_time = time.time()
            
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < duration:
                    return result
            
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result
            
        return wrapper
    return decorator

def paginate_query(query, page=1, per_page=50):
    """分页查询工具"""
    offset = (page - 1) * per_page
    return query.offset(offset).limit(per_page)
