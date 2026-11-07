"""Test helpers for Heatzy."""

from aiohttp import ClientSession
import pytest

from heatzypy import HeatzyClient
from tests import load_fixture


@pytest.fixture
async def api():
    """Heatzy client with a session created inside the running event loop."""
    async with ClientSession() as session:
        yield HeatzyClient(
            username="xx",
            password="password",
            session=session,
            time_out=30,
            region="EU",
            use_tls=True,
        )


@pytest.fixture
def mock_devices():
    """Mock devices."""
    return load_fixture("devices.json")


@pytest.fixture
def mock_device():
    """Mock devices."""
    return load_fixture("device.json")


@pytest.fixture
def mock_attributes():
    """Mock devices."""
    return load_fixture("attributes.json")


@pytest.fixture
def mock_attribut(request):
    """Mock device."""
    device = request.param
    all_attrs = load_fixture("attributes.json")
    return all_attrs[device]


@pytest.fixture
def mock_token():
    """Mock devices."""
    return {"expire_at": "", "token": "123456"}
