Implementation of an http server which communicates with WOLF HVAC systems via their ISM8 module. Documentation can be found on the official Homepage of Wolf, which provides detailed documentation on https://oxomi.com/service/json/catalog/pdf?portal=2024876&user=&roles=&accessToken=&catalog=10572791

Received datagrams are translated to python datatypes and held in a internal dictionary for further usage. Callback functionality is implemented for push-style integrations. R/W datapoints can be encoded and sent to ISM8.

This python package was built in order to integrate a [WOLF](https://www.wolf.eu) heating system into the [Home Assistant](https://www.home-assistant.io) ecosystem. The library takes advantage of the ASYNCIO-Library.

### Usage

`Ism8` is the asyncio protocol *and* its own factory. The ISM8 module dials in, so
the caller only starts a server and hands the instance over:

```python
import asyncio
from wolf_ism8 import Ism8

ism8 = Ism8()
ism8.set_watchdog_timeout(60)
await asyncio.get_running_loop().create_server(ism8, port=12004)
```

Nothing is pushed until the ISM8 dials in, so ask for the initial values from the
connection callback, which fires with the device IP:

```python
def on_connect(ip):
    print(f"ISM8 connected: {ip}")
    ism8.request_all_datapoints()

ism8.register_connection_callback(on_connect)
```

#### Reading values

`register_callback(cb, dp_id)` subscribes to one datapoint. The callback takes no
arguments — read the value with `read_sensor(dp_id)`, which serves the last cached
value and keeps it across disconnects:

```python
def on_boiler_temp():
    print(ism8.read_sensor(4))

ism8.register_callback(on_boiler_temp, 4)
# ...
ism8.remove_callback(4)
```

For building entity lists, `get_all_sensors()` returns the datapoint table itself
(`dp_id → (device_name, datapoint_name, data_type, writable_flag)`) and
`get_all_devices()` the sorted device names. `connected()` and
`get_remote_ip_address()` report the link state.

#### Writing values

`send_dp_value(dp_id, value)` validates the value against the datapoint's allowed
range, encodes it and sends it. It returns `False` and logs if the datapoint is not
writable, the value is out of range, or the link is down.

```python
ism8.send_dp_value(4, 42.0)
```

#### Helpers

Some BM-2 datapoints report which appliances or circuits exist as one bit per
component: `is_bitfield(dp_id)` tells whether a datapoint is one of these and
`decode_bitfield(dp_id, value)` returns the names of the components present.
`first_fw_version(dp_id)` gives the minimum ISM8 firmware version a datapoint
exists in, so an integration can hide datapoints an older device never sends.

### Connection callbacks

`register_connection_callback(cb)` is called with the device IP when the ISM8
connects, `register_disconnect_callback(cb)` on every disconnect: a dropped socket,
a watchdog expiry or `close()`. A reconnecting ISM8 simply replaces the previous
socket — the connection callback fires again and cached values are kept.

### Inactivity watchdog

`Ism8()` starts with the watchdog off. `set_watchdog_timeout(seconds)` enables it:
the connection is aborted after that many seconds without incoming data, so a
power-lost ISM8 (which never sends a FIN) is detected. The timeout is stored, any
pending timer is dropped and the timer is armed immediately when the connection is
live — an already-silent device is covered from the call onwards. Call it again with
`None` to switch the watchdog off.

Nothing is ever unregistered for you. Datapoint and connection callbacks survive
every disconnect, so call `remove_callback(dp_id)`,
`unregister_connection_callback()` and `unregister_disconnect_callback()` in your
own teardown before closing the connection.
