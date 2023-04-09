Implementation of an http server which communicates with WOLF HVAC systems via their ISM8 module. Received datagrams are translated to pyhon datatypes and held in a internal dictionary for further 
usage. Writable datapoints are correctly encoded and sent to ISM8. 

This python package was built in order to integrate a [WOLF](https://www.wolf.eu) heating system into the [Home Assistant](https://www.home-assistant.io) ecosystem. The library takes advantage of the ASYNCIO-Library.