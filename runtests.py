import logging
import asyncio
import wolf_ism8 as w

async def setup_server(tst_ism8 : w.Ism8):
    _eventloop=asyncio.get_running_loop()
    task1=_eventloop.create_task(_eventloop.create_server(tst_ism8.factory, "", 12004))
    print ("Setup Server")    
    _server=await task1
    _LOGGER.debug("Waiting for ISM8 connection on %s", _server.sockets[0].getsockname())
    
async def test_connection(tst_ism8 : w.Ism8):
    while tst_ism8._transport==None:
        print ('no connection yet')
        await asyncio.sleep(1)

async def test_write_on_off(tst_ism8 : w.Ism8):
    '''
    72:  ('MK1', 'Mischer Zeitprogramm 1', 'DPT_Switch', True)
    73:  ('MK1', 'Mischer Zeitprogramm 2', 'DPT_Switch', True)
    74:  ('MK1', 'Mischer Zeitprogramm 3', 'DPT_Switch', True)
    '''
    
    print ('waiting to send')
    await asyncio.sleep(1)
    tst_ism8.send_dp_value(72, 1)
    print ('waiting for ACK')
    await asyncio.sleep(10)
        
async def main():
    ism8=w.Ism8()
    await setup_server(ism8)
    await test_connection(ism8)
    await test_write_on_off(ism8)
    


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    _LOGGER = logging.getLogger(__name__)
    asyncio.run(main())


    
