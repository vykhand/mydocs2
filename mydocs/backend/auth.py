"""Microsoft Entra ID (Azure AD) JWT validation for FastAPI."""

import os
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from tinystructlog import get_logger

logger = get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)

# Cached JWKS data
_jwks_cache: dict[str, Any] | None = None


def _get_settings() -> tuple[str, str, str]:
    """Return (tenant_id, client_id, issuer) from environment."""
    tenant_id = os.getenv("ENTRA_TENANT_ID", "")
    client_id = os.getenv("ENTRA_CLIENT_ID", "")
    issuer = os.getenv(
        "ENTRA_ISSUER",
        f"https://login.microsoftonline.com/{tenant_id}/v2.0",
    )
    return tenant_id, client_id, issuer


async def _get_jwks() -> dict[str, Any]:
    """Fetch and cache the JWKS from Microsoft's well-known endpoint."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    tenant_id, _, _ = _get_settings()
    url = (
        f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
    _jwks_cache = resp.json()
    return _jwks_cache


def _find_rsa_key(jwks: dict[str, Any], kid: str) -> dict[str, str] | None:
    """Find the signing key matching the token's kid."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """Validate the Bearer token and return the decoded claims.

    When ENTRA_TENANT_ID is unset (local dev), authentication is skipped
    and a stub user is returned.
    """
    tenant_id, client_id, issuer = _get_settings()

    # If Entra is not configured, skip auth (local development)
    if not tenant_id:
        return {"sub": "local-dev", "name": "Local Developer"}

    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    token = creds.credentials
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
        )

    jwks = await _get_jwks()
    rsa_key = _find_rsa_key(jwks, unverified_header.get("kid", ""))

    if rsa_key is None:
        # Key not found — JWKS may have rotated. Bust cache and retry once.
        global _jwks_cache
        _jwks_cache = None
        jwks = await _get_jwks()
        rsa_key = _find_rsa_key(jwks, unverified_header.get("kid", ""))
        if rsa_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find signing key",
            )

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)

    # Accept both the raw client ID and the Application ID URI as valid
    # audiences. MSAL SPA requests api://{client_id}/access_as_user which
    # produces tokens with aud=api://{client_id}.
    valid_audiences = [client_id, f"api://{client_id}"]

    # Accept both v1 (sts.windows.net) and v2 (login.microsoftonline.com)
    # issuer formats. Token version depends on the app manifest's
    # accessTokenAcceptedVersion setting.
    valid_issuers = [
        issuer,
        f"https://sts.windows.net/{tenant_id}/",
    ]

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=valid_audiences,
            issuer=valid_issuers,
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {exc}",
        )

    return payload
