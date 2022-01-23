#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This example can be run safely as it won't change anything in your box configuration
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
        data = await api.async_get_device(device["did"])
        mode = data.get("attr").get("mode")
        logger.info("Heater : {} , mode : {}".format(name, mode))
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
