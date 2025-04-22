from collections import defaultdict
import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException
import os

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[Tuple[str, str], list] = defaultdict(list)
    
    def is_rate_limited(self, ip: str, path: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        
        # Clean up old requests
        self.requests[(ip, path)] = [
            req_time for req_time in self.requests[(ip, path)]
            if req_time > minute_ago
        ]
        
        # Check if we're over the limit
        if len(self.requests[(ip, path)]) >= self.requests_per_minute:
            return True
        
        # Add new request
        self.requests[(ip, path)].append(now)
        return False

rate_limiter = RateLimiter(
    requests_per_minute=int(os.getenv('RATE_LIMIT', '60'))
)

async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)
    
    client_ip = request.client.host
    path = request.url.path
    
    if rate_limiter.is_rate_limited(client_ip, path):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )
    
    return await call_next(request)