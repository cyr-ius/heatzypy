"""Authentication class."""

from __future__ import annotations

import asyncio
from json import JSONDecodeError
import logging
import socket
from time import time
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession
from yarl import URL

from .const import APPLICATION_ID, RETRY, URL_PATH
from .exception import (
    AuthenticationFailed,
    CommandFailed,
    HttpRequestFailed,
    RetrieveFailed,
    TimeoutExceededError,
    UnexpectedResponse,
)

logger = logging.getLogger(__name__)


class Auth:
    """Class to make authenticated requests."""

    def __init__(
        self,
        session: ClientSession | None,
        username: str,
        password: str,
        timeout: int,
        host: str,
        use_tls: bool = True,
    ):
        """Initialize the auth."""
        self._session = session or ClientSession()
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._expire_at: float = time()
        self._timeout: int = timeout
        self._retry = RETRY
        self._host = host
        self._scheme = "https" if use_tls else "http"

    async def async_request(self, path: str, method: str = "get", **kwargs: Any) -> Any:
        """Make a request."""
        kwargs.setdefault("headers", {})
        kwargs["headers"].update({"X-Gizwits-Application-Id": APPLICATION_ID})

        if path != "login":
            await self.async_get_token()
            kwargs["headers"].update({"X-Gizwits-User-Token": self._access_token})

        try:
            async with asyncio.timeout(self._timeout):
                url = URL.build(
                    scheme=self._scheme, host=self._host, path=f"{URL_PATH}/{path}"
                )
                logger.debug("Request: %s (%s) - %s", path, method, kwargs.get("json"))
                response = await self._session.request(method, url, **kwargs)
                response.raise_for_status()
        except ClientResponseError as error:
            if method == "get":
                raise RetrieveFailed(
                    f"{path} not retrieved ({error.status})"
                ) from error
            if path == "login":
                raise AuthenticationFailed(
                    f"{error.message} ({error.status})"
                ) from error
            if method == "post" and error.status in [400, 500, 502] and self._retry > 0:
                self._retry -= 1
                await asyncio.sleep(3)
                return await self.async_request(path, method, **kwargs)
            raise CommandFailed(
                f"Cmd failed {path} with {kwargs.get('json')} ({error.status} {error.message})"
            ) from error
        except (asyncio.CancelledError, asyncio.TimeoutError) as error:
            raise TimeoutExceededError(
                "Timeout occurred while connecting to Heatzy."
            ) from error
        except (ClientError, socket.gaierror) as error:
            raise HttpRequestFailed(
                "Error occurred while communicating with Heatzy."
            ) from error

        json_response: dict[str, Any] = {}
        try:
            if response.status != 204:
                json_response = await response.json(content_type=None)
        except JSONDecodeError as error:
            raise UnexpectedResponse(f"Error while decoding Json ({error})") from error

        logger.debug("RESPONSE: %s", json_response)

        return json_response

    async def async_get_token(self, force: bool = False) -> Any:
        """Get Token authentication."""
        if force or self._expire_at < time():
            payload = {"username": self._username, "password": self._password}
            token = await self.async_request("login", "post", json=payload)
            self._expire_at = token.get("expire_at")
            self._access_token = token.get("token")

            return token
