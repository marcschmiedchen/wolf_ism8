import asyncio
import logging

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


# @pytest.mark.asyncio
# async def test_write_hvac(tst_ism8: wolf.Ism8, _LOGGER):
#     """
#     try to send 57 Programmwahl Heizkreis DPT_HVACMode Out / In
#     """
#     _LOGGER.debug("trying to send DPT_HVACMode ")
#     tst_ism8.send_dp_value(57, "Automatikbetrieb")
#     assert(tst_ism8.read_sensor(57)=="Automatikbetrieb")

@pytest.fixture(scope="module")
def tst_ism8():
    return wolf.Ism8()

@pytest.fixture(scope="module")
def _LOGGER():
    return logging.getLogger(__name__)
