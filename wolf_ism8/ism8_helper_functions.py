import logging
from .ism8_constants import *

log = logging.getLogger(__name__)


def decode_HVACMode(input: int) -> int:
    return input


def encode_HVACMode(input: int) -> bytearray:
    return bytearray([input])


def decode_DHWMode(input: int) -> int:
    return input


def encode_DHWMode(input: int) -> bytearray:
    return bytearray([input])


def decode_Scaling(input: int) -> float:
    return 100 / 255 * input


def encode_Scaling(input: float) -> bytearray:
    return bytearray([round(input / (100 / 255))])


def decode_HVACContrMode(input: int) -> int:
    return input


def encode_HVACContrMode(input: int) -> bytearray:
    return bytearray([input])


def decode_Bool(input: int) -> bool:
    # take 1st bit and cast to Bool
    return bool(input & 0b1)


def encode_Bool(input: bool) -> bytearray:
    return bytearray(0b1) if input else bytearray(0b0)


def decode_Int(input: int) -> int:
    return int(input)


def decode_Float(input: int) -> float:
    _sign = (input & 0b1000000000000000) >> 15
    _exponent = (input & 0b0111100000000000) >> 11
    _mantisse = input & 0b0000011111111111
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
    log.debug("encoded %s -> %s", input, encoded_float.hex(":"))
    return encoded_float


def validate_dp_value(dp_id: int, value) -> bool:
    """
    checks if value is valid for the datapoint before sending to ISM
    """
    if dp_id not in DATAPOINTS:
        log.error("unknown datapoint: %s, value: %s", dp_id, value)
        return False
    if not DATAPOINTS[dp_id][IX_RW_FLAG]:
        log.error("datapoint %s not writable", dp_id)
        return False

    dp_type = DATAPOINTS[dp_id][IX_TYPE]
    python_datatype = DATATYPES[dp_type][DT_PYTHONTYPE]
    if not isinstance(value, python_datatype):
        log.error(
            "value for has invalid datatype %s, should be %s",
            type(value),
            python_datatype,
        )
        return False

    if (value > max(DP_VALUES_ALLOWED.get(dp_id))) or (value < min(DP_VALUES_ALLOWED.get(dp_id))):
        log.error("value %d is out of range", value)
        return False
    return True
