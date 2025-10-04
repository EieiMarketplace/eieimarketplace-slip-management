import os
import json
import asyncio
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any

import aiohttp
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:7001").rstrip("/")
# Optional internal/Docker DNS (e.g., http://user-management:7001)
AUTH_SERVICE_INTERNAL_URL = os.getenv("AUTH_SERVICE_INTERNAL_URL", "").rstrip("/")
BYPASS_AUTH = os.getenv("BYPASS_AUTH", "false").lower() == "true"

# Add your docker-compose service DNS here if you have it:
DEFAULT_DOCKER_SERVICE = "http://user-management:7001"

# FastAPI security dependency
security = HTTPBearer(auto_error=True)


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
@dataclass
class UserInfo:
    user_id: str
    role: str
    token: str


# -----------------------------------------------------------------------------
# URL candidates
# -----------------------------------------------------------------------------
def _candidate_urls(path: str) -> List[str]:
    """Build a list of candidate base URLs with the given path appended."""
    bases = [
        AUTH_SERVICE_URL,
        AUTH_SERVICE_INTERNAL_URL,
        DEFAULT_DOCKER_SERVICE,
        "http://host.docker.internal:7001",  # Works on Docker Desktop
        "http://127.0.0.1:7001",             # Only works if service is on the same host namespace
        "http://localhost:7001",
    ]
    return [f"{b}{path}" for b in bases if b]


# -----------------------------------------------------------------------------
# HTTP helpers
# -----------------------------------------------------------------------------
async def _request_json(
    method: str,
    url: str,
    headers: Dict[str, str],
    payload: Optional[Dict[str, Any]] = None,
    timeout_sec: float = 10.0,
) -> Tuple[int, str, Optional[Dict[str, Any]]]:
    """Make an HTTP request and return (status, text, json_or_none) without double-reading."""
    timeout = aiohttp.ClientTimeout(total=timeout_sec)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        req = session.post if method.upper() == "POST" else session.get
        async with req(url, headers=headers, json=payload) as resp:
            text = await resp.text()
            data: Optional[Dict[str, Any]] = None
            # Parse JSON leniently (even if server Content-Type is wrong)
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = None
            return resp.status, text, data


# -----------------------------------------------------------------------------
# Auth service calls
# -----------------------------------------------------------------------------
async def get_user_from_token(token: str) -> UserInfo:
    """Resolve user info via GET /users/info with Bearer token."""
    headers = {"Authorization": f"Bearer {token}"}
    for url in _candidate_urls("/users/info"):
        try:
            status, _text, data = await _request_json("GET", url, headers=headers, timeout_sec=10)
            if status == 200 and isinstance(data, dict):
                user_id = str(data.get("id", "")).strip()
                role = str(data.get("role", "")).strip()
                if not user_id or not role:
                    raise HTTPException(status_code=502, detail="Malformed user info from auth service")
                return UserInfo(user_id=user_id, role=role, token=token)

            if status == 401:
                raise HTTPException(status_code=401, detail="Invalid or expired token")

            # Non-200/401: try next candidate
            continue

        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue
        except HTTPException:
            raise
        except Exception:
            continue

    if BYPASS_AUTH:
        return UserInfo(user_id="dev-user", role="organizer", token=token)

    raise HTTPException(status_code=503, detail="Authentication service is currently unavailable")


async def call_auth_service(token: str, user_id: str, required_role: str) -> bool:
    """Verify authorization via POST /users/verify with Bearer token."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"uuid": user_id, "required_role": required_role}

    for url in _candidate_urls("/users/verify"):
        try:
            status, _text, data = await _request_json("POST", url, headers=headers, payload=payload, timeout_sec=10)
            if status == 200 and isinstance(data, dict):
                return bool(data.get("verify", False))
            if status == 401:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            if status == 403:
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            # Other statuses: try next candidate
            continue

        except (aiohttp.ClientError, asyncio.TimeoutError):
            continue
        except HTTPException:
            raise
        except Exception:
            continue

    if BYPASS_AUTH:
        return True

    raise HTTPException(status_code=503, detail="Authentication service is currently unavailable")


# -----------------------------------------------------------------------------
# FastAPI dependencies
# -----------------------------------------------------------------------------
def require_role(required_role: str):
    """Factory for a dependency that ensures the caller has a given role."""
    async def _dep(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
        token = credentials.credentials
        user = await get_user_from_token(token)
        authorized = await call_auth_service(token, user.user_id, required_role)
        if not authorized:
            raise HTTPException(status_code=403, detail=f"{required_role.capitalize()} role required")
        return user
    return _dep


# Shortcut for organizer-only endpoints
require_organizer_auth = require_role("organizer")


async def get_optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[UserInfo]:
    """Return UserInfo if token present & valid, else None (no exceptions)."""
    if not credentials:
        return None
    try:
        return await get_user_from_token(credentials.credentials)
    except HTTPException:
        return None
