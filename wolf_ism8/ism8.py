"""
Module for gathering info and sending commands from/to Wolf HVAC System via ISM8 adapter
"""
import logging
import asyncio

from .ism8_constants import *
from .ism8_helper_functions import *


class Ism8(asyncio.Protocol):
    """
    This protocol class listens to messages from ISM8 module and
    feeds data into internal data dictionary. Also provides functionality for
    writing datapoints.
    """

    log = logging.getLogger(__name__)

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
        else:
            return ""

    @staticmethod
    def is_writable(dp_id) -> bool:
        """returns writable flag from static Dictionary"""
        return DATAPOINTS.get(dp_id, ["", "", "", "", ""])[IX_RW_FLAG]

    @staticmethod
    def get_value_range(dp_id: int):
        """returns allowed values for write operations"""
        return DP_VALUES_ALLOWED.get(dp_id, tuple())

    @staticmethod
    def get_library_version() -> str:
        """returns current implementation version"""
        return LIB_VERSION

    @staticmethod
    def get_all_sensors() -> dict:
        """returns dictionary (nbr -> list of properties) for all ISM8 datapoints"""
        return DATAPOINTS

    @staticmethod
    def get_all_devices():
        """returns list of all ISM8 devices. Unique first Component of DATAPOINTS"""
        return sorted(set([x[0] for x in DATAPOINTS.values()]))

    def __init__(self):
        # the datapoint-values from the device are stored and buffered here
        self._dp_values = {}
        self._transport = None
        self._connected = False
        return

    def factory(self):
        return self

    def request_all_datapoints(self) -> None:
        """send 'request all datapoints' to ISM8"""
        req_msg = bytearray(ISM_REQ_DP_MSG)
        Ism8.log.debug("Sending REQ_ALL_DP: %s ", req_msg.hex(":"))
        if self._transport:
            self._transport.write(req_msg)

    def connection_made(self, transport) -> None:
        """is called as soon as an ISM8 connects to server"""
        _peername = transport.get_extra_info("peername")
        Ism8.log.info("Connection from ISM8: %s", _peername)
        self._transport = transport
        self._connected = True

    def connection_lost(self, exc):
        """
        Is called when connection ends. closes socket.
        """
        Ism8.log.debug("ISM8 closed the connection. Stopping")
        self._connected = False
        if self._transport:
            self._transport.close()

    def data_received(self, data) -> None:
        """is called whenever data is ready. Conducts buffering, slices the messages
        and extracts the payload for further processing."""
        _header_ptr = 0
        msg_length = 0
        while _header_ptr < len(data):
            _header_ptr = data.find(ISM_HEADER, _header_ptr)
            if _header_ptr >= 0:
                if len(data[_header_ptr:]) >= 9:
                    # smallest processable data:
                    # hdr plus 5 bytes=>at least 9 bytes
                    msg_length = 256 * data[_header_ptr + 4] + data[_header_ptr + 5]
                    # msg_length comes in bytes 4 and 5
                else:
                    msg_length = len(data) + 1
            else:
                Ism8.log.debug("No ISM8-signature in network message. Skipping data.")
                break

            # 2 possible outcomes here: Buffer is to short for message=>abort
            # buffer is larger than msg => : process 1 message,
            # then continue loop
            if len(data) < _header_ptr + msg_length:
                Ism8.log.debug("Buffer shorter than expected / broken Message.")
                # Ism8.log.debug(f"Discarding: {data[_header_ptr:]}")
                # setting Ptr to end of data will end loop
                _header_ptr = len(data)
            else:
                # send ACK to ISM8 according to API: ISM Header,
                # then msg-length(17), then ACK w/ 2 bytes from original msg
                ack_msg = bytearray(ISM_ACK_DP_MSG)
                ack_msg[12] = data[_header_ptr + 12]
                ack_msg[13] = data[_header_ptr + 13]
                if self._transport:
                    self._transport.write(ack_msg)
                # process message without header (first 10 bytes)
                self.process_msg(data[_header_ptr + 10 : _header_ptr + msg_length])
                # prepare to get next message; advance Ptr to next Msg
                _header_ptr += msg_length

    def process_msg(self, msg):
        """
        Processes received datagram(s) according to ISM8 API specification.
        Split into dp_id, message length and encoded values for further processing
        """
        # number of datapoints in message are coded into bytes 4 and 5
        max_dp = msg[4] * 256 + msg[5]
        # i keeps track of the bytes
        i = 0
        # loop over datapoint counter, until all dps are processed
        dp_ctr = 1
        while dp_ctr <= max_dp:
            Ism8.log.debug("DP %d / %d in datagram:", dp_ctr, max_dp)
            dp_id = msg[i + 6] * 256 + msg[i + 7]
            dp_length = msg[i + 9]
            dp_raw_value = bytearray(msg[i + 10 : i + 10 + dp_length])
            Ism8.log.debug(
                "Processing DP-ID %d, %s, message: %s",
                dp_id, DATAPOINTS.get(dp_id, 'unknown')[IX_NAME], dp_raw_value.hex(':')
            )
            self.decode_datapoint(dp_id, dp_raw_value)
            # now advance byte counter and datapoint counter
            dp_ctr += 1
            i = i + 10 + dp_length

    def decode_datapoint(self, dp_id: int, raw_bytes: bytearray) -> None:
        """
        receives raw bytes, decodes them according to ISM8-API data type
        into int/str/float values and stores them in dictionary
        """
        if dp_id in DATAPOINTS:
            dp_type = DATAPOINTS[dp_id][IX_TYPE]
        else:
            Ism8.log.info(f"unknown datapoint: {dp_id}, data:{raw_bytes}")
            return

        result = 0
        for single_byte in raw_bytes:
            result = result * 256 + int(single_byte)

        if dp_type in (
            "DPT_Switch",
            "DPT_Bool",
            "DPT_Enable",
            "DPT_OpenClose",
        ):
            self._dp_values[dp_id] = decode_Bool(result)

        elif dp_type in (
            "DPT_Value_Temp",
            "DPT_Value_Tempd",
            "DPT_Tempd",
            "DPT_Value_Pres",
            "DPT_Power",
            "DPT_Value_Volume_Flow",
        ):
            if decode_Float(result) is not None:
                self._dp_values[dp_id] = decode_Float(result)

        elif dp_type in ("DPT_ActiveEnergy", "DPT_ActiveEnergy_kWh"):
            self._dp_values[dp_id] = decode_Int(result)

        elif dp_type == "DPT_FlowRate_m3/h":
            self._dp_values[dp_id] = 0.0001 * decode_Int(result)

        elif dp_type == "DPT_Scaling":
            self._dp_values[dp_id] = decode_Scaling(result)

        elif dp_type == "DPT_HVACMode":
            if dp_id == 149:
                self._dp_values[dp_id] = decode_dict(result, HVACModes_CWL)
            else:
                self._dp_values[dp_id] = decode_dict(result, HVACModes)

        elif dp_type == "DPT_DHWMode":
            self._dp_values[dp_id] = decode_dict(result, DHWModes)

        elif dp_type == "DPT_HVACContrMode":
            self._dp_values[dp_id] = decode_dict(result, HVACContrModes)

        else:
            Ism8.log.info(f"datatype <{dp_type}> not implemented, fallback to INT.")
            self._dp_values[dp_id] = decode_Int(result)

        Ism8.log.debug("decoded %d to %s", result, self._dp_values[dp_id])
        return

    def send_dp_value(self, dp_id: int, value) -> None:
        """
        sends values for a (writable) datapoint in ISM8. Before message is sent,
        several checks are performed
        """
        if not self._connected or self._transport is None:
            Ism8.log.error("No Connection to ISM8 Module")
            return
        # return if value is out of range
        if not validate_dp_range(dp_id, value):
            Ism8.log.error("Validation failed. data out of range.")
            return

        # now encode the value according to ISM8 spec, depending on data-type
        # if encoding fails, None is returned an no data is sent
        encoded_value = self.encode_datapoint(value, dp_id)

        if encoded_value is not None:
            # prepare frame with obj info
            update_msg = self.build_message(dp_id, encoded_value)
            Ism8.log.debug(f"sending datapoint number {dp_id} as {encoded_value}")
            # now send message to ISM8
            self._transport.write(update_msg)
            # after sending update internal cache
            Ism8.log.debug(f"updating cache for {dp_id} with {value}")
            self._dp_values[dp_id] = value
        return

    def build_message(self, dp_id: int, encoded_value: bytearray):
        update_msg = bytearray()
        update_msg.extend(ISM_HEADER)
        update_msg.extend((0).to_bytes(2, byteorder="big"))
        update_msg.extend(ISM_CONN_HEADER)
        update_msg.extend(ISM_SERVICE_TRANSMIT)
        update_msg.extend(dp_id.to_bytes(2, byteorder="big"))
        update_msg.extend((1).to_bytes(2, byteorder="big"))

        update_msg.extend(dp_id.to_bytes(2, byteorder="big"))
        update_msg.extend((0).to_bytes(1, byteorder="big"))
        update_msg.extend((len(encoded_value)).to_bytes(1, byteorder="big"))
        update_msg.extend(encoded_value)
        frame_size = len(update_msg).to_bytes(2, byteorder="big")
        update_msg[4] = frame_size[0]
        update_msg[5] = frame_size[1]
        return update_msg

    def encode_datapoint(self, value, dp_id):
        # check if DP exists
        if dp_id in DATAPOINTS:
            dp_type = DATAPOINTS[dp_id][IX_TYPE]
        else:
            Ism8.log.error(f"unknown datapoint: {dp_id}, data: {value}")
            return

        if dp_type in (
            "DPT_Switch",
            "DPT_Bool",
            "DPT_Enable",
            "DPT_OpenClose",
        ):
            return encode_Bool(value)

        elif dp_type in (
            "DPT_Value_Temp",
            "DPT_Value_Tempd",
            "DPT_Tempd",
            "DPT_Value_Pres",
            "DPT_Power",
            "DPT_Value_Volume_Flow",
        ):
            return encode_Float(value)

        elif dp_type == "DPT_Scaling":
            return encode_Scaling(value)

        # special treatment for point 149 (CWL) according to wolf specs
        elif dp_type == "DPT_HVACMode":
            if dp_id == 149:
                return encode_dict(value, HVACModes_CWL)
            else:
                return encode_dict(value, HVACModes)

        elif dp_type == "DPT_DHWMode":
            return encode_dict(value, DHWModes)

        else:
            Ism8.log.info(f"writing datatype not implemented: {dp_type}")
            return None

    def read_sensor(self, dp_id: int):
        """
        Returns sensor value from private dictionary of sensor-readings
        """
        return self._dp_values.get(dp_id, None)
