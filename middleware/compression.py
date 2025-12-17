"""
响应压缩中间件 - Response Compression Middleware
Gzip Compression and Streaming Support

功能：
- Gzip响应压缩
- 流式响应支持（大数据集）
- 响应分页优化
- 自动内容协商

目标：减少网络传输时间，提升API响应速度
"""

import gzip
import io
import logging
from functools import wraps
from flask import request, Response, stream_with_context
from typing import Union, Generator, Any

logger = logging.getLogger(__name__)

class CompressionMiddleware:
    """响应压缩中间件"""
    
    def __init__(self, app=None, 
                 min_size: int = 1024,
                 compression_level: int = 6,
                 mime_types: list = None):
        """
        初始化压缩中间件
        
        Parameters:
        -----------
        app : Flask
            Flask应用实例
        min_size : int
            最小压缩大小（字节），小于此大小不压缩
        compression_level : int
            压缩级别 (1-9)，级别越高压缩率越高但速度越慢
        mime_types : list
            需要压缩的MIME类型列表
        """
        self.min_size = min_size
        self.compression_level = compression_level
        self.mime_types = mime_types or [
            'text/html',
            'text/css',
            'text/plain',
            'text/xml',
            'text/javascript',
            'application/json',
            'application/javascript',
            'application/xml',
            'application/xml+rss',
            'application/xhtml+xml',
            'image/svg+xml'
        ]
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """注册中间件到Flask应用"""
        app.after_request(self.compress_response)
        logger.info("响应压缩中间件已注册")
    
    def compress_response(self, response: Response) -> Response:
        """
        压缩响应
        
        Parameters:
        -----------
        response : Response
            Flask响应对象
            
        Returns:
        --------
        Response : 压缩后的响应对象
        """
        # 检查客户端是否支持gzip
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if 'gzip' not in accept_encoding.lower():
            return response
        
        # 检查响应是否已经压缩
        if response.headers.get('Content-Encoding'):
            return response
        
        # 检查响应MIME类型
        content_type = response.headers.get('Content-Type', '').split(';')[0]
        if content_type not in self.mime_types:
            return response
        
        # 获取响应数据
        response_data = response.get_data()
        
        # 检查响应大小
        if len(response_data) < self.min_size:
            logger.debug(f"响应太小({len(response_data)}字节)，跳过压缩")
            return response
        
        # 执行Gzip压缩
        try:
            gzip_buffer = io.BytesIO()
            with gzip.GzipFile(
                mode='wb',
                compresslevel=self.compression_level,
                fileobj=gzip_buffer
            ) as gzip_file:
                gzip_file.write(response_data)
            
            compressed_data = gzip_buffer.getvalue()
            
            # 计算压缩率
            original_size = len(response_data)
            compressed_size = len(compressed_data)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            # 只有在压缩有效时才使用压缩数据
            if compressed_size < original_size:
                response.set_data(compressed_data)
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Length'] = str(compressed_size)
                response.headers['Vary'] = 'Accept-Encoding'
                
                logger.debug(
                    f"响应已压缩: {original_size}B -> {compressed_size}B "
                    f"(压缩率: {compression_ratio:.1f}%)"
                )
            else:
                logger.debug("压缩后体积更大，使用原始响应")
        
        except Exception as e:
            logger.error(f"响应压缩失败: {e}")
        
        return response


