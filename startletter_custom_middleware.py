from datetime import datetime, timedelta
from typing import Callable, Dict, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.exceptions import HTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable, rate_limit: int, window_seconds: int):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        self.clients: Dict[str, Dict[str, Optional[datetime, int]]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        current_time = datetime.now()

        if client_ip not in self.clients:
            self.clients[client_ip] = {
                "count": 1,
                "expires_at": current_time + timedelta(seconds=self.window_seconds),
            }
        else:
            client_data = self.clients[client_ip]
            if current_time > client_data["expires_at"]:
                client_data["count"] = 1
                client_data["expires_at"] = current_time + timedelta(seconds=self.window_seconds)
            else:
                client_data["count"] += 1

        if self.clients[client_ip]["count"] > self.rate_limit:
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later."
            )

        response = await call_next(request)
        return response

# Esmerald Application Setup
from esmerald import Esmerald

app = Esmerald()
app.add_middleware(RateLimiterMiddleware, rate_limit=100, window_seconds=60)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
