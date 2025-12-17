/**
 * 前端缓存优化模块
 * 减少重复API调用，提升页面加载速度
 */

class FrontendCache {
    constructor(defaultTTL = 30000) { // 默认30秒缓存
        this.cache = new Map();
        this.defaultTTL = defaultTTL;
    }

    set(key, data, ttl = null) {
        const expiry = Date.now() + (ttl || this.defaultTTL);
        this.cache.set(key, {
            data: data,
            expiry: expiry
        });
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) {
            return null;
        }

        if (Date.now() > item.expiry) {
            this.cache.delete(key);
            return null;
        }

        return item.data;
    }

    clear() {
        this.cache.clear();
    }

    // 清理过期缓存
    cleanup() {
        const now = Date.now();
        for (const [key, value] of this.cache.entries()) {
            if (now > value.expiry) {
                this.cache.delete(key);
            }
        }
    }

    getStats() {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys())
        };
    }
}

// 全局缓存实例
const frontendCache = new FrontendCache();

// 包装fetch请求的缓存函数
async function cachedFetch(url, options = {}, ttl = null) {
    const cacheKey = `fetch_${url}_${JSON.stringify(options)}`;
    
    // 尝试从缓存获取
    const cached = frontendCache.get(cacheKey);
    if (cached) {
        console.log(`✅ 缓存命中: ${url}`);
        return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(cached)
        });
    }

    // 缓存未命中，发起请求
    try {
        const response = await fetch(url, options);
        if (response.ok) {
            const data = await response.json();
            // 缓存响应数据
            frontendCache.set(cacheKey, data, ttl);
            console.log(`📥 数据已缓存: ${url}`);
            
            return {
                ok: true,
                json: () => Promise.resolve(data)
            };
        }
        return response;
    } catch (error) {
        console.error(`❌ 请求失败: ${url}`, error);
        throw error;
    }
}

// 批量预加载关键数据
async function preloadCriticalData() {
    const criticalEndpoints = [
        '/api/network-data',
        '/api/get-btc-price',
        '/api/get_miners_data'
    ];

    console.log('🚀 开始预加载关键数据...');
    
    const promises = criticalEndpoints.map(endpoint => 
        cachedFetch(endpoint, {}, 60000) // 预加载数据缓存60秒
            .catch(error => console.warn(`预加载失败 ${endpoint}:`, error))
    );

    await Promise.allSettled(promises);
    console.log('✅ 关键数据预加载完成');
}

// 定期清理过期缓存
setInterval(() => {
    frontendCache.cleanup();
}, 60000); // 每分钟清理一次

// 页面加载时预加载数据
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', preloadCriticalData);
} else {
    preloadCriticalData();
}

// 导出供其他模块使用
window.frontendCache = frontendCache;
window.cachedFetch = cachedFetch;
window.preloadCriticalData = preloadCriticalData;