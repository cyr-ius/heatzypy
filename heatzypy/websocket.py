"""Class for websocket."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
import logging
import socket
from typing import TYPE_CHECKING, Any, cast

import aiohttp
from aiohttp import ClientSession, ClientWebSocketResponse
from yarl import URL as yurl

from .const import APPLICATION_ID, WS_PING_INTERVAL, WS_PORT, WSS_PORT
from .exception import AuthenticationFailed, ConnectionFailed, WebsocketError

if TYPE_CHECKING:
    from .auth import Auth

logger = logging.getLogger(__name__)


class Websocket:
    """Heatzy websocket."""

    def __init__(
        self, session: ClientSession, auth: Auth, host: str, use_tls: bool = True
    ) -> None:
        """Initialize."""
        self.session = session
        self._auth = auth
        self.ws: ClientWebSocketResponse = cast(ClientWebSocketResponse, None)

        self.devices: dict[str, Any] = {}
        self.is_logged: bool = False

        self._host = host
        self._scheme = "wss" if use_tls else "ws"
        self._port = WSS_PORT if use_tls else WS_PORT

        self._all_devices: bool = False
        self._auto_subscribe: bool = False
        self.subscribed_devices: list[str] = []
        self.last_invalid_msg: dict[str, Any] | None = None

        self._callbacks: list[Callable[..., None]] = []

    @property
    def is_connected(self) -> bool:
        """Return if we are connect to the WebSocket."""
        return self.ws is not None and not self.ws.closed

    @property
    def is_updated(self) -> bool:
        """Return if all devices updated."""
        attrs_fills = [
            device["did"] for device in self.devices.values() if device.get("attrs")
        ]
        return list(self.devices.keys()) == attrs_fills and len(self.devices) > 0

    async def async_fetch_binding_devices(self) -> None:
        """Return bindings devices."""
        bindings = await self._auth.async_request("bindings")
        for info in bindings.get("devices", {}):
            self.devices.update({info["did"]: info})

    async def async_get_devices(self) -> dict[str, Any]:
        """Return all devices data while listen connection."""
        for did in self.devices:
            payload = {"cmd": "c2s_read", "data": {"did": did}}
            await self._send_cmd(payload)
        return self.devices

    async def async_control_device(
        self, device_id: str, payload: dict[str, dict[str, Any]]
    ) -> None:
        """Send command to device.

        Args:
        ----
            - payload: raw or attrs dictionary containing the actions dictionary
             {"raw": [1,1,3]} or {"attrs": {"mode": "cft"} }
        """
        cmd = "c2s_raw" if payload.get("raw") else "c2s_write"
        control = {"cmd": cmd, "data": {"did": device_id, **payload}}
        await self._send_cmd(control)

    async def _async_heartbeat(self) -> None:
        """Heatbeat websocket."""
        while not self.ws.closed:
            await self.async_ping()
            await asyncio.sleep(WS_PING_INTERVAL)

    async def async_ping(self) -> None:
        """Send ping."""
        await self._send_cmd({"cmd": "ping"})

    async def async_connect(
        self, auto_subscribe: bool = True, all_devices: bool = False
    ) -> None:
        """Connect to the WebSocket.

        Args:
        ---
            - auto_subscribe set True the server automatically subscribes to all the bound devices
            if false, you need to select the devices to be subscribed to through the following async_subscribe
            - all_devices set True return all subscribed devices if one device change else return only device
        """

        self._auto_subscribe = auto_subscribe
        self._all_devices = all_devices

        if self.is_connected:
            return

        if not self.session:
            raise WebsocketError("Session not found")

        if not self.devices:
            await self.async_fetch_binding_devices()

        try:
            url = yurl.build(
                scheme=self._scheme, host=self._host, port=self._port, path="/ws/app/v1"
            )
            self.ws = await self.session.ws_connect(url=url)
            logger.debug("WEBSOCKET Connected to a %s Websocket", url)
        except (
            aiohttp.WSServerHandshakeError,
            aiohttp.ClientConnectionError,
            socket.gaierror,
        ) as exception:
            raise ConnectionFailed(
                f"Error occurred while communicating with device on WebSocket at {url}"
            ) from exception

        try:
            await self.async_login(auto_subscribe)
        except WebsocketError as error:
            raise AuthenticationFailed(error) from error

        if auto_subscribe:
            try:
                await self.async_get_devices()
            except WebsocketError as error:
                raise AuthenticationFailed(error) from error

    async def async_login(self, auto_subscribe: bool = True) -> None:
        """Login to websocket."""

        token_data = await self._auth.async_get_token(force=True)

        payload = {
            "cmd": "login_req",
            "data": {
                "appid": APPLICATION_ID,
                "uid": token_data.get("uid"),
                "token": token_data.get("token"),
                "p0_type": "attrs_v4",
                "heartbeat_interval": WS_PING_INTERVAL,
                "auto_subscribe": auto_subscribe,
            },
        }
        await self._send_cmd(payload)
        asyncio.create_task(self._async_heartbeat())

    async def async_listen(self) -> None:
        """Listen for events on the WebSocket."""

        while not self.ws.closed:
            message = await self.ws.receive()

            if message.type == aiohttp.WSMsgType.ERROR:
                raise ConnectionFailed(self.ws.exception())

            if message.type == aiohttp.WSMsgType.BINARY:
                pass

            if message.type == aiohttp.WSMsgType.TEXT:
                try:
                    message_data = message.json()
                    logger.debug("WEBSOCKET <<< %s", message_data)
                    data = message_data.get("data")
                    cmd = message_data.get("cmd")
                    if data and cmd:
                        self.last_invalid_msg = None
                        match cmd:
                            case "login_res":
                                await self._handle_login(data)
                            case "subscribe_res":
                                await self._handle_subscription(data)
                            case "s2c_invalid_msg":
                                await self._handle_invalid_msg(data)
                            case "s2c_noti":
                                await self._handle_notification(data)
                            case "s2c_binding_changed":
                                await self._handle_binding_change(data)
                            case "s2c_online_status":
                                await self._handle_status_change(data)
                    elif cmd == "pong":
                        await self._hand_pong(message_data)
                    else:
                        logger.warn(f"Received invalid message: {message}")
                except json.JSONDecodeError:
                    logger.error("Invalid JSON format for the received message.")

            if message.type in (
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.CLOSED,
                aiohttp.WSMsgType.CLOSING,
            ):
                raise WebsocketError("Connection to the WebSocket has been closed")

    async def async_disconnect(self) -> None:
        """Disconnect from the WebSocket of a device."""
        if not self.ws or not self.is_connected:
            return

        await self.ws.close()

    async def async_subscribe(self, device_ids: list[str]) -> None:
        """Subscribed to the bound device.

        This API only applies to scenarios where the connect or login parameter auto_subscribe is set to false

        Args:
        ----
            - device_ids : Array of did
        """
        dids = [{"did": did} for did in device_ids]
        payload = {"cmd": "subscribe_req", "data": dids}
        await self._send_cmd(payload)

    async def _hand_pong(self, data: dict[str, Any]) -> None:
        """Handle ping receive."""

    async def _handle_login(self, data: dict[str, Any]) -> None:
        """Handle login response."""
        if data.get("success") is False:
            self.is_logged = False
            raise AuthenticationFailed(data)
        logger.debug("WEBSOCKET Successfully authenticated")
        self.is_logged = True

    async def _handle_subscription(self, data: dict[str, Any]) -> None:
        """Handle the response of subscription."""
        devices = cast(list[Any], data.get("success"))
        for device in devices:
            if (did := device["did"]) not in self.subscribed_devices:
                self.subscribed_devices.append(did)

    async def _handle_notification(self, data: dict[str, Any]) -> None:
        """Handle a notification receive by client."""
        if did := data.get("did"):
            device = self.devices.get(did)
            if device and (attrs := data.get("attrs")):
                device["attrs"] = attrs
                if len(self._callbacks) > 0:
                    if self._all_devices:
                        if self.is_updated:
                            self._run_callbacks(self.devices)
                    else:
                        self._run_callbacks(device)

    async def _handle_invalid_msg(self, data: dict[str, Any]) -> None:
        """Handle a notification receive by client."""
        logger.warn("Received invalid message: %s", data)
        self.last_invalid_msg = data

    async def _handle_binding_change(self, data: dict[str, Any]) -> None:
        """Handle a new binding status."""
        if (did := data.get("did")) and (data.get("bind") is False):
            self.devices.pop(did, None)
        elif did:
            bindings = await self._auth.async_request("bindings")
            if bindings and (data := bindings.get(did, {})):
                self.devices.update({did: data})

    async def _handle_status_change(self, data: dict[str, Any]) -> None:
        """Handle a new status."""
        did = data.pop("did", None)
        if device := self.devices.get(did):
            device.update(data)

    async def _send_cmd(self, payload: dict[str, Any]) -> None:
        """Send command to websocket."""
        if not self.ws or not self.is_connected:
            raise WebsocketError("Not connected to a Heatzy WebSocket")

        logger.debug("WEBSOCKET >>> %s", payload)
        await self.ws.send_json(payload)

    def register_callback(self, callback: Callable[..., None]) -> None:
        """Register a data update callback.

        :param func callback: Takes one function, which should be registered.
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[..., None]) -> None:
        """Unregister a data update callback.

        :param func callback: Takes one function, which should be unregistered.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _run_callbacks(self, data: dict[str, Any]) -> None:
        """Schedule a data callbacks."""
        for fn in self._callbacks:
            fn(data)
