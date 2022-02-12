#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This example can be run safely as it won't change anything.
"""

import asyncio
import logging

from heatzypy.heatzy import HeatzyClient

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

USERNAME = "my-login"
PASSWORD = "my-password"


async def main():
    api = HeatzyClient(USERNAME, PASSWORD)

    devices = await api.async_get_devices()
    for device in devices:
        name = device.get("dev_alias")

        # Get data device
        data = await api.async_get_device(device["did"])
        logger.info("Heater : {} , mode : {}".format(name, data.get("attr").get("mode")))

        # set all Pilot v2 devices to preset 'eco' mode.
        # await api.async_control_device(device["did"], {"attrs": {"mode": "eco"}})

    await api.async_close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
