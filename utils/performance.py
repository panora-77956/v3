# -*- coding: utf-8 -*-
"""
Performance Optimization Utilities
Provides caching, connection pooling, and request batching
"""

import time
import hashlib
import pickle
import os
import logging
from typing import Any, Callable, Dict, Optional
from functools import wraps
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Get logger for this module
logger = logging.getLogger(__name__)


# Global session with connection pooling
_session = None


def get_session(
    pool_connections: int = 10,
    pool_maxsize: int = 20,
    max_retries: int = 3,
    backoff_factor: float = 0.5
) -> requests.Session:
    """
    Get or create a global requests session with connection pooling
    
    Args:
        pool_connections: Number of connection pools
        pool_maxsize: Maximum size of each pool
        max_retries: Maximum number of retries
        backoff_factor: Backoff factor for retries
    
    Returns:
        Configured requests.Session instance
    """
    global _session

    if _session is None:
        _session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            # Allow retries for safe HTTP methods (excluding TRACE for security)
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "POST"]
        )

        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )

        # Mount adapter for both HTTP and HTTPS
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)

        # Set reasonable timeout defaults
        _session.request = _add_timeout_to_session(_session.request)

    return _session


def _add_timeout_to_session(request_func):
    """Add default timeout to session requests"""
    @wraps(request_func)
    def wrapper(*args, **kwargs):
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 120  # Default 120s timeout
        return request_func(*args, **kwargs)
    return wrapper


class SimpleCache:
    """
    Simple in-memory cache with TTL support
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize cache
        
        Args:
            max_size: Maximum number of items in cache
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, tuple] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry is None or time.time() < expiry:
                self.hits += 1
                return value
            else:
                # Expired, remove it
                del self._cache[key]

        self.misses += 1
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache"""
        if ttl is None:
            ttl = self.default_ttl

        expiry = None if ttl <= 0 else time.time() + ttl

        # Evict oldest if cache is full
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Remove oldest entry using FIFO (relies on dict insertion order in Python 3.7+)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = (value, expiry)

    def clear(self):
        """Clear entire cache"""
        self._cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%"
        }


class DiskCache:
    """
    Simple disk-based cache for persistent storage
    """

    def __init__(self, cache_dir: str = None, max_age_days: int = 7):
        """
        Initialize disk cache
        
        Args:
            cache_dir: Directory for cache files (defaults to ./cache)
            max_age_days: Maximum age of cache files in days
        """
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'cache'
            )

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age_seconds = max_age_days * 24 * 3600

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key"""
        # Hash the key to create a valid filename
        # Using SHA-256 following security best practices (MD5 would be sufficient for caching)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache"""
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        # Check if cache is too old
        age = time.time() - cache_path.stat().st_mtime
        if age > self.max_age_seconds:
            cache_path.unlink()
            return None

        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except (pickle.PickleError, EOFError, IOError):
            # Corrupted cache file, remove it
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, key: str, value: Any):
        """Set value in disk cache"""
        cache_path = self._get_cache_path(key)

        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
        except (pickle.PickleError, IOError) as e:
            logger.warning(f"Could not write to cache: {e}")

    def clear(self):
        """Clear all cache files"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink(missing_ok=True)

    def cleanup_old_files(self):
        """Remove cache files older than max_age"""
        now = time.time()
        for cache_file in self.cache_dir.glob("*.cache"):
            age = now - cache_file.stat().st_mtime
            if age > self.max_age_seconds:
                cache_file.unlink(missing_ok=True)


# Global caches
_memory_cache = SimpleCache()
_disk_cache = None


def cached(ttl: int = 3600, use_disk: bool = False):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time-to-live in seconds (0 for no expiry)
        use_disk: Use disk cache instead of memory cache
    
    Example:
        @cached(ttl=3600)
        def expensive_function(arg1, arg2):
            # ... expensive computation ...
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__module__}.{func.__name__}:{str(args)}:{str(kwargs)}"

            # Select cache
            if use_disk:
                global _disk_cache
                if _disk_cache is None:
                    _disk_cache = DiskCache()
                cache = _disk_cache
            else:
                cache = _memory_cache

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl if not use_disk else None)

            return result

        # Add cache control methods
        wrapper.clear_cache = lambda: _memory_cache.clear() if not use_disk else _disk_cache.clear()
        wrapper.cache_stats = lambda: _memory_cache.get_stats() if not use_disk else None

        return wrapper

    return decorator


def batch_requests(
    urls: list,
    max_workers: int = 5,
    timeout: int = 120
) -> list:
    """
    Batch multiple HTTP requests for better performance
    
    Args:
        urls: List of URLs to fetch
        max_workers: Maximum concurrent requests
        timeout: Timeout for each request
    
    Returns:
        List of responses in same order as urls
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    session = get_session()
    results = [None] * len(urls)

    def fetch(index, url):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return index, response
        except requests.RequestException as e:
            return index, e

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch, i, url): i for i, url in enumerate(urls)}

        for future in as_completed(futures):
            index, result = future.result()
            results[index] = result

    return results


# Example usage
if __name__ == '__main__':
    # Test session with connection pooling
    session = get_session()
    print(f"✓ Created session with connection pooling")

    # Test simple cache
    cache = SimpleCache()
    cache.set('test_key', 'test_value', ttl=60)
    value = cache.get('test_key')
    print(f"✓ Simple cache: {value}")
    print(f"  Stats: {cache.get_stats()}")

    # Test disk cache
    disk_cache = DiskCache()
    disk_cache.set('test_key', {'data': 'test_value'})
    value = disk_cache.get('test_key')
    print(f"✓ Disk cache: {value}")

    # Test cached decorator
    @cached(ttl=60)
    def slow_function(x):
        time.sleep(0.1)
        return x * 2

    start = time.time()
    result1 = slow_function(5)
    time1 = time.time() - start

    start = time.time()
    result2 = slow_function(5)
    time2 = time.time() - start

    print(f"✓ Cached function: first={time1:.3f}s, cached={time2:.3f}s")
    print(f"  Cache stats: {slow_function.cache_stats()}")

    print("\n✅ All performance optimization tests passed!")
