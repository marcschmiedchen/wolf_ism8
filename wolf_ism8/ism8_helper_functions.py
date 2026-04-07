# pylint: disable-msg=W1203
"""contains encode/decode helper functions for ISM8 datapoints"""
import datetime
import logging

from .ism8_constants import (
    DATAPOINTS,
    DATATYPES,
    DP_VALUES_ALLOWED,
    DT_PYTHONTYPE,
    IX_RW_FLAG,
    IX_TYPE,
    DHWModes,
    HVACContrModes,
    HVACModes,
    HVACModes_CWL,
)

log = logging.getLogger(__name__)

MAX_DISCARDS = 2
JUMP_FILTER_DELTA = 20
_JUMP_FILTER_TYPES = frozenset(("DPT_Value_Temp", "DPT_Value_Tempd", "DPT_Tempd"))


def decode_dict(mode_number: int, mode_dic: dict) -> str | None:
    """returns a human readable string from the API-encoded mode_number"""
    res = mode_dic.get(mode_number)
    if res is None:
        log.warning(f"mode number {mode_number} not implemented:")
    return res


def encode_dict(mode: str, mode_dic: dict) -> bytearray | None:
    """encodes a string into corresponding ISM-Mode numbers"""
    entry_list = [item[0] for item in mode_dic.items() if item[1] == mode]
    if not entry_list:
        log.error(f"error encoding {mode}")
        return None
    if len(entry_list) == 1:
        # the bytearray-constructor NEEDS a list with one entry!
        # do not cast the mode-number on its own
        return bytearray(entry_list)
    else:
        log.error(f"error encoding mode {mode}, matching not exact ")
        return None


def decode_scaling(value: int) -> float:
    """decodes a scaled value from 0-255 to 0-100"""
    return 100 / 255 * value


def encode_scaling(value: float) -> bytearray:
    """encodes a value from 0-100 to 0-255"""
    return bytearray([round(value / (100 / 255))])


def decode_bool(value: int) -> bool:
    """decodes a boolean value for int data"""
    return bool(value & 0b1)


def encode_bool(value: int) -> bytearray:
    """encodes a boolean value from int data"""
    return bytearray(b"\x01") if value else bytearray(b"\x00")


def decode_int(value: int) -> int:
    """decodes an integer value"""
    return int(value)


def decode_float(value: int) -> float | None:
    """decodes a float value"""
    _sign = (value & 0b1000000000000000) >> 15
    _exponent = (value & 0b0111100000000000) >> 11
    _mantisse = value & 0b0000011111111111
    if _mantisse == 0b0000011111111111:
        # according to WOLF specs, a mantisse with all bits set
        # indicates invalid data
        return None
    if _sign == 1:
        _mantisse = -(~(_mantisse - 1) & 0x07FF)
    decoded_float = float(0.01 * (2**_exponent) * _mantisse)
    return decoded_float


def encode_float(value: float) -> bytearray:
    """encodes a float value to ISM8 format"""
    value = round(value, 2)
    data = [0, 0]
    encoded_float = bytearray()
    _exponent = 0
    _mantisse_calc = round(abs(value) * 100)
    while _mantisse_calc.bit_length() > 11:
        _exponent += 1
        _mantisse_calc = round(_mantisse_calc / 2)
    _mantisse = round(value * 100 / (1 << _exponent))
    if value < 0:
        data[0] |= 0x80
        _mantisse = round((~(_mantisse * -1) + 1) & 0x07FF)
    data[0] |= (_exponent & 0x0F) << 3
    data[0] |= (_mantisse >> 8) & 0x7
    data[1] |= _mantisse & 0xFF
    for byte in data:
        encoded_float.append(byte)
    return encoded_float


def decode_date(value: int) -> datetime.date:
    """decodes a date value"""
    year = value & 0b000000000000000001111111
    month = (value & 0b000000000000111100000000) >> 8
    day = (value & 0b000111110000000000000000) >> 16
    return datetime.date(year + 2000, month, day)


def encode_date(value: datetime.date) -> bytearray:
    """encodes a date value"""
    encoded_date = bytearray()
    encoded_date.append(value.day)
    encoded_date.append(value.month)
    encoded_date.append(value.year - 2000)
    log.debug(f"encoded {value} -> {encoded_date.hex(':')}")
    return encoded_date


def decode_time_of_day(value: int) -> datetime.time:
    """decodes a time value"""
    seconds = value & 0b000000000000000000111111
    minutes = (value & 0b000000000011111100000000) >> 8
    hours = (value & 0b000111110000000000000000) >> 16
    return datetime.time(hour=hours, minute=minutes, second=seconds)


def encode_time_of_day(value: datetime.time) -> bytearray:
    """encodes a time value"""
    encoded_time = bytearray()
    encoded_time.append(value.hour)
    encoded_time.append(value.minute)
    encoded_time.append(value.second)
    log.debug(f"encoded {value} -> {encoded_time.hex(':')}")
    return encoded_time


