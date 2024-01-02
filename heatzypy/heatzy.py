"""Heatzy API."""
from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any, Callable, Self

import aiohttp  # pylint: disable=import-error
from aiohttp import ClientSession  # pylint: disable=import-error
from yarl import URL  # pylint: disable=import-error

from .auth import Auth
from .const import HEATZY_APPLICATION_ID, WS_HOST, WS_PORT
from .exception import ConnectionClose, ConnectionFailed, WebsocketError

_LOGGER = logging.getLogger(__name__)
HEARTBEAT_INTERVAL = 30

_LOGGER = logging.getLogger(__name__)


class HeatzyClient:
    """Heatzy Client data."""

    def __init__(
        self,
        username: str,
        password: str,
        session: ClientSession = ClientSession(),
        time_out: int = 120,
    ) -> None:
        """Load parameters."""
        self._auth = Auth(session, username, password, time_out)
        self.session = session
        self.request = self._auth.request

        self._client: aiohttp.ClientWebSocketResponse | None = None
        self._devices: dict[str, Any] = {}
        self.authenticated: bool = False

    @property
    def connected(self) -> bool:
        """Return if we are connect to the WebSocket."""
        return self._client is not None and not self._client.closed

    async def async_bindings(self) -> dict[str, dict[str, Any]]:
        """Fetch all configured devices."""
        return await self.request("bindings")

    async def async_control_device(
        self, device_id: str, payload: dict[str, Any]
    ) -> None:
        """Control state of device with given id."""
        await self.request(f"control/{device_id}", method="POST", json=payload)

    async def async_ws_listen(self, callback: Callable[..., None]) -> None:
        """Listen for events on the WebSocket.

        Args:
        ----
            callback: Method to call when a state update is received from the device.

        """
        if not self._client or not self.connected:
            _LOGGER.debug("Not authenticated to a WebSocket, login...")
            await self._async_login()

        if not self._devices:
            _LOGGER.debug("Fetch all data")
            await self.async_get_devices()

        while not self._client.closed:
            message = await self._client.receive()

            if message.type == aiohttp.WSMsgType.ERROR:
                raise ConnectionFailed(self._client.exception())

            if message.type == aiohttp.WSMsgType.TEXT:
                message_data = message.json()
                _LOGGER.debug(message_data)
                if (data := message_data.get("data")) and (did := data.get("did")):
                    self._devices[did]["attrs"] = data.get("attrs", {})
                    callback(self._devices)

            if message.type in (
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.CLOSED,
                aiohttp.WSMsgType.CLOSING,
            ):
                _LOGGER.debug("Connection to the WebSocket has been closed")
                await self.async_ws_listen(callback)

        msg = "Not connected to a WebSocket"
        raise WebsocketError(msg)

    async def async_get_devices(self) -> dict[str, Any]:
        """Fetch all data."""
        if not self._client or not self.connected:
            _LOGGER.debug("Not authenticated to a WebSocket, login...")
            await self._async_login()

        bindings = await self.async_bindings()
        devices = bindings.get("devices", [])
        for device in devices:
            if isinstance(device, dict) and (did := device.get("did")):
                read_data = {"cmd": "c2s_read", "data": {"did": did}}
                await self._client.send_json(read_data)
                message = await self._client.receive()

                if message.type == aiohttp.WSMsgType.ERROR:
                    raise ConnectionFailed(self._client.exception())

                if message.type == aiohttp.WSMsgType.TEXT:
                    message_data = message.json()
                    device["attrs"] = message_data.get("data", {}).get("attrs", {})

                if message.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSING,
                ):
                    _LOGGER.debug("Connection to the WebSocket has been closed")
                    await self.async_get_devices()

        self._devices = {
            did: device
            for device in devices
            if isinstance(device, dict) and (did := device.get("did"))
        }
        return self._devices

    async def async_get_device(self, device_id: str) -> dict[str, Any]:
        """Fetch device with given id."""
        devices = await self.async_get_devices()
        return devices.get(device_id, {})

    async def async_disconnect(self) -> None:
        """Disconnect from the WebSocket of a device."""
        if not self._client or not self.connected:
            return

        await self._client.close()

    async def async_close(self) -> None:
        """Close open client (WebSocket) session."""
        await self.async_disconnect()
        if self.session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter."""
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit."""
        await self.async_close()

    async def _async_heartbeat(self) -> None:
        while not self._client.closed:
            data = {"cmd": "ping"}
            _LOGGER.debug(data)
            await self._client.send_json(data)
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def _async_connect(self) -> None:
        """Connect to the WebSocket."""
        if self.connected:
            return

        if not self.session:
            msg = f"The device at {WS_HOST} does not support WebSockets"
            raise WebsocketError(msg)

        url = URL.build(scheme="ws", host=WS_HOST, port=WS_PORT, path="/ws/app/v1")

        try:
            self._client = await self.session.ws_connect(url=url)
            _LOGGER.debug("Connected")
        except (
            aiohttp.WSServerHandshakeError,
            aiohttp.ClientConnectionError,
            socket.gaierror,
        ) as exception:
            msg = f"Error occurred while communicating with device on WebSocket at {WS_HOST}"
            raise ConnectionFailed(msg) from exception

    async def _async_login(self) -> None:
        self.authenticated = False
        if not self._client or not self.connected:
            _LOGGER.debug("Not connected to a WebSocket, connecting...")
            await self._async_connect()

        token_data = await self._auth.async_get_token()

        login = {
            "cmd": "login_req",
            "data": {
                "appid": HEATZY_APPLICATION_ID,
                "uid": token_data.get("uid"),
                "token": token_data.get("token"),
                "p0_type": "attrs_v4",
                "heartbeat_interval": HEARTBEAT_INTERVAL,
                "auto_subscribe": True,
            },
        }
        await self._client.send_json(login)
        message = await self._client.receive()

        if message.type == aiohttp.WSMsgType.ERROR:
            raise ConnectionFailed(self._client.exception())

        if message.type == aiohttp.WSMsgType.TEXT:
            message_data = message.json()
            if message_data.get("data", {}).get("success") is False:
                raise WebsocketError(message_data)
            _LOGGER.debug("Logged")
            self.authenticated = True
            asyncio.create_task(self._async_heartbeat())

        if message.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSED,
            aiohttp.WSMsgType.CLOSING,
        ):
            msg = f"Connection to the WebSocket on {WS_HOST} has been closed"
            raise ConnectionClose(msg)
