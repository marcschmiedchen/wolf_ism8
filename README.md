Implementation of an http server which communicates with WOLF HVAC systems via their ISM8 module. Received datagrams are translated to pyhon datatypes and held in a internal dictionary for further 
usage. Writable datapoints are correctly encoded and sent to ISM8. 

This python package was built in order to integrate a [WOLF](https://www.wolf.eu) heating system into the [Home Assistant](https://www.home-assistant.io) ecosystem. The library takes advantage of the ASYNCIO-Library.

A test module is included in the root of the project, which conducts the following tasks for demonstration purposes (no configuration needed)

* print a list of all supported datapoints
* start listening on all IP-adresses on your host on port 12004 (standard port for ISM8)
* connect to ISM8 as soon as it sends messages to your IP
* log/debug all incoming datagrams and sensor updates
* try to set 3 different datapoints on ISM8 as an example