import logging
import time

from aiohttp import ClientResponse, ClientSession

from .const import HEATZY_API_URL, HEATZY_APPLICATION_ID
from .exception import AuthenticationFailed

_LOGGER = logging.getLogger(__name__)


class Auth:
    """Class to make authenticated requests."""

    def __init__(self, session: ClientSession, username: str, password: str):
        """Initialize the auth."""
        self._session = session
        self._username = username
        self._password = password
        self._access_token = None

    async def request(self, service: str, method: str = "GET", **kwargs) -> ClientResponse:
        """Make a request."""
        headers = dict(
            kwargs.pop("headers", {"X-Gizwits-Application-Id": HEATZY_APPLICATION_ID})
        )
        if kwargs.pop("auth", None) is None:
            access_token = await self._async_get_token()
            headers["X-Gizwits-User-Token"] = access_token

        return await self._session.request(
            method, f"{HEATZY_API_URL}/{service}", **kwargs, headers=headers,
        )

    async def _async_get_token(self) -> str:
        """Get Token authentication."""
        if self._access_token is None or self._access_token.get("expire_at") < time.time():
            payload = {"username": self._username, "password": self._password}
            response = await self.request("login", method="POST", json=payload, auth=True)
            if response.status != 200:
                raise AuthenticationFailed(f"{response.reason} ({response.status})")
            self._access_token = await response.json()
        return self._access_token["token"]
