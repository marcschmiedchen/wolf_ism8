# pylint: disable-msg=W1203
"""
Module for gathering info and sending commands from/to Wolf HVAC System via ISM8 adapter
"""
import logging
import asyncio
from .ism8_constants import (
    DATAPOINTS,
    DATATYPES,
    IX_DEVICENAME,
    IX_NAME,
    IX_TYPE,
    IX_RW_FLAG,
    DT_UNIT,
    DP_VALUES_ALLOWED,
    ISM_HEADER,
    ISM_ACK_DP_MSG,
    ISM_CONN_HEADER,
    ISM_SERVICE_TRANSMIT,
    ISM_REQ_DP_MSG,
    HVACModes,
    HVACModes_CWL,
    HVACContrModes,
    DHWModes,
)
from .ism8_helper_functions import (
    decode_scaling,
    decode_bool,
    decode_float,
    decode_int,
    decode_dict,
    decode_date,
    decode_time_of_day,
    encode_bool,
    encode_float,
    encode_scaling,
    encode_dict,
    encode_date,
    encode_time_of_day,
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
    def is_writable(dp_id) -> bool:
        """returns writable flag from static Dictionary"""
        if dp_id in DATAPOINTS.keys():  # pylint: disable=C0201
            return DATAPOINTS[dp_id][IX_RW_FLAG]
        return False

    @staticmethod
    def get_value_range(dp_id: int):
        """returns allowed values for write operations"""
        return DP_VALUES_ALLOWED.get(dp_id, tuple())

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
            return "1.90"
        return "1.00"

    def __init__(self):
        # the datapoint-values from the device are stored and buffered here
        self._dp_values = {}
        self._transport = None
        self._remote_ip_address = None
        self._connected = False
        self.log = logging.getLogger(__name__)
        # the callbacks for all datapoints are stored in a dictionary
        self._callback_on_data = {}

    def factory(self):
        """factory method for asyncio"""
        return self

    def get_remote_ip_adress(self):
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

    def connection_lost(self, exc):
        """
        Is called when connection ends. closes socket.
        """
        self.log.debug("ISM8 closed the connection. Stopping")
        self._connected = False
        if self._transport:
            self._transport.close()

    def register_callback(self, cb, dp_nbr):
        """registers a callback for a datapoint; is called when data is received"""
        self._callback_on_data.update({dp_nbr: cb})

    def remove_callback(self, dp_nbr):
        """removes a callback for a datapoint"""
        self._callback_on_data.pop(dp_nbr)

    def connected(self):
        """returns connection status"""
        return self._connected

    def data_received(self, data) -> None:
        """is called whenever data is ready. Conducts buffering, slices the messages
        and extracts the payload for further processing. Returns false if ISM8 data
        could not be processed"""
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
            # self.log.debug(f"found header at {ptr}")
            # smallest processable data: KNX header (6 bytes) and conn. header (4bytes)
            if len(data[ptr:]) >= 10:
                # frame size is encoded at offset +4 (2bytes)
                frame_size = 256 * data[ptr + 4] + data[ptr + 5]
                # self.log.debug(f"msg length = {frame_size}")
            else:
                # self.log.error("Broken header structure. Skipping data.")
                return False

            if len(data[ptr:]) < frame_size:
                # self.log.debug(f"data length = {len(data)}")
                # self.log.error("Object server message too short. Skipping data.")
                return False

            # process next ObjectServer message (see docs), starts at ISM-header+10
            msg = data[ptr + 10 : ptr + frame_size]
            if self.process_object_server_msg(msg):
                # self.log.debug("Message successfully processed, sending ACK")
                # send ACK to ISM8 according to API: ISM Header,
                # then msg-length(17), then ACK w/ 2 bytes from original msg
                ack_msg = bytearray(ISM_ACK_DP_MSG)
                ack_msg[12] = data[ptr + 12]
                ack_msg[13] = data[ptr + 13]
                if self._transport:
                    self._transport.write(ack_msg)
            else:
                self.log.info("Message faulty, maybe resend by ISM8. No ACK.")

            # prepare to get decode message; advance Ptr to next Msg if bytes are left
            if len(data[ptr + frame_size :]) > 0:
                self.log.debug(f"more data: {len(data[ptr + frame_size :])} byte.")
                ptr = data.find(ISM_HEADER, ptr + frame_size)
            else:
                # self.log.debug("End of network buffer.")
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
            # self.log.debug(f"processing datapoint {counter} / {number_of_datapoints}")
            dp_id = msg[data_ptr + 6] * 256 + msg[data_ptr + 7]
            dp_command = msg[data_ptr + 8]
            dp_length = msg[data_ptr + 9]
            # only set value if data length is greater than 0 and command byte is "read"
            if dp_length > 0 and dp_command == 0x03:
                dp_value = msg[data_ptr + 10 : data_ptr + 10 + dp_length]
                self.log.debug(f"{dp_id=} => {dp_value.hex(':')=} =>")
                self.decode_datapoint(dp_id, dp_value)
                self.log.debug(f"decoded to {self._dp_values[dp_id]}")
            else:
                self.log.debug("data discarded due to zero data length")
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
            self.log.debug(f"unknown datapoint: {dp_id}, data:{raw_bytes.hex(':')}")
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
            self._dp_values[dp_id] = decode_bool(result)

        elif dp_type in (
            "DPT_Value_Temp",
            "DPT_Value_Tempd",
            "DPT_Tempd",
            "DPT_Value_Pres",
            "DPT_Power",
            "DPT_Value_Volume_Flow",
        ):
            temp_value = decode_float(result)
            if temp_value is None or (temp_value > 1000 and dp_type == "DPT_Power"):
                # ignore invalid data, not clear where it comes from...
                self.log.debug("discarding %s, out of range", temp_value)
                return
            else:
                self._dp_values[dp_id] = temp_value

        elif dp_type in ("DPT_ActiveEnergy", "DPT_ActiveEnergy_kWh"):
            self._dp_values[dp_id] = decode_int(result)

        elif dp_type == "DPT_FlowRate_m3/h":
            temp_value = 0.0001 * decode_int(result)
            # ignore wrong data , not clear where it comes from...
            if temp_value > 1000:
                self.log.debug("discarding %s, out of range", temp_value)
                return
            else:
                self._dp_values[dp_id] = temp_value

        elif dp_type == "DPT_Scaling":
            self._dp_values[dp_id] = decode_scaling(result)

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
            self.log.info("datatype not implemented, fallback to INT.")
            self._dp_values[dp_id] = decode_int(result)

        if self._dp_values[dp_id] is None:
            self.log.info("error decoding DP")

        if dp_id in self._callback_on_data.keys():  # pylint: disable=C0201
            self._callback_on_data[dp_id]()
        else:
            self.log.debug("no callback for dp.")
        return

    def send_dp_value(self, dp_id: int, value) -> bool:
        """
        sends values for a (writable) datapoint in ISM8. Before message is sent,
        several checks are performed. Return true if successful, false otherwise.
        """
        # return if value is out of range
        if not validate_dp_range(dp_id, value):
            self.log.error("data validation failed. data may be out of range.")
            return False
        if not self._connected or self._transport is None:
            self.log.error("No Connection to ISM8 Module")
            return False
        # now encode the value according to ISM8 spec, depending on data-type
        # if encoding fails, None is returned an no data is sent
        encoded_value = self.encode_datapoint(value, dp_id)
        if encoded_value is None:
            self.log.error(f"Encoding failed for datapoint {dp_id} with value {value}")
            return False

        # prepare dataframe
        update_msg = self.build_message(dp_id, encoded_value)
        self.log.debug(f"sending datapoint number {dp_id} as {encoded_value}")
        # send message to ISM8
        self._transport.write(update_msg)
        # after sending update internal cache
        self._dp_values[dp_id] = value
        return True

    def build_message(self, dp_id: int, encoded_value: bytearray) -> bytearray:
        """builds a message for ISM8 for one datapoint, according to ISM8 specs"""
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

    def encode_datapoint(self, value, dp_id) -> bytearray | None:
        """encodes a Value to ISM8 bytecode according to specs"""
        # safety check if DP exists, get type
        if dp_id in DATAPOINTS:
            dp_type = DATAPOINTS[dp_id][IX_TYPE]
        else:
            self.log.info(f"unknown datapoint: {dp_id}, data: {value}")
            return None

        if dp_type in (
            "DPT_Switch",
            "DPT_Bool",
            "DPT_Enable",
            "DPT_OpenClose",
        ):
            return encode_bool(value)

        elif dp_type in (
            "DPT_Value_Temp",
            "DPT_Value_Tempd",
            "DPT_Tempd",
            "DPT_Value_Pres",
            "DPT_Power",
            "DPT_Value_Volume_Flow",
        ):
            return encode_float(value)

        elif dp_type == "DPT_Scaling":
            return encode_scaling(value)

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
            self.log.error(f"writing datatype not implemented: {dp_type}")
            return None

    def read_sensor(self, dp_id: int):
        """
        Returns sensor value from private dictionary of sensor-readings
        """
        return self._dp_values.get(dp_id, None)
