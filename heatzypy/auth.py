"""Authentication class."""
import logging
import time

from aiohttp import ClientResponse, ClientSession, ClientResponseError

from .const import HEATZY_API_URL, HEATZY_APPLICATION_ID
from .exception import AuthenticationFailed, RetrieveFailed, CommandFailed

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

        try:
            _LOGGER.debug("METHOD:%s URL:%s", method, service)
            _LOGGER.debug("DATA:%s", kwargs)
            response = await self._session.request(
                method, f"{HEATZY_API_URL}/{service}", **kwargs, headers=headers,
            )
            response.raise_for_status()
        except ClientResponseError as error:
            if method == "GET":
                raise RetrieveFailed(f"{service} not retrieved ({error.status})")
            elif service == "login":
                raise AuthenticationFailed(f"{error.message} ({error.status})")
            else:
                raise CommandFailed(f"Command failed {service} with {kwargs} ({error.status} {error.message})")
        else:
            response = await response.json(content_type=None)
            _LOGGER.debug(response)
            return response

    async def _async_get_token(self) -> str:
        """Get Token authentication."""
        if self._access_token is None or self._access_token.get("expire_at") < time.time():
            payload = {"username": self._username, "password": self._password}
            self._access_token = await self.request("login", method="POST", json=payload, auth=True)
        return self._access_token["token"]
