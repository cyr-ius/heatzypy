"""Tests analytics."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from aiohttp import ClientError, ClientResponseError
import pytest

from heatzypy import AuthenticationFailed, HeatzyClient, TimeoutExceededError
from heatzypy.exception import HttpRequestFailed
from tests import mock_response


@pytest.mark.asyncio
async def test_init() -> None:
    """Init api."""
    api = HeatzyClient("x", "y")
    assert api.websocket.is_connected is False
    assert api._auth._username == "x"


@pytest.mark.asyncio
async def test_request(api, mock_token, mock_devices) -> None:
    """Test connection."""
    req_token = mock_response({"expire_at": "", "token": "123456"})
    req_devices = mock_response(mock_devices)

    with patch(
        "aiohttp.ClientSession.request", side_effect=[req_token(), req_devices()]
    ):
        await api.async_bindings()

    assert len(req_token.mock_calls) == 3
    assert len(req_devices.mock_calls) == 3


@pytest.mark.asyncio
async def test_error_request(api) -> None:
    """Test connection."""
    with patch("aiohttp.ClientSession.request", side_effect=[asyncio.TimeoutError]):
        try:
            await api.async_bindings()
        except TimeoutExceededError as error:
            assert error is not None

    with patch("aiohttp.ClientSession.request", side_effect=[ClientError]):
        try:
            await api.async_bindings()
        except HttpRequestFailed as error:
            assert error is not None

    with patch(
        "aiohttp.ClientSession.request",
        side_effect=[
            ClientResponseError(request_info=AsyncMock(), history=(AsyncMock()))
        ],
    ):
        try:
            await api.async_bindings()
        except AuthenticationFailed as error:
            assert error is not None


@pytest.mark.asyncio
@patch("heatzypy.auth.Auth.async_get_token")
async def test_bindings(token, api, mock_devices) -> None:
    """Test connection."""
    req_devices = mock_response(mock_devices)
    with (
        patch("aiohttp.ClientSession.request", return_value=req_devices()),
    ):
        bindings = await api.async_bindings()

    assert bindings["data"] is not None


@pytest.mark.asyncio
@patch("heatzypy.auth.Auth.async_get_token")
@pytest.mark.parametrize("mock_attribut", ["inea"], indirect=True)
async def test_get_devices(token, api, mock_device, mock_attribut) -> None:
    """Test connection."""
    with (
        patch(
            "heatzypy.HeatzyClient.async_bindings",
            return_value={"devices": [mock_device]},
        ),
        patch(
            "heatzypy.HeatzyClient.async_get_device_data", return_value=mock_attribut
        ),
    ):
        devices = await api.async_get_devices()

    assert devices.get("ZtTGUB8Li86z7TG9A7XTQY") is not None


@pytest.mark.asyncio
@patch("heatzypy.auth.Auth.async_get_token")
@pytest.mark.parametrize("mock_attribut", ["inea"], indirect=True)
async def test_get_device(token, api, mock_device, mock_attribut) -> None:
    """Test connection."""
    req_device = mock_response(mock_device)
    with (
        patch("aiohttp.ClientSession.request", return_value=req_device()),
        patch(
            "heatzypy.HeatzyClient.async_get_device_data", return_value=mock_attribut
        ),
    ):
        device = await api.async_get_device("ZtTGUB8Li86z7TG9A7XTQY")

    assert device["attrs"] is not None
    assert device["did"] == "ZtTGUB8Li86z7TG9A7XTQY"


@pytest.mark.asyncio
@patch("heatzypy.auth.Auth.async_get_token")
async def test_control(token, api) -> None:
    """test send control."""
    mock = mock_response()
    with (
        patch("aiohttp.ClientSession.request", return_value=mock()),
    ):
        await api.async_control_device("ZtTGUB8Li86z7TG9A7XTQY", {"mode": "cft"})

    assert len(mock.mock_calls) == 3
