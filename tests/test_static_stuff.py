import logging
import asyncio
import datetime
import pytest
import wolf_ism8 as wolf


@pytest.mark.asyncio
async def test_async_setup_server(tst_ism8: wolf.Ism8, _LOGGER):
    _eventloop = asyncio.get_running_loop()
    task1 = _eventloop.create_task(
        _eventloop.create_server(tst_ism8.factory, port=12004)
    )
    _LOGGER.debug("Setup Server")
    _server = await task1
    _LOGGER.debug(f"Waiting for ISM8 connection on {_server.sockets[0].getsockname()}")
    assert _server is not None
    return _server


@pytest.mark.asyncio
async def test_version(_LOGGER):
    """
    checks version reporting
    """
    _LOGGER.debug(f"Lib version {wolf.__version__}")
    assert wolf.__version__ is not None


@pytest.mark.asyncio
async def test_write_boolean_DP(tst_ism8: wolf.Ism8, _LOGGER):
    """
    72:  ('MK1', 'Mischer Zeitprogramm 1', 'DPT_Switch', True)
    """
    _LOGGER.debug("trying to activate MK1 Zeitprogramm Nbr 1")
    encoded_value = tst_ism8.encode_datapoint(72, 1)
    update_msg = tst_ism8.build_message(72, encoded_value)
    assert update_msg is not None


