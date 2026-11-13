Implementation of an http server which communicates with WOLF HVAC systems via their ISM8 module. Documentation can be found on the official Homepage of Wolf, which provides detailed documentation on https://oxomi.com/service/json/catalog/pdf?portal=2024876&user=&roles=&accessToken=&catalog=10572791

Received datagrams are translated to python datatypes and held in a internal dictionary for further usage. Callback functionality is implemented for push-style integrations. R/W datapoints can be encoded and sent to ISM8.

This python package was built in order to integrate a [WOLF](https://www.wolf.eu) heating system into the [Home Assistant](https://www.home-assistant.io) ecosystem. The library takes advantage of the ASYNCIO-Library.

### Connection callbacks

`register_connection_callback(cb)` is called with the device IP when the ISM8
connects, `register_disconnect_callback(cb)` on every disconnect: a dropped socket,
a watchdog expiry or `close()`. A reconnecting ISM8 simply replaces the previous
socket — the connection callback fires again and cached values are kept.

Nothing is ever unregistered for you. Datapoint and connection callbacks survive
every disconnect, so call `remove_callback(dp_id)`,
`unregister_connection_callback()` and `unregister_disconnect_callback()` in your
own teardown before closing the connection.
