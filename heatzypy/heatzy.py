"""Heatzy API."""
import logging
import time

import requests
from requests.exceptions import RequestException

from .const import HEATZY_API_URL, HEATZY_APPLICATION_ID
from .exception import HeatzyException, HttpRequestFailed

logger = logging.getLogger(__name__)


class HeatzyClient:
    """Heatzy Client data."""

    def __init__(self, username, password):
        """Load parameters."""
        self._session = requests.Session()
        self._username = username
        self._password = password
        self._authentication = None

    def _authenticate(self):
        """Get Heatzy stored authentication if it exists or authenticate against Heatzy API."""
        headers = {"X-Gizwits-Application-Id": HEATZY_APPLICATION_ID}
        payload = {"username": self._username, "password": self._password}

        response = self._make_request("/login", method="POST", payload=payload, headers=headers)
        if response.status_code != 200:
            raise HeatzyException("Authentication failed", response.status_code)

        logger.debug("Authentication successful with {}".format(self._username))
        return response.json()

    def _get_token(self):
        """Get authentication token."""
        if self._authentication is not None and self._authentication.get("expire_at") > time.time():
            return self._authentication["token"]
        self._authentication = self._authenticate()
        if self._authentication:
            return self._authentication["token"]

    def _make_request(self, service, method="GET", headers=None, payload=None):
        """Request session."""
        if headers is None:
            token = self._get_token()
            headers = {
                "X-Gizwits-Application-Id": HEATZY_APPLICATION_ID,
                "X-Gizwits-User-Token": token,
            }
        url = HEATZY_API_URL + service
        logger.debug("{} {} {}".format(method, url, headers))
        try:
            return self._session.request(method=method, url=url, json=payload, headers=headers)
        except RequestException as error:
            raise HttpRequestFailed("Request failed") from error

    def get_devices(self):
        """Fetch all configured devices."""
        response = self._make_request("/bindings")
        if response.status_code != 200:
            raise HeatzyException("Devices not retrieved", response.status_code)

        # API response has Content-Type=text/html, content_type=None silences parse error by forcing content type
        body = response.json()
        devices = body.get("devices")

        return [self._merge_with_device_data(device) for device in devices]

    def get_device(self, device_id):
        """Fetch device with given id."""
        response = self._make_request(f"/devices/{device_id}")
        if response.status_code != 200:
            raise HeatzyException(f"Device data for {device_id} not retrieved", response.status_code)

        # API response has Content-Type=text/html, content_type=None silences parse error by forcing content type
        logger.debug(response.text)
        device = response.json()
        return self._merge_with_device_data(device)

    def _merge_with_device_data(self, device):
        """Fetch detailled data for given device and merge it with the device information."""
        device_data = self._get_device_data(device.get("did"))
        return {**device, **device_data}

    def _get_device_data(self, device_id):
        """Fetch detailled data for device with given id."""
        response = self._make_request(f"/devdata/{device_id}/latest")
        if response.status_code != 200:
            raise HeatzyException(f"Device data for {device_id} not retrieved", response.status_code)

        logger.debug(response.text)
        device_data = response.json()
        return device_data

    def control_device(self, device_id, payload):
        """Control state of device with given id."""
        self._make_request(f"/control/{device_id}", method="POST", payload=payload)

    def is_connected(self):
        """Check connection."""
        return self._authenticate() is not None
