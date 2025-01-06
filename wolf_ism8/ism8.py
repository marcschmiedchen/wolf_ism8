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
    def get_version() -> str:
        """returns library version"""
        return LIB_VERSION

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
        if dp_id in DATAPOINTS.keys():
            return DATAPOINTS[dp_id][IX_RW_FLAG]
        else:
            return False

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

    @staticmethod
    def first_fw_version(dp_id: int) -> str:
        "returns first ISM8-firmware version of datapoint implementation"
        if 191 < dp_id < 208:
            return "1.50"
        if dp_id in (209, 210, 211, 251):
            return "1.70"
        if 354 < dp_id < 362:
            return "1.70"
        if 363 < dp_id < 373:
            return "1.80"
        if 211 < dp_id < 251:
            return "1.80"
        return "1.00"

    def __init__(self):
        # the datapoint-values from the device are stored and buffered here
        self._dp_values = {}
        self._transport = None
        self._remote_ip_address = None
        self._connected = False
        # the callbacks for all datapoints are stored in a dictionary
        self._callback_on_data = {}
        return

    def factory(self):
        return self

    def get_remote_ip_adress(self):
        return self._remote_ip_address

    def request_all_datapoints(self) -> None:
        """send 'request all datapoints' to ISM8"""
        req_msg = bytearray(ISM_REQ_DP_MSG)
        Ism8.log.debug("Sending REQ_ALL_DP: %s ", req_msg.hex(":"))
        if self._transport:
            self._transport.write(req_msg)  # type: ignore

    def connection_made(self, transport) -> None:
        """is called as soon as an ISM8 connects to server"""
        self._transport = transport
        self._connected = True
        self._remote_ip_address = transport.get_extra_info("peername")[0]
        Ism8.log.info("Connection from ISM8: %s", self._remote_ip_address)

    def connection_lost(self, exc):
        """
        Is called when connection ends. closes socket.
        """
        Ism8.log.debug("ISM8 closed the connection. Stopping")
        self._connected = False
        if self._transport:
            self._transport.close()

    def register_callback(self, cb, dp_nbr):
        self._callback_on_data.update({dp_nbr: cb})

    def remove_callback(self, dp_nbr):
        self._callback_on_data.pop(dp_nbr)

    def connected(self):
        return self._connected

    def data_received(self, data) -> None:
        """is called whenever data is ready. Conducts buffering, slices the messages
        and extracts the payload for further processing. Returns false if ISM8 data
        could not be processed"""
        frame_size = 0
        # find first header location
        ptr = data.find(ISM_HEADER)
        if ptr == -1:
            Ism8.log.error("No ISM8-signature in network message. Skipping data.")
            return False
        # loop from header to header (if there are more than 1)
        # loop ends when no header is found in the remaining data
        while ptr >= 0:
            Ism8.log.debug(f"found header at {ptr}")
            # smallest processable data: KNX header (6 bytes) and conn. header (4bytes)
            if len(data[ptr:]) >= 10:
                # frame size is encoded at offset +4 (2bytes)
                frame_size = 256 * data[ptr + 4] + data[ptr + 5]
                Ism8.log.debug(f"msg length = {frame_size}")
            else:
                Ism8.log.error("Broken header structure. Skipping data.")
                return False

            if len(data[ptr:]) < frame_size:
                Ism8.log.debug(f"data length = {len(data)}")
                Ism8.log.error("Object server message too short. Skipping data.")
                return False

            # process next ObjectServer message (see docs), starts at ISM-header+10
            msg = data[ptr + 10 : ptr + frame_size]
            if self.process_object_server_msg(msg):
                Ism8.log.debug("Message successfully processed, sending ACK")
                # send ACK to ISM8 according to API: ISM Header,
                # then msg-length(17), then ACK w/ 2 bytes from original msg
                ack_msg = bytearray(ISM_ACK_DP_MSG)
                ack_msg[12] = data[ptr + 12]
                ack_msg[13] = data[ptr + 13]
                if self._transport:
                    self._transport.write(ack_msg)
            else:
                Ism8.log.info("Message faulty, maybe resend by ISM8. No ACK.")

            # prepare to get decode message; advance Ptr to next Msg if bytes are left
            ptr = ptr + frame_size
            if len(data[ptr:]) > 0:
                Ism8.log.info("more data in buffer. Try to extract next datagram.")
                ptr = data.find(ISM_HEADER)
            else:
                Ism8.log.info("End of network buffer.")
                break
        return True

    def process_object_server_msg(self, msg: bytes):
        """
        Processes received datagram(s) according to ISM8 API specification.
        Split into dp_id, message length and encoded values for further processing
        """
        Ism8.log.debug(f"ObjectServer message received: {msg.hex(':')}")
        # number of datapoints in message are coded into bytes 4 and 5
        number_of_datapoints = msg[4] * 256 + msg[5]
        # data_ptr keeps track of the bytes
        data_ptr = 0
        counter = 1
        while counter <= number_of_datapoints:
            Ism8.log.debug(f"processing datapoint {counter} / {number_of_datapoints}")
            dp_id = msg[data_ptr + 6] * 256 + msg[data_ptr + 7]
            dp_length = msg[data_ptr + 9]
            if dp_length > 0:
                dp_value = msg[data_ptr + 10 : data_ptr + 10 + dp_length]
                Ism8.log.debug(f"DP {dp_id}, raw value: {dp_value.hex(':')}")
                self.decode_datapoint(dp_id, dp_value)
            else:
                Ism8.log.info(f"DP {dp_id} discarded due to zero data")
                return False
            # now advance counters, go on to next datapoint in message (if any)
            counter += 1
            data_ptr = data_ptr + 4 + dp_length
        return True

    def decode_datapoint(self, dp_id: int, raw_bytes: bytes) -> None:
        """
        receives raw bytes, decodes them according to ISM8-API data type
        into int/str/float values and stores them in dictionary
        """
        if dp_id in DATAPOINTS:
            dp_type = DATAPOINTS[dp_id][IX_TYPE]
        else:
            Ism8.log.info(f"unknown datapoint: {dp_id}, data:{raw_bytes.hex(':')}")
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
            temp_value = decode_Float(result)
            if temp_value is None or (temp_value > 1000 and dp_type == "DPT_Power"):
                # ignore invalid data, not clear where it comes from...
                Ism8.log.debug("discarding %s, out of range", temp_value)
                return
            else:
                self._dp_values[dp_id] = temp_value

        elif dp_type in ("DPT_ActiveEnergy", "DPT_ActiveEnergy_kWh"):
            self._dp_values[dp_id] = decode_Int(result)

        elif dp_type == "DPT_FlowRate_m3/h":
            temp_value = 0.0001 * decode_Int(result)
            # ignore wrong data , not clear where it comes from...
            if temp_value > 1000:
                Ism8.log.debug("discarding %s, out of range", temp_value)
                return
            else:
                self._dp_values[dp_id] = temp_value

        elif dp_type == "DPT_Scaling":
            self._dp_values[dp_id] = decode_Scaling(result)

        elif dp_type == "DPT_HVACMode":
            self._dp_values[dp_id] = decode_dict(result, HVACModes)

        elif dp_type == "DPT_HVACMode_CWL":
            self._dp_values[dp_id] = decode_dict(result, HVACModes_CWL)

        elif dp_type == "DPT_DHWMode":
            self._dp_values[dp_id] = decode_dict(result, DHWModes)

        elif dp_type == "DPT_HVACContrMode":
            self._dp_values[dp_id] = decode_dict(result, HVACContrModes)

        elif dp_type == "DPT_Date":
            self._dp_values[dp_id] = decode_date(result)

        elif dp_type == "DPT_TimeOfDay":
            self._dp_values[dp_id] = decode_time_of_day(result)

        else:
            Ism8.log.info(f"datatype <{dp_type}> not implemented, fallback to INT.")
            self._dp_values[dp_id] = decode_Int(result)

        if self._dp_values[dp_id] is not None:
            Ism8.log.debug(f"decoded {result} to {self._dp_values[dp_id]}")
        else:
            Ism8.log.error(f"error dp {dp_id}, msg: {raw_bytes}, type {dp_type}")

        if dp_id in self._callback_on_data.keys():
            Ism8.log.debug(f"calling callback for dp_id {dp_id}.")
            self._callback_on_data[dp_id]()
        else:
            Ism8.log.debug(f"no callback for dp_id {dp_id}.")
        return

    def send_dp_value(self, dp_id: int, value) -> None:
        """
        sends values for a (writable) datapoint in ISM8. Before message is sent,
        several checks are performed
        """
        # return if value is out of range
        if not validate_dp_range(dp_id, value):
            Ism8.log.error("data validation failed. data may be out of range.")
            return False

        if not self._connected or self._transport is None:
            Ism8.log.error("No Connection to ISM8 Module")
            return False
        # now encode the value according to ISM8 spec, depending on data-type
        # if encoding fails, None is returned an no data is sent
        encoded_value = self.encode_datapoint(value, dp_id)

        if encoded_value is not None:
            # prepare frame with obj info
            update_msg = self.build_message(dp_id, encoded_value)
            Ism8.log.debug(f"sending datapoint number {dp_id} as {encoded_value}")
            Ism8.log.debug(f"update msg = {update_msg}")
            # now send message to ISM8
            self._transport.write(update_msg)  # type: ignore
            # after sending update internal cache
            Ism8.log.debug(f"updating cache for {dp_id} with {value}")
            self._dp_values[dp_id] = value
        return True

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
            return None

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

        elif dp_type == "DPT_HVACMode":
            return encode_dict(value, HVACModes)

        elif dp_type == "DPT_HVACMode_CWL":
            return encode_dict(value, HVACModes_CWL)

        elif dp_type == "DPT_HVACContrMode":
            return encode_dict(value, HVACContrModes)

        elif dp_type == "DPT_DHWMode":
            return encode_dict(value, DHWModes)

        elif dp_type == "DPT_Date":
            return encode_date(value)

        elif dp_type == "DPT_TimeOfDay":
            return encode_time_of_day(value)

        else:
            Ism8.log.info(f"writing datatype not implemented: {dp_type}")
            return None

    def read_sensor(self, dp_id: int):
        """
        Returns sensor value from private dictionary of sensor-readings
        """
        return self._dp_values.get(dp_id, None)
