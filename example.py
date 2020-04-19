#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This example can be run safely as it won't change anything in your box configuration
'''

import asyncio
import logging

from heatzypy import HeatzyClient

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

username = "my-login"
password = "my-password"

api = HeatzyClient(username, password)
devices = await api.async_get_devices()
for device in devices:
    data = await api.async_get_device_info(device["did"])
    logger.info("Heater : {} , mode : {}".format(data.get("dev_alias"), data.get("attr").get("mode")))
