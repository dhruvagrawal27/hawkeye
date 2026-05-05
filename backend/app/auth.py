"""Keycloak JWT verification middleware."""

from __future__ import annotations

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()
_bearer = HTTPBearer(auto_error=False)

_JWKS_CACHE: dict | None = None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
async def _fetch_jwks() -> dict:
    global _JWKS_CACHE
    if _JWKS_CACHE:
        return _JWKS_CACHE
    url = (
        f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
        "/protocol/openid-connect/certs"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _JWKS_CACHE = resp.json()
        return _JWKS_CACHE


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Return the decoded token payload. Raise 401 if invalid."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    try:
        jwks = await _fetch_jwks()
        # Decode header to find kid
        unverified_header = jwt.get_unverified_header(token)
        key = next(
            (k for k in jwks["keys"] if k["kid"] == unverified_header.get("kid")),
            None,
        )
        if key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown key id")
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
            options={"verify_aud": False},  # Keycloak may use different aud
        )
        return payload
    except JWTError as exc:
        log.warning("jwt_invalid", error=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_role(*roles: str):
    """Return a dependency that enforces at least one of the given roles."""
    async def _check(payload: dict = Depends(verify_token)) -> dict:
        realm_roles: list[str] = (
            payload.get("realm_access", {}).get("roles", [])
        )
        if not any(r in realm_roles for r in roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return payload
    return _check


# Convenience shortcuts
require_analyst = require_role("analyst", "supervisor", "admin")
require_supervisor = require_role("supervisor", "admin")
require_admin = require_role("admin")