@pytest.mark.asyncio
async def test_write_float_DP(tst_ism8: wolf.Ism8, _LOGGER):
    """
    56: ("DKW", "Warmwassersolltemperatur", "DPT_Value_Temp", True),
    """
    _LOGGER.debug("trying to change warmwasserSollTemp to 51.4")
    tst_ism8.send_dp_value(56, 51.8)
    encoded_value = tst_ism8.encode_datapoint(51.8, 56)
    assert encoded_value is not None
    update_msg = tst_ism8.build_message(56, encoded_value)
    assert update_msg is not None
    await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_network_decoding(tst_ism8: wolf.Ism8, _LOGGER, caplog):
    # decoding tests
    caplog.set_level(logging.DEBUG)
    _LOGGER.debug("trying to decode network msg from github. should fail.")
    test_bytes = bytearray(
        b"\x06\x20\xf0\x80\x00\x14\x04\x00\x00\x00\xf0\x06\x00\xb2\x00\x01\x00\xb2\x03\x00"
    )
    assert tst_ism8.data_received(test_bytes) is True
    # network message should not yield datapoint in dictionary
    assert 178 not in tst_ism8._dp_values.keys()

    _LOGGER.debug("trying to decode valid network msg")
    test_bytes = bytearray(
        b"\x06\x20\xf0\x80\x00\x16\x04\x00\x00\x00\xf0\x06\x00\xb2\x00\x01\x00\xb2\x03\x02\x02\x62"
    )
    assert tst_ism8.data_received(test_bytes) is True
    assert 178 in tst_ism8._dp_values.keys()
    assert tst_ism8._dp_values[178] == pytest.approx(6.1)

    _LOGGER.debug("trying to decode compound network msg1")
    test_bytes = bytearray(
        b"\x06\x20\xf0\x80\x00\x1c\x04\x00\x00\x00\xf0\x06\x00\xb2\x00\x02\x00\xb2\x03\x02\x02\x62\x00\xb3\x03\x02\x02\x63"
    )
    assert tst_ism8.data_received(test_bytes) is True
    assert 178 in tst_ism8._dp_values.keys()
    assert tst_ism8._dp_values[178] == pytest.approx(6.1)
    assert 179 in tst_ism8._dp_values.keys()
    assert tst_ism8._dp_values[178] == pytest.approx(6.1)

    _LOGGER.debug("trying to decode real compound network msg with 5x same message")
    test_bytes = bytearray(
        b"\x06\x20\xf0\x80\x00\x15\x04\x00\x00\x00\xf0\x06\x00\x75\x00\x01\x00\x75\x03\x01\x00\x06\x20\xf0\x80\x00\x15\x04\x00\x00\x00\xf0\x06\x00\x75\x00\x01\x00\x75\x03\x01\x00\x06\x20\xf0\x80\x00\x15\x04\x00\x00\x00\xf0\x06\x00\x75\x00\x01\x00\x75\x03\x01\x00\x06\x20\xf0\x80\x00\x15\x04\x00\x00\x00\xf0\x06\x00\x75\x00\x01\x00\x75\x03\x01\x00\x06\x20\xf0\x80\x00\x15\x04\x00\x00\x00\xf0\x06\x00\x75\x00\x01\x00\x75\x03\x01\x00"
    )
    assert tst_ism8.data_received(test_bytes) is True
    assert 178 in tst_ism8._dp_values.keys()
    assert tst_ism8._dp_values[178] == pytest.approx(6.1)
    assert 179 in tst_ism8._dp_values.keys()
    assert tst_ism8._dp_values[178] == pytest.approx(6.1)

    _LOGGER.debug("trying to decode 1byte valid network msg")
    test_bytes = bytearray(
        b"\x06\x20\xf0\x80\x00\x15\x04\x00\x00\x00\xf0\x06\x00\xb2\x00\x01\x00\xb2\x03\x01\x0a"
    )
    assert tst_ism8.data_received(test_bytes) is True
    assert 178 in tst_ism8._dp_values.keys()
    assert tst_ism8._dp_values[178] == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_date_implementation(tst_ism8: wolf.Ism8, _LOGGER):
    """test of date implementation"""
    _LOGGER.debug("trying to encode date 2024-05-30")
    assert tst_ism8.encode_datapoint(datetime.date(2024, 5, 30), 154) is not None

    # return if value is out of range
    assert wolf.validate_dp_range(154, datetime.date(2024, 5, 30)) is True

    # return if value is out of range
    _LOGGER.debug("trying to encode date 2100-05-30. should be out of range")
    assert wolf.validate_dp_range(154, datetime.date(2100, 5, 30)) is False

    # decoding tests
    _LOGGER.debug("trying to decode date 2007-06-04")
    test_bytes = bytearray(b"\x04\x06\x07")
    tst_ism8.decode_datapoint(159, test_bytes)
    assert tst_ism8._dp_values[159] == datetime.date(2007, 6, 4)

    _LOGGER.debug("trying to decode date 2032-12-20")
    test_bytes = bytearray(b"\x14\x0C\x20")
    # 20.12.2016
    tst_ism8.decode_datapoint(159, test_bytes)
    assert tst_ism8._dp_values[159] == datetime.date(2032, 12, 20)

    _LOGGER.debug("trying to decode date 2048-12-48 (!) should fail")
    test_bytes = bytearray(b"\x30\x0C\x30")
    # 20.12.2016
    assert tst_ism8.decode_datapoint(159, test_bytes) is None

    _LOGGER.debug("trying to decode date from github log 1")
    test_bytes = bytearray(b"\x15\x05\x18")
    tst_ism8.decode_datapoint(155, test_bytes)

    _LOGGER.debug("encode/decode roundtrip")
    test_bytes = tst_ism8.encode_datapoint(datetime.date(2024, 5, 30), 154)
    assert test_bytes
    tst_ism8.decode_datapoint(155, test_bytes)
    assert tst_ism8._dp_values[155] == datetime.date(2024, 5, 30)


@pytest.mark.asyncio
async def test_time_of_day_implementation(tst_ism8: wolf.Ism8):
    """ """
    print("trying to encode timeofday 12:00")
    assert tst_ism8.encode_datapoint(datetime.time(hour=12, minute=0), 161) is not None

    # decoding tests
    print("trying to decode time 22:06:07")
    test_bytes = bytearray(b"\x16\x06\x07")
    tst_ism8.decode_datapoint(161, test_bytes)

    print("trying to decode time 00:00:00")
    test_bytes = bytearray(b"\x00\x00\x00")
    tst_ism8.decode_datapoint(161, test_bytes)
    assert tst_ism8._dp_values[161] == datetime.time(hour=0, minute=0)

    print("trying to decode time from github log 1")
    test_bytes = bytearray(b"\x0d\x38\x00")
    tst_ism8.decode_datapoint(156, test_bytes)
    assert tst_ism8._dp_values[156] == datetime.time(hour=13, minute=56)

    print("trying to decode time from github log 1")
    test_bytes = bytearray(b"\x10\x38\x00")
    tst_ism8.decode_datapoint(157, test_bytes)
    assert tst_ism8._dp_values[157] == datetime.time(hour=16, minute=56)

    print("trying to decode time 48:12:116 (!) should fail, but datetime is robust")
    test_bytes = bytearray(b"\x30\x0C\x60")
    tst_ism8.decode_datapoint(161, test_bytes)

    print("encode/decode roundtrip")
    test_bytes = tst_ism8.encode_datapoint(datetime.time(hour=15, minute=38), 156)
    assert test_bytes is not None
    tst_ism8.decode_datapoint(156, test_bytes)
    assert tst_ism8._dp_values[156] == datetime.time(hour=15, minute=38)


