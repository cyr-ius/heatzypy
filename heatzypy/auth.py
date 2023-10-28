"""Authentication class."""
from __future__ import annotations

import logging
import time
from typing import Any

from aiohttp import ClientResponseError, ClientSession  # pylint: disable=import-error

from .const import HEATZY_API_URL, HEATZY_APPLICATION_ID
from .exception import AuthenticationFailed, CommandFailed, RetrieveFailed

_LOGGER = logging.getLogger(__name__)


class Auth:
    """Class to make authenticated requests."""

    def __init__(self, session: ClientSession | None, username: str, password: str):
        """Initialize the auth."""
        self._session = session or ClientSession()
        self._username = username
        self._password = password
        self._access_token: dict[str, Any] | None = None

    async def request(
        self, service: str, method: str = "GET", **kwargs
    ) -> dict[str, Any]:
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
                method,
                f"{HEATZY_API_URL}/{service}",
                **kwargs,
                headers=headers,
            )
            response.raise_for_status()
        except ClientResponseError as error:
            if method == "GET":
                raise RetrieveFailed(
                    f"{service} not retrieved ({error.status})"
                ) from error
            if service == "login":
                raise AuthenticationFailed(
                    f"{error.message} ({error.status})"
                ) from error
            raise CommandFailed(
                f"Cmd failed {service} with {kwargs} ({error.status} {error.message})"
            ) from error
        else:
            json_response: dict[str, Any] = await response.json(content_type=None)
            _LOGGER.debug(json_response)
            return json_response

    async def _async_get_token(self) -> str:
        """Get Token authentication."""
        if self._access_token is None or (
            (expire_at := self._access_token.get("expire_at"))
            and expire_at < time.time()
        ):
            payload = {"username": self._username, "password": self._password}
            self._access_token = await self.request(
                "login", method="POST", json=payload, auth=True
            )
        return self._access_token["token"]

    async def async_close(self):
        """Close session."""
        self._session.close()
