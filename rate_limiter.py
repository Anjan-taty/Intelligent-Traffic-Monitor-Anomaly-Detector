import os
import time
import logging
from typing import Tuple, Dict
from collections import deque
from threading import Lock

logger = logging.getLogger("traffic_monitor.rate_limiter")

# Lua script for atomic sliding window rate limiting in Redis
# KEYS[1]: rate limit key, e.g. "rate_limit:{ip}"
# ARGV[1]: current timestamp in milliseconds
# ARGV[2]: window size in milliseconds
# ARGV[3]: max allowed requests in window
SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local clear_before = now - window

redis.call('ZREMRANGEBYSCORE', key, '-inf', clear_before)
local current_requests = redis.call('ZCARD', key)

if current_requests < limit then
    redis.call('ZADD', key, now, now)
    redis.call('PEXPIRE', key, window)
    return {1, limit - current_requests - 1, 0}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = 1
    if #oldest > 0 then
        local oldest_ts = tonumber(oldest[2])
        retry_after = math.ceil(((oldest_ts + window) - now) / 1000)
        if retry_after < 1 then retry_after = 1 end
    end
    return {0, 0, retry_after}
end
"""

class InMemorySlidingWindow:
    """Thread-safe in-memory fallback rate limiter when Redis is offline."""
    def __init__(self):
        self._history: Dict[str, deque] = {}
        self._lock = Lock()

    def check(self, ip: str, limit: int, window_seconds: float) -> Tuple[bool, int, int]:
        now = time.time()
        clear_before = now - window_seconds
        with self._lock:
            if ip not in self._history:
                self._history[ip] = deque()
            q = self._history[ip]
            while q and q[0] <= clear_before:
                q.popleft()
            
            if len(q) < limit:
                q.append(now)
                remaining = limit - len(q)
                return True, remaining, 0
            else:
                oldest = q[0]
                retry_after = max(1, int((oldest + window_seconds) - now))
                return False, 0, retry_after

class EnterpriseRateLimiter:
    """
    Production-grade Rate Limiter:
    - Primary: Atomic Redis Sliding Window with Lua scripts (Zero race conditions).
    - Secondary: Resilient in-memory sliding window fallback.
    - Features: Dynamic tiering (Normal, Throttled, Quarantined/Blocked).
    """
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = None
        self._lua_sha = None
        self._memory_limiter = InMemorySlidingWindow()
        self._manual_blocked_ips: Dict[str, float] = {} # ip -> expire_timestamp
        self._throttled_ips: Dict[str, float] = {}     # ip -> expire_timestamp
        self._init_redis()

    def _init_redis(self):
        try:
            import redis
            client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            client.ping()
            self.redis_client = client
            self._lua_sha = self.redis_client.script_load(SLIDING_WINDOW_LUA)
            logger.info("Successfully connected to Redis. Distributed sliding window active.")
        except Exception as e:
            logger.warning(f"Redis not available ({e}). Using in-memory Sliding Window fallback.")
            self.redis_client = None

    def block_ip(self, ip: str, duration_seconds: int = 300, reason: str = "Manual Block"):
        """Blocks an IP entirely for duration_seconds."""
        expire_at = time.time() + duration_seconds
        self._manual_blocked_ips[ip] = expire_at
        if self.redis_client:
            try:
                self.redis_client.setex(f"blocked_ip:{ip}", duration_seconds, reason)
            except Exception:
                pass

    def throttle_ip(self, ip: str, duration_seconds: int = 180):
        """Demotes IP to a restricted throttle tier."""
        self._throttled_ips[ip] = time.time() + duration_seconds
        if self.redis_client:
            try:
                self.redis_client.setex(f"throttled_ip:{ip}", duration_seconds, "1")
            except Exception:
                pass

    def unblock_ip(self, ip: str):
        self._manual_blocked_ips.pop(ip, None)
        self._throttled_ips.pop(ip, None)
        if self.redis_client:
            try:
                self.redis_client.delete(f"blocked_ip:{ip}")
                self.redis_client.delete(f"throttled_ip:{ip}")
            except Exception:
                pass

    def is_blocked(self, ip: str) -> bool:
        # Check local cache first
        exp = self._manual_blocked_ips.get(ip)
        if exp:
            if time.time() < exp:
                return True
            else:
                del self._manual_blocked_ips[ip]

        if self.redis_client:
            try:
                return bool(self.redis_client.exists(f"blocked_ip:{ip}"))
            except Exception:
                pass
        return False

    def is_throttled(self, ip: str) -> bool:
        exp = self._throttled_ips.get(ip)
        if exp:
            if time.time() < exp:
                return True
            else:
                del self._throttled_ips[ip]

        if self.redis_client:
            try:
                return bool(self.redis_client.exists(f"throttled_ip:{ip}"))
            except Exception:
                pass
        return False

    def check_rate_limit(
        self, 
        ip: str, 
        default_limit: int = 60, 
        window_seconds: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Checks whether the given IP is allowed.
        Returns:
            Tuple[allowed (bool), remaining (int), retry_after_seconds (int)]
        """
        if self.is_blocked(ip):
            return False, 0, 300

        # Determine tier limits
        effective_limit = default_limit
        if self.is_throttled(ip):
            effective_limit = max(5, int(default_limit / 5))  # 80% throttle penalty

        # If Redis is active, run atomic Lua script
        if self.redis_client and self._lua_sha:
            try:
                now_ms = int(time.time() * 1000)
                window_ms = window_seconds * 1000
                key = f"rate_limit:{ip}"
                res = self.redis_client.evalsha(self._lua_sha, 1, key, now_ms, window_ms, effective_limit)
                allowed = bool(res[0] == 1)
                remaining = int(res[1])
                retry_after = int(res[2])
                return allowed, remaining, retry_after
            except Exception as e:
                logger.debug(f"Redis check failed ({e}), falling back to in-memory.")

        # In-memory fallback
        return self._memory_limiter.check(ip, effective_limit, window_seconds)

# Singleton instance
rate_limiter = EnterpriseRateLimiter()
