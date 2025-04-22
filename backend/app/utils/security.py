from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from collections import defaultdict
from typing import Dict, Tuple
import os

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[Tuple[str, str], list] = defaultdict(list)
    
    def is_allowed(self, ip: str, path: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[(ip, path)] = [
            req_time for req_time in self.requests[(ip, path)]
            if req_time > minute_ago
        ]
        
        # Check if under limit
        if len(self.requests[(ip, path)]) >= self.requests_per_minute:
            return False
        
        # Add new request
        self.requests[(ip, path)].append(now)
        return True

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        rate_limit_requests: int = 60,
        allowed_hosts: list = None,
        enable_cors: bool = True
    ):
        super().__init__(app)
        self.rate_limiter = RateLimiter(rate_limit_requests)
        self.allowed_hosts = allowed_hosts or ["localhost", "127.0.0.1"]
        self.enable_cors = enable_cors
        
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "0.0.0.0"
        
        # Basic host validation
        host = request.headers.get("host", "").split(":")[0]
        if host not in self.allowed_hosts:
            logger.warning(f"Blocked request from unauthorized host: {host}")
            raise HTTPException(status_code=403, detail="Host not allowed")
        
        # Rate limiting
        if not self.rate_limiter.is_allowed(client_ip, request.url.path):
            logger.warning(f"Rate limit exceeded for IP {client_ip} on path {request.url.path}")
            raise HTTPException(status_code=429, detail="Too many requests")
        
        # Add security headers
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        if self.enable_cors:
            # Add CORS headers only if enabled
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response

class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.api_key = os.getenv("API_KEY")
    
    async def dispatch(self, request: Request, call_next):
        if self.api_key:  # Only check if API key is configured
            api_key = request.headers.get("X-API-Key")
            if not api_key or api_key != self.api_key:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or missing API key"
                )
        return await call_next(request)