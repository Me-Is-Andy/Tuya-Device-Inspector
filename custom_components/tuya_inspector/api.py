"""Read-only Tuya Cloud client for the inspector.

Deliberately limited to GET requests: this integration exists to read a
device's description, never to control it.
"""
import hashlib
import hmac
import logging
from datetime import timedelta

import aiohttp
from homeassistant.util import dt as dt_util

from .const import (
    DEVICE_LIST_PATH,
    TOKEN_PATH,
    device_info_path,
    model_path,
    properties_path,
    specification_path,
)

_LOGGER = logging.getLogger(__name__)

EMPTY_BODY_SHA256 = hashlib.sha256(b"").hexdigest()


class TuyaApiError(Exception):
    """Raised when the Tuya Cloud API returns an error."""


class TuyaInspectorApi:
    """Minimal Tuya Cloud client using the post-2021 signature algorithm."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        access_id: str,
        access_secret: str,
    ):
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._access_id = access_id
        self._access_secret = access_secret
        self._access_token = None
        self._token_expires_at = None

    def _sign(self, timestamp: str, path: str, access_token: str) -> str:
        """Build the signature Tuya requires.

        stringToSign = METHOD \n SHA256(body) \n <optional headers> \n path
        str          = client_id + access_token + t + nonce + stringToSign
        sign         = HMAC-SHA256(str, secret).upper()

        Every request here is a GET with an empty body, so the body hash is
        constant.
        """
        string_to_sign = f"GET\n{EMPTY_BODY_SHA256}\n\n{path}"
        payload = f"{self._access_id}{access_token}{timestamp}{string_to_sign}"
        return hmac.new(
            self._access_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest().upper()

    async def _get(self, path: str, use_token: bool = True) -> dict:
        timestamp = str(int(dt_util.utcnow().timestamp() * 1000))
        token = self._access_token if use_token else ""

        if use_token and not token:
            raise TuyaApiError("No access token available")

        headers = {
            "client_id": self._access_id,
            "sign_method": "HMAC-SHA256",
            "t": timestamp,
            "sign": self._sign(timestamp, path, token),
            "Content-Type": "application/json",
        }
        if use_token:
            headers["access_token"] = token

        async with self._session.get(
            f"{self._base_url}{path}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            data = await resp.json()

        if not data.get("success"):
            raise TuyaApiError(f"{data.get('code')}: {data.get('msg')}")
        return data

    async def _get_with_retry(self, path: str) -> dict:
        """Run a request, refetching the token once if it is rejected."""
        await self.async_ensure_token()
        try:
            return await self._get(path)
        except TuyaApiError as err:
            if "1010" in str(err) or "token" in str(err).lower():
                await self.async_fetch_token()
                return await self._get(path)
            raise

    async def async_ensure_token(self) -> None:
        if self._access_token and self._token_expires_at and dt_util.utcnow() < self._token_expires_at:
            return
        await self.async_fetch_token()

    async def async_fetch_token(self) -> None:
        """Get an access token.

        Tuya's expire_time is the REMAINING life of the token it returns, not
        a fresh lifetime, and it hands back the same token until that runs
        out. Renewing early just re-fetches the same nearly-dead token, so run
        it to expiry and let the retry above handle the edge.
        """
        data = await self._get(TOKEN_PATH, use_token=False)
        result = data.get("result", {})
        self._access_token = result.get("access_token")
        remaining = result.get("expire_time") or result.get("expires_in") or 7200
        self._token_expires_at = dt_util.utcnow() + timedelta(
            seconds=max(int(remaining), 10)
        )

    async def async_list_devices(self) -> list[dict]:
        """Every device in the cloud project.

        The response carries a local key for each device, so it must never be
        logged or written to diagnostics unredacted.
        """
        data = await self._get_with_retry(DEVICE_LIST_PATH)
        result = data.get("result", [])
        return result if isinstance(result, list) else []

    async def async_get_device(self, device_id: str) -> dict:
        data = await self._get_with_retry(device_info_path(device_id))
        return data.get("result", {})

    async def async_get_model(self, device_id: str) -> dict:
        data = await self._get_with_retry(model_path(device_id))
        return data.get("result", {})

    async def async_get_specification(self, device_id: str) -> dict:
        data = await self._get_with_retry(specification_path(device_id))
        return data.get("result", {})

    async def async_get_properties(self, device_id: str) -> dict:
        data = await self._get_with_retry(properties_path(device_id))
        return data.get("result", {})
