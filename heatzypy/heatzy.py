"""Heatzy API."""
from __future__ import annotations

import logging

from aiohttp import ClientSession, ClientTimeout

from .auth import Auth
from .exception import RetrieveFailed, CommandFailed

_LOGGER = logging.getLogger(__name__)


class HeatzyClient:
    """Heatzy Client data."""

    def __init__(self, username: str, password: str, session: ClientSession = None, timeout: int = 10) -> None:
        """Load parameters."""
        timeout = ClientTimeout(total=timeout)
        self._session = session if session else ClientSession(timeout=timeout)
        self.request = Auth(self._session, username, password).request

    async def async_bindings(self) -> dict:
        """Fetch all configured devices."""
        response = await self.request("bindings")
        if response.status != 200:
            raise RetrieveFailed(f"Retrieve devices failed ({response.status})")
        # API response has Content-Type=text/html, content_type=None silences parse error by forcing content type
        return await response.json(content_type=None)

    async def async_get_devices(self) -> list(str):
        """Fetch all configured devices."""
        response = await self.async_bindings()
        devices = response.get("devices")
        devices_with_datas = [await self._async_merge_with_device_data(device) for device in devices]
        dict_devices_with_datas = {device["did"]: device for device in devices_with_datas}
        return dict_devices_with_datas

    async def async_get_device(self, device_id) -> dict(str):
        """Fetch device with given id."""
        response = await self.request(f"devices/{device_id}")
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
        response = await self.request(f"devdata/{device_id}/latest")
        if response.status != 200:
            raise RetrieveFailed(f"{device_id} not retrieved ({response.status})")
        return await response.json()

    async def async_control_device(self, device_id, payload) -> None:
        """Control state of device with given id."""
        response = await self.request(f"control/{device_id}", method="POST", json=payload)
        if response.status != 200:
            raise CommandFailed(f"Command failed {device_id} {payload} ({response.status} {response.reason})")

    async def async_close(self) -> None:
        await self._session.close()
