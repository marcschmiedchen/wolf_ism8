import logging
import asyncio
import datetime
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


async def test_date_implementation(tst_ism8: wolf.Ism8):
    """ """
    print("trying to encode date 2024-05-30")
    tst_ism8.encode_datapoint(datetime.date(2024, 5, 30), 154)
    print("\n")

    # return if value is out of range
    if not wolf.validate_dp_range(154, datetime.date(2024, 5, 30)):
        print("Validation error. Should pass")
        return

    # return if value is out of range
    print("trying to encode date 2100-05-30. should be out of range")
    if wolf.validate_dp_range(154, datetime.date(2100, 5, 30)):
        print("Validation error. Should fail")
        return
    print("\n")

    # decoding tests
    print("trying to decode date 2007-06-04")
    test_bytes = bytearray(b"\x04\x06\x07")
    tst_ism8.decode_datapoint(159, test_bytes)

    print("trying to decode date 2032-12-20")
    test_bytes = bytearray(b"\x14\x0C\x20")
    # 20.12.2016
    tst_ism8.decode_datapoint(159, test_bytes)

    print("trying to decode date 2048-12-48 (!) should fail")
    test_bytes = bytearray(b"\x30\x0C\x30")
    # 20.12.2016
    tst_ism8.decode_datapoint(159, test_bytes)
    print("\n")

    print("trying to decode date from github log 1")
    test_bytes = bytearray(b"\x15\x05\x18")
    tst_ism8.decode_datapoint(155, test_bytes)

    print("encode/decode roundtrip")
    test_bytes = tst_ism8.encode_datapoint(datetime.date(2024, 5, 30), 154)
    if test_bytes:
        tst_ism8.decode_datapoint(155, test_bytes)
    print(tst_ism8._dp_values[155])
    assert tst_ism8._dp_values[155] == datetime.date(2024, 5, 30)


async def test_time_of_day_implementation(tst_ism8: wolf.Ism8):
    """ """
    print("trying to encode timeofday 12:00")
    tst_ism8.encode_datapoint(datetime.time(hour=12, minute=0), 161)

    # decoding tests
    print("trying to decode time 22:06:07")
    test_bytes = bytearray(b"\x16\x06\x07")
    tst_ism8.decode_datapoint(161, test_bytes)

    print("trying to decode time 00:00:00")
    test_bytes = bytearray(b"\x00\x00\x00")
    tst_ism8.decode_datapoint(161, test_bytes)

    print("trying to decode time from github log 1")
    test_bytes = bytearray(b"\x0d\x38\x00")
    tst_ism8.decode_datapoint(156, test_bytes)

    print("trying to decode time from github log 1")
    test_bytes = bytearray(b"\x10\x38\x00")
    tst_ism8.decode_datapoint(157, test_bytes)

    print("trying to decode time 48:12:116 (!) should fail, but datetime is robust")
    test_bytes = bytearray(b"\x30\x0C\x60")
    tst_ism8.decode_datapoint(161, test_bytes)

    print("encode/decode roundtrip")
    test_bytes = tst_ism8.encode_datapoint(datetime.time(hour=15, minute=38), 156)
    if test_bytes:
        tst_ism8.decode_datapoint(156, test_bytes)
    print(tst_ism8._dp_values[156])
    assert tst_ism8._dp_values[156] == datetime.time(hour=15, minute=38)


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
    # not in range
    tst_ism8.send_dp_value(57, "Comfort")

    tst_ism8.send_dp_value(57, "Automatikbetrieb")
    tst_ism8.send_dp_value(57, "Heizbetrieb")
    tst_ism8.send_dp_value(57, "Standby")
    tst_ism8.send_dp_value(57, "Sparbetrieb")
    tst_ism8.send_dp_value(57, "Gebäudeschutz")
    tst_ism8.send_dp_value(57, "Automatikbetrieb heizen")
    tst_ism8.send_dp_value(57, "Automatikbetrieb kühlen")


async def test_write_HVACMode149(tst_ism8: wolf.Ism8):
    """
    149 Programmwahl Heizkreis DPT_HVACMode_CWL Out / In
    """
    print("trying to change HVAC modes for CWL")
    # not in range
    tst_ism8.send_dp_value(149, "Comfort")

    tst_ism8.send_dp_value(149, "Standby")
    tst_ism8.send_dp_value(149, "Feuchteschutz")
    tst_ism8.send_dp_value(149, "Automatikbetrieb")


async def test_write_DHWMode(tst_ism8: wolf.Ism8):
    """
    58 Programmwahl Warmwasser DPT_DHWMode Out / In
    """
    # not in range
    tst_ism8.send_dp_value(58, "GibtsNicht")
    print("trying to change DHWMode to 'Auto'")
    tst_ism8.send_dp_value(58, "Automatikbetrieb")
    tst_ism8.send_dp_value(58, "Normal")
    await asyncio.sleep(5)


async def test_HVACCONTRMode(tst_ism8: wolf.Ism8):
    """
    177 Betriebsart DPT_HVACContrMode
    """
    print(tst_ism8.decode_datapoint(177, bytearray(b"\x01")))
    print(tst_ism8.decode_datapoint(177, bytearray(b"\x06")))
    print(tst_ism8.decode_datapoint(177, bytearray(b"\x07")))
    print(tst_ism8.decode_datapoint(177, bytearray(b"\x08")))
    print(tst_ism8.decode_datapoint(177, bytearray(b"\x09")))
    print(tst_ism8.encode_datapoint("GibtsNicht", 177))
    # not in range
    print("trying to change HVACContrMode to 'Frostschutz'")
    assert tst_ism8.encode_datapoint("Frostschutz", 177) == b"\x0b"


async def main():
    ism8 = wolf.Ism8()

    assert len(wolf.DATAPOINTS.items()) == 282
    assert len(ism8.get_all_devices()) == 21

    # _server = await setup_server(ism8)
    # await wait_for_connection(ism8)

    await test_write_on_off(ism8)
    await test_write_float(ism8)
    await test_write_HVACMode149(ism8)
    await test_date_implementation(ism8)
    await test_time_of_day_implementation(ism8)
    await test_HVACCONTRMode(ism8)
    print(ism8.get_value_range(57))
    print(ism8.get_value_range(157))
    print(ism8.get_value_range(158))
    print(ism8.get_value_range(179))
    await test_write_HVACMode57(ism8)
    await test_write_DHWMode(ism8)
    print("request all DP")
    ism8.request_all_datapoints()
    print(ism8.encode_datapoint(19711, 178))
    ism8.send_dp_value(153, 1)
    await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    _LOGGER = logging.getLogger(__name__)
    asyncio.run(main())
