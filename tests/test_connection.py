"""Tests analytics."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from heatzypy import HeatzyClient
from tests import mock_response


@pytest.mark.asyncio
async def test_connect(api, mock_token) -> None:
    """Test connection."""
    mock = mock_response(mock_token)
    with patch("aiohttp.ClientSession.request", return_value=mock()):
        await api._auth.async_get_token()

    assert len(mock.mock_calls) == 3


@pytest.mark.asyncio
async def test_bindings(api, mock_token, mock_devices) -> None:
    """Test connection."""
    mock = mock_response(mock_devices)
    with (
        patch("heatzypy.auth.Auth.async_get_token", return_value=mock_token),
        patch("aiohttp.ClientSession.request", return_value=mock()),
    ):
        bindings = await api.async_bindings()

    assert bindings is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("mock_attribut", ["inea"], indirect=True)
async def test_get_devices(api, mock_token, mock_devices, mock_attribut) -> None:
    """Test connection."""
    with (
        patch("heatzypy.auth.Auth.async_get_token", return_value=mock_token),
        patch(
            "heatzypy.HeatzyClient.async_bindings",
            return_value={"devices": [mock_devices["devices"][0]]},
        ),
        patch(
            "heatzypy.HeatzyClient.async_get_device_data", return_value=mock_attribut
        ),
    ):
        devices = await api.async_get_devices()

    assert devices is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("mock_attribut", ["inea"], indirect=True)
async def test_get_device(api, mock_token, mock_device, mock_attribut) -> None:
    """Test connection."""
    mock = mock_response(mock_device)
    with (
        patch("heatzypy.auth.Auth.async_get_token", return_value=mock_token),
        patch("aiohttp.ClientSession.request", return_value=mock()),
        patch(
            "heatzypy.HeatzyClient.async_get_device_data", return_value=mock_attribut
        ),
    ):
        device = await api.async_get_device("ZtTGUB8Li86z7TG9A7XTQY")

    assert device["attrs"] is not None
    assert device["did"] == "ZtTGUB8Li86z7TG9A7XTQY"


@pytest.mark.asyncio
async def test_control(api, mock_token) -> None:
    """test send control."""
    mock = mock_response()
    with (
        patch("heatzypy.auth.Auth.async_get_token", return_value=mock_token),
        patch("aiohttp.ClientSession.request", return_value=mock()),
    ):
        await api.async_control_device("ZtTGUB8Li86z7TG9A7XTQY", {"mode": "cft"})

    assert len(mock.mock_calls) == 3


@pytest.mark.asyncio
async def test_init() -> None:
    """Init api."""
    api = HeatzyClient("x", "y")
    assert api.websocket.is_connected is False
    assert api._auth._username == "x"
