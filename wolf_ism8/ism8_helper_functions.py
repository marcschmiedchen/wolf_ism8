import logging
from .ism8_constants import (
    DATAPOINTS,
    DATATYPES,
    DP_VALUES_ALLOWED,
    DT_PYTHONTYPE,
    IX_RW_FLAG,
    IX_TYPE,
    DHWModes,
)

log = logging.getLogger(__name__)


def decode_dict(mode_number: int, mode_dic: dict) -> str:
    """returns a human readable string from the API-encoded mode_number"""
    if mode_number in mode_dic.keys():
        return mode_dic[mode_number]
    else:
        log.error(f"mode number {mode_number} not implemented:")
        return ""


def encode_dict(mode: str, mode_dic: dict) -> bytearray:
    """encodes a string into corresponding ISM-Mode numbers"""
    entry_list = [item[0] for item in mode_dic.items() if item[1] == mode]
    if not entry_list:
        log.error(f"error encoding {mode}")
        log.error(f"available modes: {mode_dic.items()}")
        return None
    if len(entry_list) == 1:
        # the bytearray-constructor NEEDS a list with one entry!
        # do not cast the mode-number on its own
        return bytearray(entry_list)
    else:
        log.error(f"error encoding mode {mode}, matching not exact ")
        return None


def decode_Scaling(input: int) -> float:
    return 100 / 255 * input


def encode_Scaling(input: float) -> bytearray:
    return bytearray([round(input / (100 / 255))])


def decode_Bool(input: int) -> bool:
    # take 1st bit and cast to Bool
    return bool(input & 0b1)


def encode_Bool(input: int) -> bytearray:
    return bytearray(b"\x01") if bool(input) is True else bytearray(b"\x00")


def decode_Int(input: int) -> int:
    return int(input)


def decode_Float(input: int) -> float:
    _sign = (input & 0b1000000000000000) >> 15
    _exponent = (input & 0b0111100000000000) >> 11
    _mantisse = input & 0b0000011111111111
    if _mantisse == 0b0000011111111111:
        # according to WOLF specs, a mantisse with all bits set
        # indicates invalid data
        return None
    if _sign == 1:
        _mantisse = -(~(_mantisse - 1) & 0x07FF)
    decoded_float = float(0.01 * (2**_exponent) * _mantisse)
    return decoded_float


def encode_Float(input: float) -> bytearray:
    input = round(input, 2)
    data = [0, 0]
    encoded_float = bytearray()
    _exponent = 0
    _mantisse_calc = round(abs(input) * 100)
    while _mantisse_calc.bit_length() > 11:
        _exponent += 1
        _mantisse_calc = round(_mantisse_calc / 2)
    _mantisse = round(input * 100 / (1 << _exponent))
    if input < 0:
        data[0] |= 0x80
        _mantisse = round((~(_mantisse * -1) + 1) & 0x07FF)
    data[0] |= (_exponent & 0x0F) << 3
    data[0] |= (_mantisse >> 8) & 0x7
    data[1] |= _mantisse & 0xFF
    for byte in data:
        encoded_float.append(byte)
    # log.debug(f"encoded {input} -> {encoded_float.hex(':')}")
    return encoded_float


def validate_dp_range(dp_id: int, value) -> bool:
    """
    checks if value is valid for the datapoint before sending to ISM
    """

    # check if dp is R/O
    if not DATAPOINTS[dp_id][IX_RW_FLAG]:
        log.error(f"datapoint {dp_id} is not writable")
        return False

    # check if datatype is as expected
    dp_type = DATAPOINTS[dp_id][IX_TYPE]
    python_datatype = DATATYPES[dp_type][DT_PYTHONTYPE]
    if not isinstance(value, python_datatype):
        log.error(
            f"value for {dp_id} should be {python_datatype}, but is {type(value)},"
        )
        return False

    # check if value is in allowed range
    if isinstance(value, str):
        if dp_type == "DPT_HVACMode":
            if value not in DP_VALUES_ALLOWED[dp_id]:
                log.error(f"value {value} is out of range")
                return False
        elif dp_type == "DPT_DHWMode":
            if value not in DHWModes.values():
                log.error(f"value {value} is out of range")
                return False
    else:
        if (value > max(DP_VALUES_ALLOWED[dp_id])) or (
            value < min(DP_VALUES_ALLOWED[dp_id])
        ):
            log.error(f"value {value} is out of range")
            return False
    return True
