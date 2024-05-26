"""Heatzy API."""

from __future__ import annotations

import logging
from typing import Any, Self

from aiohttp import ClientSession

from .auth import Auth
from .const import DFLT_API_URL, EU_API_URL, TIMEOUT, US_API_URL, WS_HOST
from .websocket import Websocket

logger = logging.getLogger(__name__)


class HeatzyClient:
    """Heatzy Client data."""

    def __init__(
        self,
        username: str,
        password: str,
        session: ClientSession = ClientSession(),
        time_out: int = TIMEOUT,
        region: str = "EU",
        use_tls: bool = True,
    ) -> None:
        """Load parameters."""
        if region == "EU":
            host = EU_API_URL
        elif region == "US":
            host = US_API_URL
        else:
            host = DFLT_API_URL

        self.auth = Auth(session, username, password, time_out, host, use_tls)
        self.websocket = Websocket(session, self.auth, WS_HOST, use_tls)
        self.async_request = self.auth.async_request

    async def async_bindings(self) -> Any:
        """Fetch all configured devices."""
        return await self.async_request("bindings")

    async def async_get_devices(self) -> dict[str, Any]:
        """Fetch all configured devices."""
        response = await self.async_bindings()
        devices = {device["did"]: device for device in response.get("devices", {})}
        for did, device in devices.items():
            device_data = await self.async_get_device_data(did)
            device_data["attrs"] = device_data.pop("attr", {})
            device.update(**device_data)
        return devices

    async def async_get_device(self, device_id: str) -> dict[str, Any]:
        """Fetch device with given id."""
        device = await self.async_request(f"devices/{device_id}")
        device_data = await self.async_get_device_data(device_id)
        device_data["attrs"] = device_data.pop("attr", {})
        return {**device, **device_data}

    async def async_get_device_data(self, device_id: str) -> Any:
        """Fetch detailed data for device with given id."""
        return await self.async_request(f"devdata/{device_id}/latest")

    async def async_control_device(
        self, device_id: str, payload: dict[str, Any]
    ) -> None:
        """Control state of device with given id."""
        await self.async_request(f"control/{device_id}", "post", json=payload)

    async def async_close(self) -> None:
        """Close open client (WebSocket) session."""
        await self.websocket.async_disconnect()
        if self.auth._session:
            await self.auth._session.close()

    async def __aenter__(self) -> Self:
        """Async enter."""
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit."""
        await self.async_close()
