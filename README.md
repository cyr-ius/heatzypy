# heatzypy
Manage your Heatzy in Python

Check your config, enable or disable heater, change preset mode.

Install
-------
Use the PIP package manager
```bash
$ pip install heatzypy
```

Or manually download and install the last version from github
```bash
$ git clone https://github.com/cyr-ius/heatzypy.git
$ python setup.py install
```
Get started
-----------
```python
# Import the heatzypy package.
from heatzypy import HeatzyClient

api = HeatzyClient("username", "password")

async def async_demo():
    devices = await api.async_get_devices()
    for device in devices:
        name = device.get("dev_alias")
        data = await api.async_get_device(device["did"])
        mode = data.get("attr").get("mode")
        logger.info("Heater : {} , mode : {}".format(name, mode))

```
Have a look at the [example.py](https://github.com/cyr-ius/heatzypy/blob/master/example.py) for a more complete overview.

Notes on HTTPS
--------------
Not implemented
