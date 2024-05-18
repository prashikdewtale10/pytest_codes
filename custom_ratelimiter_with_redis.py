import aioredis
from datetime import datetime, timedelta
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.exceptions import HTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from esmerald import Esmerald

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable, redis_url: str, rate_limit: int, window_seconds: int):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        self.redis_url = redis_url
        self.redis = aioredis.from_url(redis_url, decode_responses=True)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        key = f"ratelimit:{client_ip}"
        
        # Retrieve the current count and expiry time from Redis
        current_count = await self.redis.get(key)
        if current_count is None:
            # Set the count and expiry if not set
            await self.redis.set(key, 1, ex=self.window_seconds)
            current_count = 1
        else:
            # Increment the count
            current_count = int(current_count)
            if current_count < self.rate_limit:
                await self.redis.incr(key)
            else:
                raise HTTPException(
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
        
        response = await call_next(request)
        return response

# Esmerald Application Setup
app = Esmerald()
app.add_middleware(
    RateLimiterMiddleware, 
    redis_url="redis://localhost:6379", 
    rate_limit=100, 
    window_seconds=60
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
