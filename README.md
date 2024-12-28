Implementation of an http server which communicates with WOLF HVAC systems via their ISM8 module. Documentation can be found on the official Homepage of Wolf, which provides detailed documentation on https://oxomi.com/service/json/catalog/pdf?portal=2024876&user=&roles=&accessToken=&catalog=10572791

Received datagrams are translated to pyhon datatypes and held in a internal dictionary for further usage. Callback functionality is implemented for push-style integrations. R/W datapoints can be encoded and sent to ISM8. 

This python package was built in order to integrate a [WOLF](https://www.wolf.eu) heating system into the [Home Assistant](https://www.home-assistant.io) ecosystem. The library takes advantage of the ASYNCIO-Library.