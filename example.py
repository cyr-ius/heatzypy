#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This example can be run safely as it won't change anything.
"""

import asyncio
import logging

from heatzypy import CommandFailed, HeatzyClient, HeatzyException

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

USERNAME = "my-login"
PASSWORD = "my-password"


async def main():
    """Main function."""
    api = HeatzyClient(USERNAME, PASSWORD)
    try:
        devices = await api.async_get_devices()
        for uniqe_id, device in devices.items():
            name = device.get("dev_alias")

            # Get data device
            data = await api.async_get_device(uniqe_id)
            mode = data.get("attr").get("mode")
            logger.info("Heater : %s , mode : %s", name, mode)

            # set all Pilot v2 devices to preset 'eco' mode.
            try:
                await api.async_control_device(uniqe_id, {"attrs": {"mode": "stop"}})
            except CommandFailed as error:
                logger.error(error)
    except HeatzyException as error:
        logger.error(str(error))
    await api.async_close()


loop = asyncio.new_event_loop()
loop.run_until_complete(main())
