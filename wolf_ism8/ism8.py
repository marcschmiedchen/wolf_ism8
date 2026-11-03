# pylint: disable-msg=W1203
"""
Module for gathering info and sending commands from/to Wolf HVAC System via ISM8 adapter
"""

import asyncio
import logging

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


class _RejectConnection(asyncio.Protocol):
    """Closes a connection that arrives while the ISM8 socket is in use."""

    def connection_made(self, transport) -> None:
        transport.close()


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
        """returns the components a BM-2 bitfield datapoint reports as present."""
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

    def __init__(self, watchdog_timeout: float = 90):
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
        # called when the connection is lost (either by ISM8 or by the watchdog)
        self._callback_on_disconnect = None
        # no loop is touched here: the protocol may be instantiated outside a
        # running loop (e.g. at module level in tests)
        self._watchdog_timeout = watchdog_timeout
        self._watchdog_handle = None

    def __call__(self):
        """asyncio protocol factory. The ISM8 keeps a single socket, so a second
        connection is rejected instead of overwriting the live transport."""
        if self._transport is not None:
            self.log.warning(
                "Connection while ISM8 socket is already in use: rejecting"
            )
            return _RejectConnection()
        return self

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

    def connection_lost(self, exc):
        """
        Is called when connection ends. closes socket.
        """
        self.log.debug("ISM8 closed the connection. Stopping")
        self._connected = False
        self._stop_watchdog()
        if self._transport:
            self._transport.close()
            self._transport = None
        self._notify_lost()

    def _notify_lost(self) -> None:
        """fire every datapoint callback one last time so receivers can mark the
        values as stale/unavailable now that the ISM8 is gone, then the disconnect
        callback. Every path that loses a connection must come through here."""
        for cb in self._callback_on_data.values():
            cb()
        if self._callback_on_disconnect is not None:
            self._callback_on_disconnect()

    def _restart_watchdog(self) -> None:
        """
        (re)arms the inactivity watchdog. Called whenever data is received or a
        connection is established.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # no loop: data_received() was called synchronously, e.g. from a test.
            # Such a call cannot belong to a live connection, so there is nothing
            # to guard: skip instead of raising.
            return
        self._stop_watchdog()
        self._watchdog_handle = loop.call_later(
            self._watchdog_timeout, self._on_watchdog_expired
        )

    def _stop_watchdog(self) -> None:
        """cancels a pending watchdog, if any"""
        if self._watchdog_handle is not None:
            self._watchdog_handle.cancel()
            self._watchdog_handle = None

    def _on_watchdog_expired(self) -> None:
        """
        No data received for watchdog_timeout seconds => Abort the transport
        Asyncio then calls connection_lost()"""
        self._watchdog_handle = None
        self.log.info(
            "No data from ISM8 (%s) for %ss. Assuming connection lost.",
            self._remote_ip_address,
            self._watchdog_timeout,
        )
        if self._transport is not None:
            self._transport.abort()
        else:
            # transport vanished already - asyncio will not call connection_lost(),
            # so take the same teardown path here
            self._connected = False
            self._notify_lost()

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

    def register_disconnect_callback(self, cb):
        """registers a callback for a lost connection; is called on connection_lost,
        which includes a watchdog expiry (see _on_watchdog_expired)"""
        self._callback_on_disconnect = cb

    def close(self) -> None:
        """Shutdown: stop the watchdog, detach all callbacks and drop the transport.
        Call this before the asyncio server drops its clients: close_clients() makes
        asyncio call connection_lost(), which would otherwise fire into a caller that
        is already torn down."""
        self._stop_watchdog()
        self._callback_on_connection = None
        self._callback_on_disconnect = None
        self._callback_on_data.clear()
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._connected = False

    def connected(self):
        """returns connection status"""
        return self._connected

    def data_received(self, data) -> bool:
        """is called whenever data is ready. Conducts buffering, slices the messages
        and extracts the payload for further processing. Returns false if ISM8 data
        could not be processed"""
        # any byte from the ISM8 proves the socket is still alive, even an
        # unparsable chunk: feed the watchdog before doing anything else
        self._restart_watchdog()
        self.log.debug(f"data received from ISM: {data.hex(':')}")
        frame_size = 0
        # find first header location
        ptr = data.find(ISM_HEADER)
        if ptr == -1:
            self.log.error("No ISM8-signature in network message. Skipping data.")
            return False
        # loop from header to header (if there are more than 1)
        # loop ends when no header is found in the remaining data
        while ptr >= 0:
            # smallest processable data: KNX header (6 bytes) and conn. header (4bytes)
            if len(data[ptr:]) >= 10:
                # frame size is encoded at offset +4 (2bytes)
                frame_size = 256 * data[ptr + 4] + data[ptr + 5]
            else:
                return False

            if len(data[ptr:]) < frame_size:
                return False

            # process next ObjectServer message (see docs), starts at ISM-header+10
            msg = data[ptr + 10 : ptr + frame_size]
            if self.process_object_server_msg(msg):
                # send ACK to ISM8 according to API: ISM Header,
                # then msg-length(17), then ACK w/ 2 bytes from original msg
                ack_msg = bytearray(ISM_ACK_DP_MSG)
                ack_msg[12] = data[ptr + 12]
                ack_msg[13] = data[ptr + 13]
                if self._transport:
                    self._transport.write(ack_msg)
            else:
                self.log.info("Message faulty, maybe resend by ISM8. No ACK.")

            # advance ptr to next message if bytes are left
            if len(data[ptr + frame_size :]) > 0:
                self.log.debug(f"more data: {len(data[ptr + frame_size :])} byte.")
                ptr = data.find(ISM_HEADER, ptr + frame_size)
            else:
                break
        return True

    def process_object_server_msg(self, msg: bytes):
        """
        Processes received datagram(s) according to ISM8 API specification.
        Split into dp_id, message length and encoded values for further processing
        """
        # number of datapoints in message are coded into bytes 4 and 5
        number_of_datapoints = msg[4] * 256 + msg[5]
        # data_ptr keeps track of the bytes
        data_ptr = 0
        counter = 1
        while counter <= number_of_datapoints:
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
            self.log.info(f"datatype {dp_type} not implemented, fallback to INT.")
        decoder = _DECODERS.get(dp_type, decode_int)

        value = decoder(int.from_bytes(raw_bytes, byteorder="big"))
        value = postprocess_data(self, dp_id, dp_type, value)

        if value is None:
            return False

        self._dp_values[dp_id] = value
        if dp_id in self._callback_on_data:
            self._callback_on_data[dp_id]()
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