@pytest.mark.asyncio
async def test_scaling_implementation(tst_ism8: wolf.Ism8):
    """
    test scaling implementation
    """
    assert wolf.encode_scaling(100) == b"\xff"
    assert wolf.encode_scaling(0) == b"\x00"


@pytest.mark.asyncio
async def test_write_HVACMode57(tst_ism8: wolf.Ism8, _LOGGER):
    """
    57 Programmwahl Heizkreis DPT_HVACMode Out / In
    """
    _LOGGER.debug("trying to change HVAC modes")
    # not in range
    assert wolf.validate_dp_range(57, "Comfort") is False
    # ok
    assert wolf.validate_dp_range(57, "Automatikbetrieb") is True
    assert wolf.validate_dp_range(57, "Heizbetrieb") is True
    assert wolf.validate_dp_range(57, "Standby") is True
    assert wolf.validate_dp_range(57, "Automatikbetrieb kühlen") is True


@pytest.mark.asyncio
async def test_write_HVACMode149(tst_ism8: wolf.Ism8, _LOGGER):
    """
    149 Programmwahl Heizkreis DPT_HVACMode_CWL Out / In
    """
    _LOGGER.debug("test HVAC modes for CWL and direct heating")
    # not in range
    assert wolf.validate_dp_range(149, "Comfort") is False
    # ok
    assert wolf.validate_dp_range(149, "Automatikbetrieb") is True
    assert wolf.validate_dp_range(149, "Heizbetrieb") is False
    assert wolf.validate_dp_range(149, "Standby") is True
    assert wolf.validate_dp_range(149, "Feuchteschutz") is True
    # not in range
    assert wolf.validate_dp_range(70, "Comfort") is False
    # ok
    assert wolf.validate_dp_range(70, "Automatikbetrieb") is True
    assert wolf.validate_dp_range(70, "Heizbetrieb") is True
    assert wolf.validate_dp_range(70, "Standby") is True
    assert wolf.validate_dp_range(70, "Feuchteschutz") is False


@pytest.mark.asyncio
async def test_write_DHWMode(tst_ism8: wolf.Ism8):
    """
    58 Programmwahl Warmwasser DPT_DHWMode Out / In
    """
    # not in range
    assert wolf.validate_dp_range(58, "GibtsNicht") is False
    assert wolf.validate_dp_range(58, "Automatikbetrieb") is True
    assert wolf.validate_dp_range(58, "LegioProtect") is False


@pytest.mark.asyncio
async def test_HVACCONTRMode(tst_ism8: wolf.Ism8):
    """
    177 Betriebsart DPT_HVACContrMode
    """
    tst_ism8.decode_datapoint(177, bytearray(b"\x01"))
    assert tst_ism8._dp_values[177] == "Heizbetrieb"
    tst_ism8.decode_datapoint(177, bytearray(b"\x06"))
    assert tst_ism8._dp_values[177] == "Standby"
    tst_ism8.decode_datapoint(177, bytearray(b"\x07"))
    assert tst_ism8._dp_values[177] == "Test"
    tst_ism8.decode_datapoint(177, bytearray(b"\x08"))
    assert tst_ism8._dp_values[177] == "Emergency Heat"
    tst_ism8.decode_datapoint(177, bytearray(b"\x09"))
    assert tst_ism8._dp_values[177] == "Fan Only"

    assert tst_ism8.encode_datapoint("GibtsNicht", 177) is None
    assert tst_ism8.encode_datapoint("Auto", 177) == b"\x00"
    assert tst_ism8.encode_datapoint("Frostschutz", 177) == b"\x0b"


@pytest.fixture(scope="module")
def tst_ism8():
    return wolf.Ism8()


@pytest.fixture(scope="module")
def _LOGGER():
    return logging.getLogger(__name__)
