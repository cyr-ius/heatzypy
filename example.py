#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This example can be run safely as it won't change anything in your box configuration

There are two modes to control Heatzy modules:
    - Classic mode by calling the Rest API
    - Websocket mode by calling the websocket module
"""

import asyncio
import logging
from typing import Any

from aiohttp import ClientSession
import yaml  # noqa

from heatzypy import AuthenticationFailed, HeatzyClient, HeatzyException

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Fill out the secrets in secrets.yaml, you can find an example
# _secrets.yaml file, which has to be renamed after filling out the secrets.
with open("./secrets.yaml", encoding="UTF-8") as file:
    secrets = yaml.safe_load(file)

USERNAME = secrets["USERNAME"]
PASSWORD = secrets["PASSWORD"]


async def async_main() -> None:
    """Main function."""
    async with ClientSession() as session:
        api = HeatzyClient(USERNAME, PASSWORD, session)

        def callback(devices: dict[str, Any]) -> None:
            for uniqe_id, device in devices.items():
                name = device.get("dev_alias")
                mode = device.get("attrs", {}).get("mode")
                lock = device.get("attrs", {}).get("lock_switch")
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
            asyncio.ensure_future(api.websocket.async_listen())
        except AuthenticationFailed as error:
            logger.error("Auth failed (%s)", error)
        except HeatzyException as error:
            logger.error(str(error))

        while api.websocket.is_connected:
            logger.info(f"Connected: {api.websocket.is_connected}")
            logger.info(f"Logged: {api.websocket.is_logged}")
            logger.info(f"All devices updated: {api.websocket.is_updated}")
            await asyncio.sleep(1)

        await api.async_close()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(async_main())
