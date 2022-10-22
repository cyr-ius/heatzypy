"""Exceptions for Heatzy."""


class HeatzyException(Exception):
    """Heatzy exception."""


class HttpRequestFailed(HeatzyException):
    """Request exception."""


class AuthenticationFailed(HeatzyException):
    """Authentication exception."""


class RetrieveFailed(HeatzyException):
    """Retrieve exception."""


class CommandFailed(HeatzyException):
    """Command exception."""
