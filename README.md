Implementation of an http server which manages messages to and from Wolf's Heating ISM8 module.
Received datagrams are translated to pyhon datatypes and held in a internal dictionary for further 
usage. Writable datapoints can be encoded and sent to ISM8. 

This module was built in order to integrate a Wolf heating system into Home Assistant. The library 
takes advantage of the ASYNCIO-Library.