_ENCODERS = {
    "DPT_Switch": encode_bool,
    "DPT_Bool": encode_bool,
    "DPT_Enable": encode_bool,
    "DPT_OpenClose": encode_bool,
    "DPT_Scaling": encode_scaling,
    "DPT_Value_Temp": encode_float,
    "DPT_Value_Tempd": encode_float,
    "DPT_Tempd": encode_float,
    "DPT_Value_Pres": encode_float,
    "DPT_Power": encode_float,
    "DPT_Value_Volume_Flow": encode_float,
    "DPT_HVACMode": lambda v: encode_dict(v, HVACModes),
    "DPT_HVACMode_CWL": lambda v: encode_dict(v, HVACModes_CWL),
    "DPT_HVACContrMode": lambda v: encode_dict(v, HVACContrModes),
    "DPT_DHWMode": lambda v: encode_dict(v, DHWModes),
    "DPT_Date": encode_date,
    "DPT_TimeOfDay": encode_time_of_day,
}

_DECODERS = {
    "DPT_Switch": decode_bool,
    "DPT_Bool": decode_bool,
    "DPT_Enable": decode_bool,
    "DPT_OpenClose": decode_bool,
    "DPT_Scaling": decode_scaling,
    "DPT_Value_Temp": decode_float,
    "DPT_Value_Tempd": decode_float,
    "DPT_Tempd": decode_float,
    "DPT_Value_Pres": decode_float,
    "DPT_Power": decode_float,
    "DPT_Value_Volume_Flow": decode_float,
    "DPT_ActiveEnergy": decode_int,
    "DPT_ActiveEnergy_kWh": decode_int,
    "DPT_FlowRate_m3/h": decode_int,
    "DPT_HVACMode": lambda v: decode_dict(v, HVACModes),
    "DPT_HVACMode_CWL": lambda v: decode_dict(v, HVACModes_CWL),
    "DPT_HVACContrMode": lambda v: decode_dict(v, HVACContrModes),
    "DPT_DHWMode": lambda v: decode_dict(v, DHWModes),
    "DPT_Date": decode_date,
    "DPT_TimeOfDay": decode_time_of_day,
}


def validate_dp_range(dp_id: int, value) -> bool:
    """checks if value is valid for the datapoint before sending to ISM"""
    if dp_id not in DATAPOINTS:
        log.error(f"datapoint {dp_id} is unknown")
        return False
    # check if dp is R/O
    if not DATAPOINTS[dp_id][IX_RW_FLAG]:
        log.error(f"datapoint {dp_id} is not writable")
        return False

    # check if datatype is as expected
    dp_type = DATAPOINTS[dp_id][IX_TYPE]
    python_datatype = DATATYPES[dp_type][DT_PYTHONTYPE]
    if not isinstance(value, python_datatype):
        log.error(f"DP {dp_id} should be {python_datatype}, but is {type(value)}")
        return False

    # check if value is in allowed range
    if isinstance(value, str):
        if value not in DP_VALUES_ALLOWED[dp_id]:
            log.error(f"value {value} is out of range")
            return False
    else:
        if (value > max(DP_VALUES_ALLOWED[dp_id])) or (
            value < min(DP_VALUES_ALLOWED[dp_id])
        ):
            log.error(f"value {value} is out of range")
            return False
    return True


def postprocess_data(self, dp_id, dp_type, value):
    """
    post-processing for complex problems
    """
    # sometimes there are unreasonably high power values -> drop them.
    if dp_type == "DPT_Power" and value > 1000:
        self.log.debug("discarding %s, out of range", value)
        return None

    # jump filter: discard temperature values that jump more than JUMP_FILTER_DELTA.
    # after MAX_DISCARDS consecutive discards, accept unconditionally (cache reset).
    cached = self._dp_values.get(dp_id)
    if dp_type in _JUMP_FILTER_TYPES and cached is not None:
        if abs(value - cached) > JUMP_FILTER_DELTA:
            count = self._dp_discard_count.get(dp_id, 0) + 1
            if count <= MAX_DISCARDS:
                self._dp_discard_count[dp_id] = count
                self.log.debug(
                    "jump filter: discarding %s -> %s for dp %d (%d/%d)",
                    cached, value, dp_id, count, MAX_DISCARDS,
                )
                return None
        self._dp_discard_count.pop(dp_id, None)

    # sometimes there are unreasonably high Flow Rates -> drop them.
    if dp_type == "DPT_FlowRate_m3/h":
        if value > 10000000:
            self.log.debug("discarding %s, out of range", value)
            return None
        # sometimes there are unreasonably LOW Flow Rates. Was reported as an issue
        # starting with FW 1.9. Seems the scaling factor is "1" in this case
        # so values between 0.1ccm/h and 1000ccm/h are assumed to be unscaled.
        # Bigger values get scaled down the official way(times 0.0001)
        if value > 1000:
            return value * 0.0001

    return value
