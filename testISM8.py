import logging
import asyncio
import wolf_ism8 as wolf


async def setup_server(tst_ism8: wolf.Ism8):
    _eventloop = asyncio.get_running_loop()
    task1 = _eventloop.create_task(
        _eventloop.create_server(tst_ism8.factory, port=12004)
    )
    print("Setup Server")
    _server = await task1
    _LOGGER.debug(f"Waiting for ISM8 connection on {_server.sockets[0].getsockname()}")
    return _server


async def wait_for_connection(tst_ism8: wolf.Ism8):
    while tst_ism8._transport is None:
        print("no connection yet")
        await asyncio.sleep(5)
    await asyncio.sleep(2)


async def test_write_on_off(tst_ism8: wolf.Ism8):
    """
    72:  ('MK1', 'Mischer Zeitprogramm 1', 'DPT_Switch', True)
    """
    print("trying to activate MK1 Zeitprogramm Nbr 1")
    tst_ism8.send_dp_value(72, 1)
    await asyncio.sleep(10)


async def test_write_float(tst_ism8: wolf.Ism8):
    """
    56: ("DKW", "Warmwassersolltemperatur", "DPT_Value_Temp", True),
    """
    print("trying to change warmwasserSollTemp to 51.4")
    tst_ism8.send_dp_value(56, 51.8)
    await asyncio.sleep(10)


async def test_write_scaling(tst_ism8: wolf.Ism8):
    """
    no test possible....
    """
    pass
    # tst_ism8.send_dp_value(xx, yy)
    # await asyncio.sleep(20)


async def test_write_HVACMode57(tst_ism8: wolf.Ism8):
    """
    57 Programmwahl Heizkreis DPT_HVACMode Out / In
    """
    print("trying to change HVAC modes")
    # tst_ism8.send_dp_value(57, 'Comfort')
    # tst_ism8.send_dp_value(57, 'Standby')
    # not in range
    tst_ism8.send_dp_value(57, "Building Protection")
    tst_ism8.send_dp_value(57, "Auto")
    await asyncio.sleep(5)


async def test_write_HVACMode149(tst_ism8: wolf.Ism8):
    """
    57 Programmwahl Heizkreis DPT_HVACMode Out / In
    """
    print("trying to change HVAC modes")
    tst_ism8.send_dp_value(149, "Comfort")
    # not in range
    tst_ism8.send_dp_value(149, "Standby")
    # not in range
    tst_ism8.send_dp_value(149, "Building Protection")
    tst_ism8.send_dp_value(149, "Auto")
    await asyncio.sleep(5)


async def test_write_DHWMode(tst_ism8: wolf.Ism8):
    """
    58 Programmwahl Warmwasser DPT_DHWMode Out / In
    """
    print("trying to change DHWMode to 'Auto'")
    tst_ism8.send_dp_value(58, "GibtsNicht")
    # not in range
    tst_ism8.send_dp_value(58, "Auto")
    tst_ism8.send_dp_value(58, "Normal")
    await asyncio.sleep(5)


async def main():
    ism8 = wolf.Ism8()
    # for keys, values in wolf.DATAPOINTS.items():
    #    _LOGGER.debug(f"{keys}:  {values}")

    print(ism8.get_all_devices())

    _server = await setup_server(ism8)
    await wait_for_connection(ism8)
    # await test_write_on_off(ism8)
    # await asyncio.sleep(5)
    # await test_write_float(ism8)
    # await test_write_HVACMode149(ism8)
    # print (ism8.get_value_area(57))
    # await test_write_HVACMode57(ism8)
    # await test_write_DHWMode(ism8)
    # print("request all DP")
    # ism8.request_all_datapoints()
    await asyncio.sleep(10)
    _server.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    _LOGGER = logging.getLogger(__name__)
    asyncio.run(main())
