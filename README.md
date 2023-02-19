Implementation of an http server which manages messages to and from Wolf's ISM8 module.
Received datagrams are translated to pyhon datatypes and held in a internal dictionary for further 
usage. Writable datapoints can be encoded and sent to ISM8. 

This module was built in order to integrate a Wolf heating system into Home Assistant. The library 
takes advantage of the ASYNCIO-Library.

A test module is included, which will do the following tasks for demonstration purposes, 
without further configuration:
* print a list of all supported datapoints
* start listening on all IP-adresses on your host on port 12004 (stanard port for ISM8)
* connect to ISM8 as soon as it sends messages to your IP
* log/debug all incoming datagrams and sensor updates
* try to set 3 different datapoints on ISM8 as an example
