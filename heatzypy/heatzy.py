"""Heatzy API."""
import asyncio
import logging
import time
import requests

from .exception import HeatzyException
from .const import HEATZY_API_URL, HEATZY_APPLICATION_ID

logger = logging.getLogger(__name__)


class HeatzyClient:
    """Heatzy Client data."""

    def __init__(self, username, password):
        """Load parameters."""
        self._session = requests.Session()
        self._username = username
        self._password = password
        self._authentication = None

    async def async_authenticate(self):
        """Get Heatzy stored authentication if it exists or authenticate against Heatzy API."""
        headers = {"X-Gizwits-Application-Id": HEATZY_APPLICATION_ID}
        payload = {"username": self._username, "password": self._password}
        response = self._session.post(
            HEATZY_API_URL + "/login", json=payload, headers=headers
        )

        if response.status_code != 200:
            raise HeatzyException("Authentication failed",response.status_code)
            
        logger.debug("Authentication successful with {}".format(self._username))
        return response.json()

    async def _async_get_token(self):
        """Get authentication token."""
        if self._authentication is not None and self._authentication.get("expire_at") > time.time():        
             return  self._authentication["token"]
        self._authentication = await self.async_authenticate()
        return  self._authentication["token"]
        
    async def async_get_devices(self):
        """Fetch all configured devices."""
        token = await self._async_get_token()
        headers = {
            "X-Gizwits-Application-Id": HEATZY_APPLICATION_ID,
            "X-Gizwits-User-Token": token,
        }
        response = self._session.get(
            HEATZY_API_URL + "/bindings", headers=headers
        )
        # API response has Content-Type=text/html, content_type=None silences parse error by forcing content type
        body =  response.json()
        devices = body.get("devices")
        return await asyncio.gather(
            *[self._merge_with_device_data(device) for device in devices]
        )

    async def async_get_device(self, device_id):
        """Fetch device with given id."""
        token = await self._async_get_token()
        headers = {
            "X-Gizwits-Application-Id": HEATZY_APPLICATION_ID,
            "X-Gizwits-User-Token": token,
        }
        response =  self._session.get(
            HEATZY_API_URL + "/devices/" + device_id, headers=headers
        )
        # API response has Content-Type=text/html, content_type=None silences parse error by forcing content type
        device =  response.json()
        return await self._merge_with_device_data(device)

    async def _merge_with_device_data(self, device):
        """Fetch detailled data for given device and merge it with the device information."""
        device_data = await self._async_get_device_data(device.get("did"))
        return {**device, **device_data}

    async def _async_get_device_data(self, device_id):
        """Fetch detailled data for device with given id."""
        token = await self._async_get_token()
        headers = {
            "X-Gizwits-Application-Id": HEATZY_APPLICATION_ID,
            "X-Gizwits-User-Token": token,
        }
        response = self._session.get(
            HEATZY_API_URL + "/devdata/" + device_id + "/latest", headers=headers
        )
        device_data = response.json()
        return device_data

    async def async_control_device(self, device_id, payload):
        """Control state of device with given id."""
        token = await self._async_get_token()
        headers = {
            "X-Gizwits-Application-Id": HEATZY_APPLICATION_ID,
            "X-Gizwits-User-Token": token,
        }
        self._session.post(
            HEATZY_API_URL + "/control/" + device_id, json=payload, headers=headers
        )
