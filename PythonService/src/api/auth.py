"""
API Authentication and Authorization
Simple API key-based authentication
"""

import os
from typing import Optional, List
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel


class APIKeyConfig:
    """API Key configuration and management"""

    def __init__(self):
        # Load API keys from environment variable
        # Format: TYPELESS_API_KEYS=key1,key2,key3
        env_keys = os.getenv("TYPELESS_API_KEYS", "")

        # Default key for development
        self.api_keys = set(env_keys.split(",")) if env_keys else {"dev-key-12345"}

        # Admin keys (can manage other keys)
        admin_keys = os.getenv("TYPELESS_ADMIN_KEYS", "")
        self.admin_keys = set(admin_keys.split(",")) if admin_keys else {"admin-key-12345"}

    def validate_key(self, api_key: str) -> bool:
        """Validate an API key"""
        return api_key in self.api_keys

    def is_admin_key(self, api_key: str) -> bool:
        """Check if key is an admin key"""
        return api_key in self.admin_keys

    def add_key(self, api_key: str, is_admin: bool = False):
        """Add a new API key (admin only)"""
        if is_admin:
            self.admin_keys.add(api_key)
        self.api_keys.add(api_key)

    def remove_key(self, api_key: str):
        """Remove an API key (admin only)"""
        if api_key in self.api_keys:
            self.api_keys.remove(api_key)
        if api_key in self.admin_keys:
            self.admin_keys.remove(api_key)

    def list_keys(self, include_admin: bool = False) -> List[str]:
        """List all API keys (admin only)"""
        if include_admin:
            return list(self.admin_keys)
        return list(self.api_keys)


# Global configuration
api_key_config = APIKeyConfig()


# Security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: Optional[str] = Security(api_key_header)):
    """
    Validate API key from header

    Usage:
        @router.get("/protected")
        async def protected_endpoint(api_key: str = Depends(get_api_key)):
            ...
    """

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing. Please provide X-API-Key header.",
        )

    if not api_key_config.validate_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key


async def get_admin_api_key(api_key: Optional[str] = Security(api_key_header)):
    """
    Validate admin API key from header

    Usage:
        @router.post("/admin/keys")
        async def admin_endpoint(api_key: str = Depends(get_admin_api_key)):
            ...
    """

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key is missing",
        )

    if not api_key_config.is_admin_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return api_key


# Optional authentication (allows public access with rate limits)
async def get_optional_api_key(api_key: Optional[str] = Security(api_key_header)):
    """
    Optional API key validation
    Returns the key if valid, None otherwise
    Used to differentiate authenticated vs unauthenticated requests
    """

    if api_key and api_key_config.validate_key(api_key):
        return api_key
    return None


class AuthConfig(BaseModel):
    """Authentication configuration"""
    enabled: bool = True
    require_auth: bool = False  # If False, public access with rate limits
    default_keys: List[str] = ["dev-key-12345"]
    admin_keys: List[str] = ["admin-key-12345"]


class KeyManagementResponse(BaseModel):
    """Response for key management operations"""
    success: bool
    message: str
    key_count: Optional[int] = None
    keys: Optional[List[str]] = None


def get_auth_config() -> AuthConfig:
    """Get current authentication configuration"""
    return AuthConfig(
        enabled=os.getenv("TYPELESS_AUTH_ENABLED", "true").lower() == "true",
        require_auth=os.getenv("TYPELESS_REQUIRE_AUTH", "false").lower() == "true",
        default_keys=list(api_key_config.api_keys) if len(api_key_config.api_keys) <= 5 else [],
        admin_keys=list(api_key_config.admin_keys) if len(api_key_config.admin_keys) <= 5 else []
    )
