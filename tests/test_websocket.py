"""Tests for the Websocket helper class."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, Mock

from aiohttp import ClientConnectionResetError
import pytest

from heatzypy.exception import WebsocketError
from heatzypy.websocket import Websocket


@pytest.fixture
def websocket():
    """Return a Websocket instance without opening any real connection."""
    return Websocket(session=Mock(), auth=Mock(), host="wss://example.test")


def test_is_fresh_without_devices(websocket) -> None:
    """No device known means data can't be considered fresh."""
    assert websocket.is_fresh(60) is False


def test_is_fresh_true_after_update(websocket) -> None:
    """A device updated moments ago is fresh."""
    websocket.devices = {"did1": {"did": "did1"}}
    websocket._last_update = {"did1": time.monotonic()}
    assert websocket.is_fresh(60) is True


def test_is_fresh_false_when_stale(websocket) -> None:
    """A device whose last push is older than max_age is not fresh."""
    websocket.devices = {"did1": {"did": "did1"}}
    websocket._last_update = {"did1": time.monotonic() - 120}
    assert websocket.is_fresh(60) is False


def test_is_fresh_false_when_missing_update(websocket) -> None:
    """A device that never pushed attrs is not fresh."""
    websocket.devices = {"did1": {"did": "did1"}}
    assert websocket.is_fresh(60) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("error_code", [1003, 1009, 1011])
async def test_handle_invalid_msg_raises_on_fatal_codes(websocket, error_code) -> None:
    """A fatal error code disconnects and surfaces a WebsocketError."""
    websocket.async_disconnect = AsyncMock()
    with pytest.raises(WebsocketError):
        await websocket._handle_invalid_msg({"error_code": error_code, "msg": "boom"})
    websocket.async_disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_invalid_msg_ignores_unknown_codes(websocket) -> None:
    """An unknown error code is only logged, not treated as fatal."""
    websocket.async_disconnect = AsyncMock()
    await websocket._handle_invalid_msg({"error_code": 4242, "msg": "whatever"})
    websocket.async_disconnect.assert_not_awaited()


@pytest.mark.asyncio
async def test_heartbeat_disconnects_on_send_failure(websocket) -> None:
    """A failed ping (e.g. half-closed socket) closes the websocket instead of dying silently."""
    websocket.ws = Mock(closed=False)
    websocket.async_ping = AsyncMock(
        side_effect=ClientConnectionResetError("Cannot write to closing transport")
    )
    websocket.async_disconnect = AsyncMock()

    await websocket._async_heartbeat()

    websocket.async_disconnect.assert_awaited_once()
