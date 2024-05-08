#!/usr/bin/env python3
"""
This example can be run safely as it won't change anything.

There are two modes to control Heatzy modules:
    - Classic mode by calling the Rest API
    - Websocket mode by calling the websocket module
"""

import asyncio
import logging
from typing import Any

from heatzypy import AuthenticationFailed, HeatzyClient, HeatzyException

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

USERNAME = "my-login"
PASSWORD = "my-password"


async def async_main() -> None:
    """Main function."""
    api = HeatzyClient(USERNAME, PASSWORD)

    def callback(devices: dict[str, Any]) -> None:
        """Display devices."""
        for uniqe_id, device in devices.items():
            name = device.get("dev_alias")
            mode = device.get("attrs").get("mode")
            lock = device.get("attrs").get("lock_switch")
            logger.info("Heater: %s ,mode: %s,lock: %s", name, mode, lock)
        logger.info("---------------------------------------")

    # Call Heatzy Rest API

    try:
        devices = await api.async_get_devices()
        callback(devices)
        for uniqe_id, device in devices.items():
            # set all Pilot v2 devices to preset 'eco' mode.
            try:
                # await api.async_control_device(uniqe_id, {"attrs": {"mode": "eco"}})
                pass
            except HeatzyException as error:
                logger.error(error)
    except AuthenticationFailed as error:
        logger.error("Auth failed (%s)", error)
    except HeatzyException as error:
        logger.error(str(error))

    # Listen Heatzy webscoket

    try:
        api.websocket.register_callback(callback)
        await api.websocket.async_connect(auto_subscribe=True, all_devices=True)
        await api.websocket.async_listen()
    except AuthenticationFailed as error:
        logger.error("Auth failed (%s)", error)
    except HeatzyException as error:
        logger.error(str(error))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())