def gzip_compress(data: Union[str, bytes], level: int = 6) -> bytes:
    """
    Gzip压缩数据
    
    Parameters:
    -----------
    data : Union[str, bytes]
        要压缩的数据
    level : int
        压缩级别 (1-9)
        
    Returns:
    --------
    bytes : 压缩后的数据
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    gzip_buffer = io.BytesIO()
    with gzip.GzipFile(mode='wb', compresslevel=level, fileobj=gzip_buffer) as f:
        f.write(data)
    
    return gzip_buffer.getvalue()


def gzip_decompress(data: bytes) -> bytes:
    """
    Gzip解压数据
    
    Parameters:
    -----------
    data : bytes
        压缩的数据
        
    Returns:
    --------
    bytes : 解压后的数据
    """
    with gzip.GzipFile(mode='rb', fileobj=io.BytesIO(data)) as f:
        return f.read()


# ============================================================================
# 流式响应支持
# Streaming Response Support
# ============================================================================

def stream_large_response(data_generator: Generator, 
                         chunk_size: int = 8192,
                         compress: bool = True) -> Response:
    """
    流式响应生成器（适用于大数据集）
    
    Parameters:
    -----------
    data_generator : Generator
        数据生成器
    chunk_size : int
        分块大小（字节）
    compress : bool
        是否启用压缩
        
    Returns:
    --------
    Response : 流式响应对象
    """
    def generate():
        buffer = []
        buffer_size = 0
        
        for data in data_generator:
            # 将数据转换为字符串
            if isinstance(data, dict):
                import json
                data_str = json.dumps(data) + '\n'
            else:
                data_str = str(data)
            
            data_bytes = data_str.encode('utf-8')
            buffer.append(data_bytes)
            buffer_size += len(data_bytes)
            
            # 当缓冲区达到chunk_size时，发送数据
            if buffer_size >= chunk_size:
                chunk = b''.join(buffer)
                
                if compress:
                    chunk = gzip_compress(chunk)
                
                yield chunk
                
                # 清空缓冲区
                buffer = []
                buffer_size = 0
        
        # 发送剩余数据
        if buffer:
            chunk = b''.join(buffer)
            
            if compress:
                chunk = gzip_compress(chunk)
            
            yield chunk
    
    response = Response(stream_with_context(generate()))
    response.headers['Content-Type'] = 'application/x-ndjson'  # Newline Delimited JSON
    
    if compress:
        response.headers['Content-Encoding'] = 'gzip'
    
    return response


def paginate_response(data: list, 
                      page: int = 1, 
                      per_page: int = 100,
                      max_per_page: int = 1000) -> dict:
    """
    分页响应优化
    
    Parameters:
    -----------
    data : list
        数据列表
    page : int
        页码（从1开始）
    per_page : int
        每页数量
    max_per_page : int
        最大每页数量
        
    Returns:
    --------
    dict : 分页后的响应数据
    """
    # 限制每页数量
    per_page = min(per_page, max_per_page)
    
    # 计算总页数
    total_items = len(data)
    total_pages = (total_items + per_page - 1) // per_page
    
    # 计算起始和结束索引
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # 获取当前页数据
    page_data = data[start_idx:end_idx]
    
    # 构建分页响应
    return {
        'data': page_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_page': page - 1 if page > 1 else None,
            'next_page': page + 1 if page < total_pages else None
        }
    }


# ============================================================================
# 装饰器：自动压缩响应
# Decorator: Auto Compress Response
# ============================================================================

def compress_response(min_size: int = 1024, level: int = 6):
    """
    自动压缩响应装饰器
    
    Parameters:
    -----------
    min_size : int
        最小压缩大小（字节）
    level : int
        压缩级别 (1-9)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 执行函数获取响应
            response = func(*args, **kwargs)
            
            # 检查是否为Response对象
            if not isinstance(response, Response):
                from flask import jsonify
                response = jsonify(response)
            
            # 检查客户端是否支持gzip
            accept_encoding = request.headers.get('Accept-Encoding', '')
            if 'gzip' not in accept_encoding.lower():
                return response
            
            # 检查响应是否已经压缩
            if response.headers.get('Content-Encoding'):
                return response
            
            # 获取响应数据
            response_data = response.get_data()
            
            # 检查大小
            if len(response_data) < min_size:
                return response
            
            # 压缩响应
            try:
                compressed = gzip_compress(response_data, level)
                
                if len(compressed) < len(response_data):
                    response.set_data(compressed)
                    response.headers['Content-Encoding'] = 'gzip'
                    response.headers['Content-Length'] = str(len(compressed))
                    response.headers['Vary'] = 'Accept-Encoding'
                    
                    logger.debug(
                        f"[{func.__name__}] 响应已压缩: "
                        f"{len(response_data)}B -> {len(compressed)}B"
                    )
            
            except Exception as e:
                logger.error(f"响应压缩失败: {e}")
            
            return response
        
        return wrapper
    return decorator


# ============================================================================
# 示例使用
# Usage Example
# ============================================================================

if __name__ == '__main__':
    from flask import Flask, jsonify
    
    app = Flask(__name__)
    
    # 注册压缩中间件
    compression = CompressionMiddleware(
        app,
        min_size=500,  # 500字节以上才压缩
        compression_level=6
    )
    
    @app.route('/api/large-data')
    def large_data():
        """大数据集示例"""
        data = [{'id': i, 'value': f'data_{i}'} for i in range(1000)]
        return jsonify(data)
    
    @app.route('/api/stream')
    def stream_data():
        """流式响应示例"""
        def generate_data():
            for i in range(1000):
                yield {'id': i, 'value': f'stream_{i}'}
        
        return stream_large_response(generate_data(), chunk_size=4096)
    
    @app.route('/api/paginated')
    def paginated_data():
        """分页响应示例"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        all_data = [{'id': i, 'value': f'item_{i}'} for i in range(500)]
        
        result = paginate_response(all_data, page, per_page)
        return jsonify(result)
    
    print("压缩中间件测试服务器已启动")
    print("访问 http://localhost:5000/api/large-data 测试压缩")
    print("访问 http://localhost:5000/api/stream 测试流式响应")
    print("访问 http://localhost:5000/api/paginated?page=1&per_page=20 测试分页")
    
    app.run(debug=True)
