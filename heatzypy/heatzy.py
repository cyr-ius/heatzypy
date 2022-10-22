"""Heatzy API."""
from __future__ import annotations

import logging
import time

from aiohttp import ClientSession, ClientError, ClientResponse

from .const import HEATZY_API_URL, HEATZY_APPLICATION_ID
from .exception import HttpRequestFailed, AuthenticationFailed, RetrieveFailed, CommandFailed

_LOGGER = logging.getLogger(__name__)


class HeatzyClient:
    """Heatzy Client data."""

    def __init__(self, username: str, password: str, session: ClientSession = None) -> None:
        """Load parameters."""
        self._session = session if session else ClientSession()
        self._username = username
        self._password = password
        self._authentication = None

    async def async_authenticate(self) -> ClientResponse:
        """Get Heatzy stored authentication if it exists or authenticate against Heatzy API."""
        headers = {"X-Gizwits-Application-Id": HEATZY_APPLICATION_ID}
        payload = {"username": self._username, "password": self._password}

        response = await self._async_make_request("/login", method="POST", payload=payload, headers=headers)
        if response.status != 200:
            raise AuthenticationFailed(f"Authentication Failed ({response.status})")
        return await response.json()

    async def async_get_token(self) -> str:
        """Get authentication token."""
        if self._authentication is None or self._authentication.get("expire_at") < time.time():
            self._authentication = await self.async_authenticate()
        return self._authentication["token"]

    async def _async_make_request(self, service, method="GET", headers=None, payload=None) -> ClientResponse:
        """Request session."""
        if headers is None:
            token = await self.async_get_token()
            headers = {
                "X-Gizwits-Application-Id": HEATZY_APPLICATION_ID,
                "X-Gizwits-User-Token": token,
            }

        try:
            url = HEATZY_API_URL + service
            _LOGGER.debug("{} {} {}".format(method, url, headers))
            return await self._session.request(method=method, url=url, json=payload, headers=headers)
        except ClientError as error:
            raise HttpRequestFailed("Request failed") from error

    async def async_get_devices(self) -> list(str):
        """Fetch all configured devices."""
        response = await self._async_make_request("/bindings")
        if response.status != 200:
            raise RetrieveFailed(f"Retrieve devices failed ({response.status})")
        # API response has Content-Type=text/html, content_type=None silences parse error by forcing content type
        body = await response.json(content_type=None)
        devices = body.get("devices")
        return [await self._async_merge_with_device_data(device) for device in devices]

    async def async_get_device(self, device_id) -> dict(str):
        """Fetch device with given id."""
        response = await self._async_make_request(f"/devices/{device_id}")
        if response.status != 200:
            raise RetrieveFailed(f"{device_id} not retrieved ({response.status})")
        # API response has Content-Type=text/html, content_type=None silences parse error by forcing content type
        device = await response.json(content_type=None)
        return await self._async_merge_with_device_data(device)

    async def _async_merge_with_device_data(self, device: dict(str)) -> dict(str):
        """Fetch detailed data for given device and merge it with the device information."""
        device_data = await self.async_get_device_data(device.get("did"))
        return {**device, **device_data}

    async def async_get_device_data(self, device_id: str) -> dict(str, str):
        """Fetch detailed data for device with given id."""
        response = await self._async_make_request(f"/devdata/{device_id}/latest")
        if response.status != 200:
            raise RetrieveFailed(f"{device_id} not retrieved ({response.status})")
        device_data = await response.json()
        return device_data

    async def async_control_device(self, device_id, payload) -> None:
        """Control state of device with given id."""
        response = await self._async_make_request(f"/control/{device_id}", method="POST", payload=payload)
        if response.status != 200:
            raise CommandFailed(f"Command failed ({response.status} {response.reason})")

    def is_connected(self) -> bool:
        """Check connection."""
        return self._authentication is not None

    async def async_close(self) -> None:
        await self._session.close()
