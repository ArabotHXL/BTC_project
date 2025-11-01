/**
 * In-memory LRU cache with TTL support
 */

import NodeCache from 'node-cache';

export class CacheManager {
  private cache: NodeCache;

  constructor(defaultTTL: number = 60) {
    this.cache = new NodeCache({
      stdTTL: defaultTTL,
      checkperiod: 120,
      useClones: false
    });
  }

  get<T>(key: string): T | undefined {
    return this.cache.get<T>(key);
  }

  set<T>(key: string, value: T, ttl?: number): boolean {
    return this.cache.set(key, value, ttl || 0);
  }

  has(key: string): boolean {
    return this.cache.has(key);
  }

  del(key: string): number {
    return this.cache.del(key);
  }

  flush(): void {
    this.cache.flushAll();
  }

  getStats() {
    return this.cache.getStats();
  }
}

export const cacheManager = new CacheManager();
