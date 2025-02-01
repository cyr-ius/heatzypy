"""heatzypy package."""

from .exception import (
    AuthenticationFailed,
    CommandFailed,
    ConnectionFailed,
    HeatzyException,
    RetrieveFailed,
    TimeoutExceededError,
)
from .heatzy import HeatzyClient

__all__ = [
    "AuthenticationFailed",
    "CommandFailed",
    "ConnectionFailed",
    "HeatzyClient",
    "HeatzyException",
    "RetrieveFailed",
    "TimeoutExceededError",
]
