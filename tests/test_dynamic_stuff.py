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


class _StubTransport:
    """
    minimal transport stand-in for watchdog tests. Like asyncio, abort() makes the
    loop report the connection as lost afterwards - emulated by calling back into
    the protocol, otherwise the watchdog would never reach connection_lost().
    """

    def __init__(self, protocol=None):
        self.aborted = 0
        self.closed = 0
        self.written = []
        self._protocol = protocol

    def get_extra_info(self, name):
        return ("127.0.0.1", 12004)

    def abort(self):
        self.aborted += 1
        if self._protocol is not None:
            self._protocol.connection_lost(None)

    def close(self):
        self.closed += 1

    def write(self, data):
        self.written.append(bytes(data))


# valid network message, same bytes as used in test_static_stuff.py
_VALID_MSG = bytearray(
    b"\x06\x20\xf0\x80\x00\x16\x04\x00\x00\x00\xf0\x06\x00\xb2\x00\x01\x00\xb2\x03\x02\x02\x62"
)


@pytest.mark.asyncio
async def test_watchdog_aborts_silent_connection(_LOGGER):
    """
    Connection that goes silent (no TCP FIN, e.g. ISM8 power loss) must be
    aborted by the watchdog and reported as disconnected.
    """
    ism8 = wolf.Ism8(watchdog_timeout=0.1)
    transport = _StubTransport(ism8)
    disconnects = []
    ism8.register_disconnect_callback(lambda: disconnects.append(1))

    ism8.connection_made(transport)
    assert ism8.connected() is True

    await asyncio.sleep(0.2)

    assert transport.aborted == 1
    assert ism8.connected() is False
    assert disconnects == [1]


@pytest.mark.asyncio
async def test_watchdog_reset_by_data(_LOGGER):
    """
    Incoming data must push the deadline out: a connection receiving data
    within the timeout is never aborted.
    """
    ism8 = wolf.Ism8(watchdog_timeout=0.2)
    transport = _StubTransport()

    ism8.connection_made(transport)
    # re-feed every 50ms for 400ms - twice the timeout in total
    for _ in range(8):
        await asyncio.sleep(0.05)
        assert ism8.data_received(_VALID_MSG) is True

    assert transport.aborted == 0
    assert ism8.connected() is True
    # clean up: no timer may outlive the test
    ism8.connection_lost(None)
    assert ism8._watchdog_handle is None


@pytest.mark.asyncio
async def test_watchdog_handle_cleared(_LOGGER):
    """watchdog handle is cleared after expiry AND after a manual disconnect"""
    ism8 = wolf.Ism8(watchdog_timeout=0.1)
    transport = _StubTransport(ism8)

    ism8.connection_made(transport)
    assert ism8._watchdog_handle is not None
    await asyncio.sleep(0.2)
    assert ism8._watchdog_handle is None
    assert transport.aborted == 1
    # the abort() above already triggered connection_lost() like real asyncio
    assert ism8.connected() is False

    # a late connection_lost from asyncio must not fire a second callback
    disconnects = []
    ism8.register_disconnect_callback(lambda: disconnects.append(1))
    ism8.connection_lost(None)
    assert disconnects == [1]
    assert ism8._watchdog_handle is None
    assert ism8._transport is None
