"""API Key authentication middleware."""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce API key authentication.
    
    Checks for X-API-Key header on all requests except:
    - /health (public health check)
    - /docs (API documentation)
    - /openapi.json (API schema)
    
    Enable in config with:
    - REQUIRE_API_KEY=true
    - API_KEYS=key1,key2,key3
    """
    
    EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}
    
    async def dispatch(self, request: Request, call_next):
        """Process request and check API key."""
        settings = get_settings()
        
        # Skip auth if not enabled
        if not settings.require_api_key:
            return await call_next(request)
        
        # Skip auth for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Check for API key header
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Missing API key",
                    "detail": "Include X-API-Key header with a valid API key",
                },
            )
        
        # Validate API key
        valid_keys = settings.get_valid_api_keys()
        
        if not valid_keys:
            # Config error: auth enabled but no keys configured
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Server misconfiguration",
                    "detail": "API key auth enabled but no valid keys configured",
                },
            )
        
        if api_key not in valid_keys:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Invalid API key",
                    "detail": "The provided API key is not authorized",
                },
            )
        
        # API key valid, continue
        return await call_next(request)
