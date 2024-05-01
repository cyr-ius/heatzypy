"""Authentication class."""

from __future__ import annotations

import asyncio
from json import JSONDecodeError
import logging
import socket
import time
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
        self._access_token: dict[str, Any] | None = None
        self._timeout: int = timeout
        self._retry = RETRY
        self._host = host
        self._scheme = "https" if use_tls else "http"

    async def request(
        self,
        url: str | URL,
        method: str = "get",
        json: dict[str, Any] | None = None,
        auth: bool = False,
    ) -> dict[str, Any]:
        """Make a request."""
        headers: dict[str, Any] = {"X-Gizwits-Application-Id": APPLICATION_ID}

        if auth is False:
            access_token = await self.async_get_token()
            headers["X-Gizwits-User-Token"] = access_token.get("token")

        try:
            async with asyncio.timeout(self._timeout):
                url = URL.build(
                    scheme=self._scheme, host=self._host, path=f"{URL_PATH}/{url}"
                )
                logger.debug("METHOD:%s URL:%s", method, url)
                logger.debug("DATA:%s", json)
                response = await self._session.request(
                    method, url, json=json, headers=headers
                )
                response.raise_for_status()
        except ClientResponseError as error:
            if method == "get":
                raise RetrieveFailed(f"{url} not retrieved ({error.status})") from error
            if url == "login":
                raise AuthenticationFailed(
                    f"{error.message} ({error.status})"
                ) from error
            if method == "post" and error.status in [400, 500, 502] and self._retry > 0:
                self._retry -= 1
                await asyncio.sleep(3)
                return await self.request(url, method, json, auth)
            raise CommandFailed(
                f"Cmd failed {url} with {json} ({error.status} {error.message})"
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

    async def async_get_token(self) -> dict[str, Any]:
        """Get Token authentication."""
        if self._access_token is None or (
            (expire_at := self._access_token.get("expire_at"))
            and expire_at < time.time()
        ):
            payload = {"username": self._username, "password": self._password}
            self._access_token = await self.request(
                "login", method="post", json=payload, auth=True
            )
        return self._access_token
