import logging
import asyncio
import wolf_ism8 as wolf


async def setup_server(tst_ism8: wolf.Ism8):
    _eventloop = asyncio.get_running_loop()
    task1 = _eventloop.create_task(_eventloop.create_server(tst_ism8.factory, "", 12004))
    print("Setup Server")
    _server = await task1
    _LOGGER.debug("Waiting for ISM8 connection on %s", _server.sockets[0].getsockname())


async def wait_for_connection(tst_ism8: wolf.Ism8):
    while tst_ism8._transport == None:
        print("no connection yet")
        await asyncio.sleep(5)

async def test_write_on_off(tst_ism8: wolf.Ism8):
    """
    72:  ('MK1', 'Mischer Zeitprogramm 1', 'DPT_Switch', True)
    """
    print("trying to activate MK1 Zeitprogramm Nbr 1")
    tst_ism8.send_dp_value(72, 1)
    await asyncio.sleep(20)

async def test_write_float(tst_ism8: wolf.Ism8):
    """
    56: ("DKW", "Warmwassersolltemperatur", "DPT_Value_Temp", True),
    """
    print("trying to change warmwasserSollTemp to 51.4")
    tst_ism8.send_dp_value(56, 51.4)
    await asyncio.sleep(20)
    

async def test_write_scaling(tst_ism8: wolf.Ism8):
    """
    no test possible....  
    """
    pass
    #tst_ism8.send_dp_value(xx, yy)
    #await asyncio.sleep(20)
    
async def test_write_HVACMode(tst_ism8: wolf.Ism8):
    """
    57 Programmwahl Heizkreis DPT_HVACMode Out / In
    """
    print("trying to change HVAC to 'Auto'")
    tst_ism8.send_dp_value(57, 0)
    await asyncio.sleep(5)
    tst_ism8.request_all_datapoints()
    await asyncio.sleep(20)

async def test_write_DHWMode(tst_ism8: wolf.Ism8):
    """
    58 Programmwahl Warmwasser DPT_DHWMode Out / In
    """
    print("trying to change DHWMode to 'Auto'")
    tst_ism8.send_dp_value(58, 0)
    await asyncio.sleep(5)
    tst_ism8.request_all_datapoints()
    await asyncio.sleep(20)

async def main():
    ism8 = wolf.Ism8()
    for keys, values in wolf.DATAPOINTS.items():
        _LOGGER.debug("%s:  %s" % (keys, values))

    await setup_server(ism8)
    await wait_for_connection(ism8)
    await test_write_on_off(ism8)
    await test_write_float(ism8)
    await test_write_HVACMode(ism8)
    await test_write_DHWMode(ism8)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    _LOGGER = logging.getLogger(__name__)
    asyncio.run(main())
