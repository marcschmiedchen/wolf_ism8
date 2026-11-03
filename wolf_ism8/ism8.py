# pylint: disable-msg=W1203
"""
Module for gathering info and sending commands from/to Wolf HVAC System via ISM8 adapter
"""

import asyncio
import logging
from collections.abc import Callable

from .ism8_constants import (
    DATAPOINTS,
    DATATYPES,
    DP_BITFIELDS,
    DP_VALUES_ALLOWED,
    DT_UNIT,
    ISM_ACK_DP_MSG,
    ISM_CONN_HEAD,
    ISM_HEADER,
    ISM_REQ_DP_MSG,
    ISM_SERVICE_TRANSMIT,
    IX_DEVICENAME,
    IX_NAME,
    IX_RW_FLAG,
    IX_TYPE,
)
from .ism8_helper_functions import (
    _DECODERS,
    _ENCODERS,
    decode_bitfield,
    decode_int,
    postprocess_data,
    validate_dp_range,
)


class Ism8(asyncio.Protocol):
    """
    This protocol class listens to messages from ISM8 module and
    feeds data into internal data dictionary. Also provides functionality for
    writing datapoints.
    """

    @staticmethod
    def get_device(dp_id: int) -> str:
        """returns device ID from private array of sensor-readings"""
        return DATAPOINTS.get(dp_id, ["", "", "", "", ""])[IX_DEVICENAME]

    @staticmethod
    def get_name(dp_id: int) -> str:
        """returns sensor name from static Dictionary"""
        return DATAPOINTS.get(dp_id, ["", "", "", "", ""])[IX_NAME]

    @staticmethod
    def get_type(dp_id: int) -> str:
        """returns sensor type from static Dictionary"""
        return DATAPOINTS.get(dp_id, ["", "", "", "", ""])[IX_TYPE]

    @staticmethod
    def get_unit(dp_id: int) -> str:
        """returns datapoint unit from static Dictionary"""
        if dp_id in DATAPOINTS:
            dp_type = DATAPOINTS[dp_id][IX_TYPE]
            return DATATYPES[dp_type][DT_UNIT]
        return ""

    @staticmethod
    def is_writable(dp_id: int) -> bool:
        """returns writable flag from static Dictionary"""
        return DATAPOINTS[dp_id][IX_RW_FLAG] if dp_id in DATAPOINTS else False

    @staticmethod
    def get_value_range(dp_id: int):
        """returns allowed values for write operations"""
        return DP_VALUES_ALLOWED.get(dp_id, ())

    @staticmethod
    def decode_bitfield(dp_id: int, value) -> tuple[str, ...]:
        """returns the components a BM-2 bitfield datapoint reports as present.

        Empty tuple for datapoints that do not carry a bitfield, so callers can
        offer the decoded names on every datapoint without checking the id first.
        """
        return decode_bitfield(dp_id, value)

    @staticmethod
    def is_bitfield(dp_id: int) -> bool:
        """returns whether this datapoint encodes presence of components per bit"""
        return dp_id in DP_BITFIELDS

    @staticmethod
    def get_all_sensors() -> dict:
        """returns dictionary (nbr -> list of properties) for all ISM8 datapoints"""
        return DATAPOINTS

    @staticmethod
    def get_all_devices():
        """returns list of all ISM8 devices. Unique first Component of DATAPOINTS"""
        return sorted({x[IX_DEVICENAME] for x in DATAPOINTS.values()})

    @staticmethod
    def first_fw_version(dp_id: int) -> str:
        """returns first ISM8-firmware version of datapoint implementation"""
        match dp_id:
            case _ if 191 < dp_id < 209:
                return "1.50"
            case 209 | 210 | 211 | 251:
                return "1.70"
            case _ if 354 < dp_id < 362:
                return "1.70"
            case _ if 363 < dp_id < 373:
                return "1.80"
            case _ if 211 < dp_id < 251:
                return "1.90"
            case _:
                return "1.00"

    def __init__(self, keepalive_timeout: float | None = 90.0):
        """
        keepalive_timeout: seconds without any data from the ISM8 after which the
        connection is considered dead. The ISM8 sends a keepalive datapoint (767)
        roughly every 30s, so three missed keepalives are a safe default. A power
        cut of the ISM8 does not send a TCP FIN, so without this watchdog the
        half-open connection would never be noticed. None disables the watchdog.
        """
        # the datapoint-values from the device are stored and buffered here
        self._dp_values = {}
        self._dp_discard_count = {}
        self._transport = None
        self._remote_ip_address = None
        self._connected = False
        self.log = logging.getLogger(__name__)
        # the callbacks for all datapoints are stored in a dictionary
        self._callback_on_data = {}
        # its possible to register a callback once the connection is established
        self._callback_on_connection = None
        # listeners for connection state changes, called with True/False
        self._connection_state_callbacks: list[Callable[[bool], None]] = []
        # currently active per-connection protocol (see factory)
        self._active_connection = None
        # watchdog: declares the connection dead when the ISM8 goes silent
        self._keepalive_timeout = keepalive_timeout
        self._watchdog: asyncio.TimerHandle | None = None

    def factory(self):
        """factory method for asyncio: one protocol object per TCP connection.

        All connections share this Ism8 instance (datapoint cache, callbacks), but
        each keeps its own transport and receive buffer. That way the late
        connection_lost of a stale connection cannot tear down a newer one.
        """
        return _Ism8Connection(self)

    def _on_connection_made(self, conn, transport) -> None:
        """called by a per-connection protocol once the ISM8 has connected"""
        old = self._active_connection
        if old is not None and old is not conn and old.transport is not None:
            self.log.info("New ISM8 connection, closing previous connection")
            old.transport.close()
        self._active_connection = conn
        self.connection_made(transport)

    def _on_connection_lost(self, conn, exc) -> None:
        """called by a per-connection protocol when its connection ends"""
        if conn is not self._active_connection:
            self.log.debug("Stale ISM8 connection closed, ignoring")
            return
        self._active_connection = None
        self.connection_lost(exc)

    def get_remote_ip_address(self):
        """returns the IP address of the ISM8 module after connection"""
        return self._remote_ip_address

    def request_all_datapoints(self) -> None:
        """send 'request all datapoints' to ISM8"""
        req_msg = bytearray(ISM_REQ_DP_MSG)
        self.log.debug("Sending REQ_ALL_DP: %s ", req_msg.hex(":"))
        if not self._connected or self._transport is None:
            self.log.error("No Connection to ISM8 Module")
        else:
            self._transport.write(req_msg)  # type: ignore

    def connection_made(self, transport) -> None:
        """is called as soon as an ISM8 connects to server"""
        self._transport = transport
        self._connected = True
        self._remote_ip_address = transport.get_extra_info("peername")[0]
        self.log.info("Connection from ISM8: %s", self._remote_ip_address)
        self._restart_watchdog()
        if self._callback_on_connection is not None:
            self._callback_on_connection(self._remote_ip_address)
        self._notify_connection_state(True)

    def connection_lost(self, exc):
        """
        Is called when connection ends. closes socket.
        """
        self.log.info("ISM8 connection closed (%s)", exc)
        self._cancel_watchdog()
        self._connected = False
        if self._transport:
            self._transport.close()
        self._transport = None
        self._notify_connection_state(False)

    def _restart_watchdog(self) -> None:
        """(re)arms the keepalive watchdog; called on connect and on every message"""
        self._cancel_watchdog()
        if not self._keepalive_timeout:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # called outside of an event loop (e.g. unit tests feeding data_received)
            return
        self._watchdog = loop.call_later(
            self._keepalive_timeout, self._on_watchdog_expired
        )

    def _cancel_watchdog(self) -> None:
        if self._watchdog is not None:
            self._watchdog.cancel()
            self._watchdog = None

    def _on_watchdog_expired(self) -> None:
        """no data for keepalive_timeout seconds: drop the (half-open) connection.
        Aborting the transport makes asyncio call connection_lost, which in turn
        flags the integration. A reconnecting ISM8 opens a fresh connection."""
        self._watchdog = None
        self.log.warning(
            "No data from ISM8 for %s s, assuming connection lost",
            self._keepalive_timeout,
        )
        conn = self._active_connection
        if conn is not None and conn.transport is not None:
            conn.transport.abort()
        else:
            self.connection_lost(None)

    def _notify_connection_state(self, connected: bool) -> None:
        for callback in list(self._connection_state_callbacks):
            try:
                callback(connected)
            except Exception:  # pylint: disable=broad-except
                self.log.exception("connection state callback failed")

    def register_callback(self, cb, dp_nbr):
        """registers a callback for a datapoint; is called when data is received"""
        self._callback_on_data[dp_nbr] = cb

    def remove_callback(self, dp_nbr):
        """removes a callback for a datapoint"""
        self._callback_on_data.pop(dp_nbr, None)

    def register_connection_callback(self, cb):
        """registers a callback for the connection; is called when connection is made"""
        self._callback_on_connection = cb
        if self._connected:
            self._callback_on_connection(self._remote_ip_address)

    def register_connection_state_callback(
        self, cb: Callable[[bool], None]
    ) -> Callable[[], None]:
        """registers a listener for connection state changes. It is called with
        True when the ISM8 connects and False when the connection is lost or the
        keepalive watchdog expires. Returns a function that removes the listener."""
        self._connection_state_callbacks.append(cb)

        def _remove() -> None:
            if cb in self._connection_state_callbacks:
                self._connection_state_callbacks.remove(cb)

        return _remove

    def connected(self):
        """returns connection status"""
        return self._connected

    def data_received(self, data) -> bool:
        """Processes one chunk of data. Kept for backwards compatibility; the
        per-connection protocol buffers the TCP stream and calls process_buffer.
        Returns False if no complete ISM8 frame could be processed."""
        buffer = bytearray(data)
        processed = self.process_buffer(buffer)
        if buffer:
            self.log.debug(f"incomplete frame discarded: {len(buffer)} byte")
        return processed > 0

    def process_buffer(self, buffer: bytearray) -> int:
        """Consumes all complete ISM8 frames from `buffer` (in place) and leaves an
        incomplete trailing frame for the next TCP segment. Returns the number of
        frames processed. TCP is a stream: frames may be split across segments or
        several frames may arrive in one segment."""
        frames = 0
        while True:
            ptr = buffer.find(ISM_HEADER)
            if ptr == -1:
                # keep a possible partial header at the end, drop the rest
                if len(buffer) > len(ISM_HEADER):
                    self.log.debug(f"discarding {len(buffer)} byte w/o ISM8-header")
                    del buffer[: len(buffer) - (len(ISM_HEADER) - 1)]
                return frames
            if ptr > 0:
                self.log.debug(f"discarding {ptr} byte before ISM8-header")
                del buffer[:ptr]
            # frame size is encoded at offset +4 (2 bytes)
            if len(buffer) < 6:
                return frames
            frame_size = 256 * buffer[4] + buffer[5]
            if frame_size < 14:
                # implausible frame size: skip this header and resync
                self.log.warning(f"invalid ISM8 frame size {frame_size}, resyncing")
                del buffer[: len(ISM_HEADER)]
                continue
            if len(buffer) < frame_size:
                # wait for the rest of the frame
                return frames
            frame = bytes(buffer[:frame_size])
            del buffer[:frame_size]
            self._process_frame(frame)
            frames += 1

    def _process_frame(self, frame: bytes) -> None:
        """Processes one complete frame and sends the ACK to the ISM8."""
        # process ObjectServer message (see docs), starts at ISM-header+10
        msg = frame[10:]
        try:
            ok = self.process_object_server_msg(msg)
        except Exception:  # pylint: disable=broad-except
            self.log.exception(f"error processing ISM8 frame {frame.hex(':')}")
            ok = False
        if ok:
            # send ACK to ISM8 according to API: ISM Header,
            # then msg-length(17), then ACK w/ 2 bytes from original msg
            ack_msg = bytearray(ISM_ACK_DP_MSG)
            ack_msg[12] = frame[12]
            ack_msg[13] = frame[13]
            if self._transport:
                self._transport.write(ack_msg)
        else:
            self.log.info("Message faulty, maybe resend by ISM8. No ACK.")

    def process_object_server_msg(self, msg: bytes):
        """
        Processes received datagram(s) according to ISM8 API specification.
        Split into dp_id, message length and encoded values for further processing
        """
        if len(msg) < 6:
            self.log.info(f"ISM8 message too short: {bytes(msg).hex(':')}")
            return False
        # number of datapoints in message are coded into bytes 4 and 5
        number_of_datapoints = msg[4] * 256 + msg[5]
        # data_ptr keeps track of the bytes
        data_ptr = 0
        counter = 1
        while counter <= number_of_datapoints:
            if len(msg) < data_ptr + 10 or len(msg) < data_ptr + 10 + msg[data_ptr + 9]:
                self.log.info("ISM8 message truncated, datapoint exceeds frame")
                return False
            dp_id = msg[data_ptr + 6] * 256 + msg[data_ptr + 7]
            dp_command = msg[data_ptr + 8]
            dp_length = msg[data_ptr + 9]
            # only set value if data length is greater than 0 and command byte is "read"
            if dp_length > 0 and dp_command == 0x03:
                dp_value = msg[data_ptr + 10 : data_ptr + 10 + dp_length]
                self.log.debug(f"{dp_id=} => {dp_value.hex(':')=} =>")
                if self.decode_datapoint(dp_id, dp_value):
                    self.log.debug(f"decoded to {self._dp_values[dp_id]}")
                else:
                    self.log.info("no data decoded from msg")
            else:
                self.log.debug("data discarded due to zero data length")
                return False
            # now advance counters, go on to next datapoint in message (if any)
            counter += 1
            data_ptr = data_ptr + 4 + dp_length
        return True

    def decode_datapoint(self, dp_id: int, raw_bytes: bytes) -> bool | None:
        """
        receives raw bytes, decodes them according to ISM8-API data type
        into int/str/float values and stores them in dictionary
        """
        if dp_id in DATAPOINTS:
            dp_type = DATAPOINTS[dp_id][IX_TYPE]
        else:
            self.log.debug(f"unknown datapoint: {dp_id}, data:{raw_bytes.hex(':')}")
            return

        if dp_type not in _DECODERS:
            self.log.debug(f"datatype {dp_type} not implemented, fallback to INT.")
        decoder = _DECODERS.get(dp_type, decode_int)

        value = decoder(int.from_bytes(raw_bytes, byteorder="big"))
        value = postprocess_data(self, dp_id, dp_type, value)

        if value is None:
            return False

        self._dp_values[dp_id] = value
        callback = self._callback_on_data.get(dp_id)
        if callback is not None:
            # a failing subscriber must not abort the frame (-> no ACK -> reconnect)
            try:
                callback()
            except Exception:  # pylint: disable=broad-except
                self.log.exception(f"callback for datapoint {dp_id} failed")
        return True

    def send_dp_value(self, dp_id: int, value) -> bool:
        """
        sends values for a (writable) datapoint in ISM8. Before message is sent,
        several checks are performed. Return true if successful, false otherwise.
        """
        # return early if value is out of range
        if not validate_dp_range(dp_id, value):
            self.log.error(f"data validation failed for {value}. May be out of range.")
            return False
        if not self._connected or self._transport is None:
            self.log.error("No Connection to ISM8 Module")
            return False
        # now encode the value according to ISM8 spec, depending on data-type
        # if encoding fails, None is returned an no data is sent
        encoded_value = self.encode_datapoint(dp_id, value)
        if encoded_value is None:
            self.log.error(f"Encoding failed for datapoint {dp_id} with value {value}")
            return False

        # prepare dataframe & send
        update_msg = self.build_message(dp_id, encoded_value)
        self.log.debug(f"sending datapoint number {dp_id} as {encoded_value}")
        self._transport.write(update_msg)
        # after sending update internal cache
        self._dp_values[dp_id] = value
        self.log.debug(f"updated cache with {value}")
        return True

    def build_message(self, dp_id: int, encoded_value: bytearray) -> bytearray:
        """builds a message for ISM8 for one datapoint, according to ISM8 specs"""
        update_msg = bytearray()
        update_msg.extend(ISM_HEADER)
        update_msg.extend(b"\x00\x00")
        update_msg.extend(ISM_CONN_HEAD)
        update_msg.extend(ISM_SERVICE_TRANSMIT)
        update_msg.extend(dp_id.to_bytes(2, byteorder="big"))
        update_msg.extend(b"\x00\x01")

        update_msg.extend(dp_id.to_bytes(2, byteorder="big"))
        update_msg.extend(b"\x00")
        update_msg.extend((len(encoded_value)).to_bytes(1, byteorder="big"))
        update_msg.extend(encoded_value)
        frame_size = len(update_msg).to_bytes(2, byteorder="big")
        update_msg[4] = frame_size[0]
        update_msg[5] = frame_size[1]
        return update_msg

    def encode_datapoint(self, dp_id: int, value) -> bytearray | None:
        """encodes a Value to ISM8 bytecode according to specs"""
        # safety check if DP exists, get type
        if dp_id in DATAPOINTS:
            dp_type = DATAPOINTS[dp_id][IX_TYPE]
        else:
            self.log.info(f"unknown datapoint: {dp_id}, data: {value}")
            return None

        encoder = _ENCODERS.get(dp_type)
        if encoder:
            return encoder(value)

        self.log.error(f"writing datatype not implemented: {dp_type}")
        return None

    def read_sensor(self, dp_id: int):
        """
        Returns sensor value from private dictionary of sensor-readings
        """
        return self._dp_values.get(dp_id, None)


class _Ism8Connection(asyncio.Protocol):
    """Protocol object for exactly one TCP connection from the ISM8.

    Holds the transport and a receive buffer for this connection and forwards
    everything else to the shared Ism8 instance.
    """

    MAX_BUFFER = 64 * 1024

    def __init__(self, ism8: Ism8):
        self._ism8 = ism8
        self.transport = None
        self._buffer = bytearray()

    def connection_made(self, transport) -> None:
        self.transport = transport
        self._ism8._on_connection_made(self, transport)

    def data_received(self, data) -> None:
        if self._ism8._active_connection is not self:
            # data from a connection that was already replaced
            return
        self._ism8.log.debug(f"data received from ISM: {data.hex(':')}")
        self._ism8._restart_watchdog()
        self._buffer.extend(data)
        if len(self._buffer) > self.MAX_BUFFER:
            self._ism8.log.warning("ISM8 receive buffer overflow, discarding data")
            self._buffer.clear()
            return
        self._ism8.process_buffer(self._buffer)

    def connection_lost(self, exc) -> None:
        self._buffer.clear()
        self._ism8._on_connection_lost(self, exc)
        self.transport = None
