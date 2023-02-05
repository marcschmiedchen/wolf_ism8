"""
Module for gathering info from Wolf Heating System via ISM8 adapter
"""

import datetime
import logging
import asyncio
from time import time
from typing import Any, Optional

_LOGGER = logging.getLogger(__name__)


class Ism8(asyncio.Protocol):
    """
    This protocol class is invoked to listen to message from ISM8 module and
    feed data into internal data array
    """

    ISM_HEADER = b"\x06\x20\xf0\x80"
    ISM_CONN_HEADER = b"\x04\x00\x00\x00"
    ISM_SERVICE_RECEIVE = b"\xF0\x06"
    ISM_SERVICE_ACK = b"\xF0\x86"
    ISM_SERVICE_TRANSMIT = b"\xF0\xC1"
    ISM_SERVICE_READ_ALL = b"\xF0\xD0"
    ISM_ACK_DP_OBJ = b"\x00\x00" + b"\x00\x00" + b"\x00"
    ISM_ACK_DP_MSG = (
        ISM_HEADER + b"\x00\x11" + ISM_CONN_HEADER + ISM_SERVICE_ACK + ISM_ACK_DP_OBJ
    )
    ISM_REQ_DP_MSG = ISM_HEADER + b"\x00\x16" + ISM_CONN_HEADER + ISM_SERVICE_READ_ALL
    # constant byte arrays for creating ISM8 network messages
    # Msg: ISM_HEADER || bytearray(LENGTH_MSG) || ISM_CONN_HEADER || ISM_SERVICE_XX ||

    DEVICES = {
        "HG1": "Heizgerät (1) TOB, CGB-2, MGK-2, COB-2 oder TGB-2",
        "HG2": "Heizgerät (2) TOB, CGB-2, MGK-2, COB-2 oder TGB-2",
        "HG3": "Heizgerät (3) TOB, CGB-2, MGK-2, COB-2 oder TGB-2",
        "HG4": "Heizgerät (4) TOB, CGB-2, MGK-2, COB-2 oder TGB-2",
        "SYM": "Systembedienmodul",
        "DKW": "Direkter Heizkreis + direktes Warmwasser",
        "MK1": "Mischerkreis 1 + Warmwasser 1",
        "MK2": "Mischerkreis 2 + Warmwasser 2",
        "MK3": "Mischerkreis 3 + Warmwasser 3",
        "KM": "Kaskadenmodul",
        "MM1": "Mischermodule 1",
        "MM2": "Mischermodule 2",
        "MM3": "Mischermodule 3",
        "SM": "Solarmodul",
        "CWL": "CWL Excellent / CWL 2",
        "BWL": "Heizgerät (1) BWL-1S oder CHA",
        "BM2": "BM-2 Bedienmodul",
    }

    DP_DEVICE = 0
    # index of Wolf ISM main device name
    DP_NAME = 1
    # index of datapoint name
    DP_TYPE = 2
    # index of datapoint type (as described in Wolf API)
    DP_RW = 3
    # index of R/W-flag (writing not implemented so far)
    DP_UNIT = 4
    # index of unit description, if applicable
    DP_VALUE_AREA = 5
    # index of datapoint value area according to ism8 api, if applicable

    DATAPOINTS = {
        1: ("HG1", "Stoerung", "DPT_Switch", False, "", None),
        2: ("HG1", "Betriebsart", "DPT_HVACContrMode", False, "", None),
        3: ("HG1", "Brennerleistung", "DPT_Scaling", False, "%", None),
        4: ("HG1", "Kesseltemperatur", "DPT_Value_Temp", False, "C", None),
        5: ("HG1", "Sammlertemperatur", "DPT_Value_Temp", False, "C", None),
        6: ("HG1", "Ruecklauftemperatur", "DPT_Value_Temp", False, "C", None),
        7: ("HG1", "Warmwassertemperatur", "DPT_Value_Temp", False, "C", None),
        8: ("HG1", "Aussentemperatur", "DPT_Value_Temp", False, "C", None),
        9: ("HG1", "Status Brenner", "DPT_Switch", False, "", None),
        10: ("HG1", "Status Heizkreispumpe", "DPT_Switch", False, "", None),
        11: ("HG1", "Status Speicherladepumpe", "DPT_Switch", False, "", None),
        12: ("HG1", "Status 3W-Umschaltventil", "DPT_OpenClose", False, "", None),
        13: ("HG1", "Anlagendruck", "DPT_Value_Pres", False, "Pa", None),
        14: ("HG2", "Stoerung", "DPT_Switch", False, "", None),
        15: ("HG2", "Betriebsart", "DPT_HVACContrMode", False, "", None),
        16: ("HG2", "Brennerleistung", "DPT_Scaling", False, "%", None),
        17: ("HG2", "Kesseltemperatur", "DPT_Value_Temp", False, "C", None),
        18: ("HG2", "Sammlertemperatur", "DPT_Value_Temp", False, "C", None),
        19: ("HG2", "Ruecklauftemperatur", "DPT_Value_Temp", False, "C", None),
        20: ("HG2", "Warmwassertemperatur", "DPT_Value_Temp", False, "C", None),
        21: ("HG2", "Aussentemperatur", "DPT_Value_Temp", False, "C", None),
        22: ("HG2", "Status Brenner", "DPT_Switch", False, "", None),
        23: ("HG2", "Status Heizkreispumpe", "DPT_Switch", False, "", None),
        24: ("HG2", "Status Speicherladepumpe", "DPT_Switch", False, "", None),
        25: ("HG2", "Status 3W-Umschaltventil", "DPT_OpenClose", False, "", None),
        26: ("HG2", "Anlagendruck", "DPT_Value_Pres", False, "Pa", None),
        27: ("HG3", "Stoerung", "DPT_Switch", False, "", None),
        28: ("HG3", "Betriebsart", "DPT_HVACContrMode", False, "", None),
        29: ("HG3", "Brennerleistung", "DPT_Scaling", False, "%", None),
        30: ("HG3", "Kesseltemperatur", "DPT_Value_Temp", False, "C", None),
        31: ("HG3", "Sammlertemperatur", "DPT_Value_Temp", False, "C", None),
        32: ("HG3", "Ruecklauftemperatur", "DPT_Value_Temp", False, "C", None),
        33: ("HG3", "Warmwassertemperatur", "DPT_Value_Temp", False, "C", None),
        34: ("HG3", "Aussentemperatur", "DPT_Value_Temp", False, "C", None),
        35: ("HG3", "Status Brenner", "DPT_Switch", False, "", None),
        36: ("HG3", "Status Heizkreispumpe", "DPT_Switch", False, "", None),
        37: ("HG3", "Status Speicherladepumpe", "DPT_Switch", False, "", None),
        38: ("HG3", "Status 3W-Umschaltventil", "DPT_OpenClose", False, "", None),
        39: ("HG3", "Anlagendruck", "DPT_Value_Pres", False, "Pa", None),
        40: ("HG4", "Stoerung", "DPT_Switch", False, "", None),
        41: ("HG4", "Betriebsart", "DPT_HVACContrMode", False, "", None),
        42: ("HG4", "Brennerleistung", "DPT_Scaling", False, "%", None),
        43: ("HG4", "Kesseltemperatur", "DPT_Value_Temp", False, "C", None),
        44: ("HG4", "Sammlertemperatur", "DPT_Value_Temp", False, "C", None),
        45: ("HG4", "Ruecklauftemperatur", "DPT_Value_Temp", False, "C", None),
        46: ("HG4", "Warmwassertemperatur", "DPT_Value_Temp", False, "C", None),
        47: ("HG4", "Aussentemperatur", "DPT_Value_Temp", False, "C", None),
        48: ("HG4", "Status Brenner", "DPT_Switch", False, "", None),
        49: ("HG4", "Status Heizkreispumpe", "DPT_Switch", False, "", None),
        50: ("HG4", "Status Speicherladepumpe", "DPT_Switch", False, "", None),
        51: ("HG4", "Status 3W-Umschaltventil", "DPT_OpenClose", False, "", None),
        52: ("HG4", "Anlagendruck", "DPT_Value_Pres", False, "a", None),
        53: ("SYM", "Stoerung", "DPT_Switch", False, "", None),
        54: ("SYM", "Aussentemperatur", "DPT_Value_Temp", False, "C", None),
        55: ("DKW", "Raumtemperatur", "DPT_Value_Temp", False, "C", None),
        56: (
            "DKW",
            "Warmwassersolltemperatur",
            "DPT_Value_Temp",
            True,
            "C",
            [i for i in range(20, 81, 1)],
        ),
        57: (
            "DKW",
            "Programmwahl Heizkreis",
            "DPT_HVACMode",
            True,
            "",
            [i for i in range(0, 4, 1)],
        ),
        58: (
            "DKW",
            "Programmwahl Warmwasser",
            "DPT_DHWMode",
            True,
            "",
            [i for i in range(0, 5, 2)],
        ),
        59: ("DKW", "Heizkreis Zeitprogramm 1", "DPT_Switch", True, "", [0, 1]),
        60: ("DKW", "Heizkreis Zeitprogramm 2", "DPT_Switch", True, "", [0, 1]),
        61: ("DKW", "Heizkreis Zeitprogramm 3", "DPT_Switch", True, "", [0, 1]),
        62: ("DKW", "Warmwasser Zeitprogramm 1", "DPT_Switch", True, "", [0, 1]),
        63: ("DKW", "Warmwasser Zeitprogramm 2", "DPT_Switch", True, "", [0, 1]),
        64: ("DKW", "Warmwasser Zeitprogramm 3", "DPT_Switch", True, "", [0, 1]),
        65: (
            "DKW",
            "Sollwertkorrektur",
            "DPT_Tempd",
            True,
            "K",
            [(i / 10) for i in range(-40, 45, 5)],
        ),
        66: (
            "DKW",
            "Sparfaktor",
            "DPT_Tempd",
            True,
            "K",
            [(i / 10) for i in range(0, 105, 5)],
        ),
        67: ("MK1", "Stoerung", "DPT_Switch", False, "", None),
        68: ("MK1", "Raumtemperatur", "DPT_Value_Temp", False, "C", None),
        69: (
            "MK1",
            "Warmwassersolltemperatur",
            "DPT_Value_Temp",
            True,
            "C",
            [i for i in range(20, 81, 1)],
        ),
        70: (
            "MK1",
            "Programmwahl Mischer",
            "DPT_HVACMode",
            True,
            "",
            [i for i in range(0, 4, 1)],
        ),
        71: (
            "MK1",
            "Programmwahl Warmwasser",
            "DPT_DHWMode",
            True,
            "",
            [i for i in range(0, 5, 2)],
        ),
        72: ("MK1", "Mischer Zeitprogramm 1", "DPT_Switch", True, "", [0, 1]),
        73: ("MK1", "Mischer Zeitprogramm 2", "DPT_Switch", True, "", [0, 1]),
        74: ("MK1", "Mischer Zeitprogramm 3", "DPT_Switch", True, "", [0, 1]),
        75: ("MK1", "Warmwasser Zeitprogramm 1", "DPT_Switch", True, "", [0, 1]),
        76: ("MK1", "Warmwasser Zeitprogramm 2", "DPT_Switch", True, "", [0, 1]),
        77: ("MK1", "Warmwasser Zeitprogramm 3", "DPT_Switch", True, "", [0, 1]),
        78: (
            "MK1",
            "Sollwertkorrektur",
            "DPT_Tempd",
            True,
            "K",
            [(i / 10) for i in range(-40, 45, 5)],
        ),
        79: (
            "MK1",
            "Sparfaktor",
            "DPT_Tempd",
            True,
            "K",
            [(i / 10) for i in range(0, 105, 5)],
        ),
        80: ("MK2", "Stoerung", "DPT_Switch", False, "", None),
        82: (
            "MK2",
            "Warmwassersolltemperatur",
            "DPT_Value_Temp",
            True,
            "C",
            [i for i in range(20, 81, 1)],
        ),
        83: (
            "MK2",
            "Programmwahl Mischer",
            "DPT_HVACMode",
            True,
            "",
            [i for i in range(0, 4, 1)],
        ),
        84: (
            "MK2",
            "Programmwahl Warmwasser",
            "DPT_DHWMode",
            True,
            "",
            [i for i in range(0, 5, 2)],
        ),
        85: ("MK2", "Mischer Zeitprogramm 1", "DPT_Switch", True, "", [0, 1]),
        86: ("MK2", "Mischer Zeitprogramm 2", "DPT_Switch", True, "", [0, 1]),
        87: ("MK2", "Mischer Zeitprogramm 3", "DPT_Switch", True, "", [0, 1]),
        88: ("MK2", "Warmwasser Zeitprogramm 1", "DPT_Switch", True, "", [0, 1]),
        89: ("MK2", "Warmwasser Zeitprogramm 2", "DPT_Switch", True, "", [0, 1]),
        90: ("MK2", "Warmwasser Zeitprogramm 3", "DPT_Switch", True, "", [0, 1]),
        91: (
            "MK2",
            "Sollwertkorrektur",
            "DPT_Tempd",
            True,
            "K",
            [(i / 10) for i in range(-40, 45, 5)],
        ),
        92: (
            "MK2",
            "Sparfaktor",
            "DPT_Tempd",
            True,
            "K",
            [(i / 10) for i in range(0, 105, 5)],
        ),
        94: ("MK3", "Raumtemperatur", "DPT_Value_Temp", False, "C", None),
        95: (
            "MK3",
            "Warmwassersolltemperatur",
            "DPT_Value_Temp",
            True,
            "C",
            [i for i in range(20, 81, 1)],
        ),
        96: (
            "MK3",
            "Programmwahl Mischer",
            "DPT_HVACMode",
            True,
            "",
            [i for i in range(0, 4, 1)],
        ),
        97: (
            "MK3",
            "Programmwahl Warmwasser",
            "DPT_DHWMode",
            True,
            "",
            [i for i in range(0, 5, 2)],
        ),
        98: ("MK3", "Mischer Zeitprogramm 1", "DPT_Switch", True, "", [0, 1]),
        99: ("MK3", "Mischer Zeitprogramm 2", "DPT_Switch", True, "", [0, 1]),
        100: ("MK3", "Mischer Zeitprogramm 3", "DPT_Switch", True, "", [0, 1]),
        101: ("MK3", "Warmwasser Zeitprogramm 1", "DPT_Switch", True, "", [0, 1]),
        102: ("MK3", "Warmwasser Zeitprogramm 2", "DPT_Switch", True, "", [0, 1]),
        103: ("MK3", "Warmwasser Zeitprogramm 3", "DPT_Switch", True, "", [0, 1]),
        104: (
            "MK3",
            "Sollwertkorrektur",
            "DPT_Tempd",
            True,
            "K",
            [(i / 10) for i in range(-40, 45, 5)],
        ),
        105: (
            "MK3",
            "Sparfaktor",
            "DPT_Tempd",
            True,
            "K",
            [(i / 10) for i in range(0, 105, 5)],
        ),
        106: ("KM", "Stoerung", "DPT_Switch", False, "", None),
        107: ("KM", "Sammlertemperatur", "DPT_Value_Temp", False, "C", None),
        108: ("KM", "Gesamtmodulationsgrad", "DPT_Scaling", False, "%", None),
        109: ("KM", "Vorlauftemperatur Mischer", "DPT_Value_Temp", False, "C", None),
        110: ("KM", "Status Mischerkreispumpe", "DPT_Switch", False, "", None),
        111: ("KM", "Status Ausgang A1", "DPT_Enable", False, "", None),
        112: ("KM", "Eingang E1", "DPT_Value_Temp", False, "C", None),
        113: ("KM", "Eingang E2", "DPT_Value_Temp", False, "C", None),
        114: ("MM1", "Stoerung", "DPT_Switch", False, "", None),
        115: ("MM1", "Warmwassertemperatur", "DPT_Value_Temp", False, "C", None),
        116: ("MM1", "Vorlauftemperatur Mischer", "DPT_Value_Temp", False, "C", None),
        117: ("MM1", "Status Mischerkreispumpe", "DPT_Switch", False, "", None),
        118: ("MM1", "Status Ausgang A1", "DPT_Enable", False, "", None),
        119: ("MM1", "Eingang E1", "DPT_Value_Temp", False, "C", None),
        120: ("MM1", "Eingang E2", "DPT_Value_Temp", False, "C", None),
        121: ("MM2", "Stoerung", "DPT_Switch", False, "", None),
        122: ("MM2", "Warmwassertemperatur", "DPT_Value_Temp", False, "C", None),
        123: ("MM2", "Vorlauftemperatur Mischer", "DPT_Value_Temp", False, "C", None),
        124: ("MM2", "Status Mischerkreispumpe", "DPT_Switch", False, "", None),
        125: ("MM2", "Status Ausgang A1", "DPT_Enable", False, "", None),
        126: ("MM2", "Eingang E1", "DPT_Value_Temp", False, "C", None),
        127: ("MM2", "Eingang E2", "DPT_Value_Temp", False, "C", None),
        128: ("MM3", "Stoerung", "DPT_Switch", False, "", None),
        129: ("MM3", "Warmwassertemperatur", "DPT_Value_Temp", False, "C", None),
        130: ("MM3", "Vorlauftemperatur Mischer", "DPT_Value_Temp", False, "C", None),
        131: ("MM3", "Status Mischerkreispumpe", "DPT_Switch", False, "", None),
        132: ("MM3", "Status Ausgang A1", "DPT_Enable", False, "", None),
        133: ("MM3", "Eingang E1", "DPT_Value_Temp", False, "C", None),
        134: ("MM3", "Eingang E2", "DPT_Value_Temp", False, "C", None),
        135: ("SM", "Stoerung", "DPT_Switch", False, "", None),
        136: ("SM", "Warmwassertemperatur Solar 1", "DPT_Value_Temp", False, "C", None),
        137: ("SM", "Temperatur Kollektor 1", "DPT_Value_Temp", False, "C", None),
        138: ("SM", "Eingang E1", "DPT_Value_Temp", False, "C", None),
        139: (
            "SM",
            "Eingang E2 (Durchfluss)",
            "DPT_Value_Volume_Flow",
            False,
            "l/h",
            None,
        ),
        140: ("SM", "Eingang E3", "DPT_Value_Temp", False, "C", None),
        141: ("SM", "Status Solarkreispumpe SKP1", "DPT_Switch", False, "", None),
        142: ("SM", "Status Ausgang A1", "DPT_Enable", False, "", None),
        143: ("SM", "Status Ausgang A2", "DPT_Enable", False, "", None),
        144: ("SM", "Status Ausgang A3", "DPT_Enable", False, "", None),
        145: ("SM", "Status Ausgang A4", "DPT_Enable", False, "", None),
        146: ("SM", "Durchfluss", "DPT_Value_Volume_Flow", False, "l/h", None),
        147: ("SM", "aktuelle Leistung", "DPT_Power", False, "kW", None),
        148: ("CWL", "Stoerung", "DPT_Switch", False, "", None),
        149: ("CWL", "Programm", "DPT_DHWMode", True, "", [0, 1, 3]),
        150: ("CWL", "Zeitprogramm 1", "DPT_Switch", True, "", [0, 1]),
        151: ("CWL", "Zeitprogramm 2", "DPT_Switch", True, "", [0, 1]),
        152: ("CWL", "Zeitprogramm 3", "DPT_Switch", True, "", [0, 1]),
        153: ("CWL", "Intensivlueftung AN_AUS", "DPT_Switch", True, "", [0, 1]),
        154: ("CWL", "Intensivlueftung Startdatum", "DPT_Date", True, "", None),
        155: ("CWL", "Intensivlueftung Enddatum", "DPT_Date", True, "", None),
        156: ("CWL", "Intensivlueftung Startzeit", "DPT_TimeOfDay", True, "", None),
        157: ("CWL", "Intensivlueftung Endzeit", "DPT_TimeOfDay", True, "", None),
        158: ("CWL", "Zeitw. Feuchteschutz AN_AUS", "DPT_Switch", True, "", [0, 1]),
        159: ("CWL", "Zeitw. Feuchteschutz Startdatum", "DPT_Date", True, "", None),
        160: ("CWL", "Zeitw. Feuchteschutz Enddatum", "DPT_Date", True, "", None),
        161: ("CWL", "Zeitw. Feuchteschutz Startzeit", "DPT_TimeOfDay", True, "", None),
        162: ("CWL", "Zeitw. Feuchteschutz Endzeit", "DPT_TimeOfDay", True, "", None),
        163: ("CWL", "Lueftungsstufe", "DPT_Scaling", False, "%", None),
        164: ("CWL", "Ablufttemperatur", "DPT_Value_Temp", False, "C", None),
        165: ("CWL", "Frischlufttemperatur", "DPT_Value_Temp", False, "C", None),
        166: ("CWL", "Durchsatz Zuluft", "DPT_FlowRate_m3/h", False, "m3/h", None),
        167: ("CWL", "Durchsatz Abluft", "DPT_FlowRate_m3/h", False, "m3/h", None),
        168: ("CWL", "Bypass Initialisierung", "DPT_Bool", False, "", None),
        169: ("CWL", "Bypass oeffnet_offen", "DPT_Bool", False, "", None),
        170: ("CWL", "Bypass schliesst_geschlossen", "DPT_Bool", False, "", None),
        171: ("CWL", "Bypass Fehler", "DPT_Bool", False, "", None),
        172: ("CWL", "Frost Status: Init_Warte", "DPT_Bool", False, "", None),
        173: ("CWL", "Frost Status: Kein Frost", "DPT_Bool", False, "", None),
        174: ("CWL", "Frost Status: Vorwaermer", "DPT_Bool", False, "", None),
        175: ("CWL", "Frost Status: Fehler", "DPT_Bool", False, "", None),
        176: ("BWL", "Stoerung", "DPT_Switch", False, "", None),
        177: ("BWL", "Betriebsart", "DPT_HVACContrMode", False, "", None),
        178: ("BWL", "Heizleistung", "DPT_Power", False, "W", None),
        179: ("BWL", "Kuehlleistung", "DPT_Power", False, "W", None),
        180: ("BWL", "Kesseltemperatur", "DPT_Value_Temp", False, "C", None),
        181: ("BWL", "Sammlertemperatur", "DPT_Value_Temp", False, "C", None),
        182: ("BWL", "Ruecklauftemperatur", "DPT_Value_Temp", False, "C", None),
        183: ("BWL", "Warmwassertemperatur", "DPT_Value_Temp", False, "C", None),
        184: ("BWL", "Aussentemperatur", "DPT_Value_Temp", False, "C", None),
        185: ("BWL", "Status Heizkreispumpe", "DPT_Switch", False, "", None),
        186: ("BWL", "Status Aux-Pumpe", "DPT_Switch", False, "", None),
        187: ("BWL", "3W-Umschaltventil HZ_WW", "DPT_OpenClose", False, "", None),
        188: ("BWL", "3W-Umschaltventil HZ_K", "DPT_OpenClose", False, "", None),
        189: ("BWL", "Status E-Heizung", "DPT_Switch", False, "", None),
        190: ("BWL", "Anlagendruck", "DPT_Value_Pres", False, "Pa", None),
        191: ("BWL", "Leistungsaufnahme", "DPT_Power", False, "W", None),
        192: ("CWL", "Filterwarnung aktiv", "DPT_Switch", False, "-", None),
        193: ("CWL", "Filterwarnung zuruecksetzen", "DPT_Switch", True, "-", [0, 1]),
        194: ("SYM", "1x Warmwasserladung (gobal)", "DPT_Switch", True, "-", [0, 1]),
        195: ("SM", "Tagesertrag", "DPT_ActiveEnergy", False, "Wh", None),
        196: ("SM", "Gesamtertrag", "DPT_ActiveEnergy_kWh", False, "kWh", None),
        197: ("HG1", "Abgastemperatur", "DPT_Value_Temp", False, "C", None),
        198: ("HG1", "Leistungsvorgabe", "DPT_Scaling", True, "%", None),
        199: ("HG1", "Kesseltemperaturvorgabe", "DPT_Value_Temp", True, "C", None),
        200: ("HG2", "Abgastemperatur", "DPT_Value_Temp", False, "C", None),
        201: ("HG2", "Leistungsvorgabe", "DPT_Scaling", True, "%", None),
        202: ("HG2", "Kesseltemperaturvorgabe", "DPT_Value_Temp", True, "C", None),
        203: ("HG3", "Abgastemperatur", "DPT_Value_Temp", False, "C", None),
        204: ("HG3", "Leistungsvorgabe", "DPT_Scaling", True, "%", None),
        205: ("HG3", "Kesseltemperaturvorgabe", "DPT_Value_Temp", True, "C", None),
        206: ("HG4", "Abgastemperatur", "DPT_Value_Temp", False, "C", None),
        207: ("HG4", "Leistungsvorgabe", "DPT_Scaling", True, "%", None),
        208: ("HG4", "Kesseltemperaturvorgabe", "DPT_Value_Temp", True, "C", None),
        209: ("KM", "Gesamtmodulationsgradvorgabe", "DPT_Scaling", True, "%", None),
        210: ("KM", "Sammlertemperaturvorgabe", "DPT_Value_Temp", True, "C", None),
        211: ("KM", "Betriebsart Heizen/Kühlen", "DPT_Switch", False, "", None),
        251: (
            "BM2",
            "Erkennung verfügbare Heiz-/ Mischerkreise",
            "DPT_Value_1_Ucount",
            False,
            "",
            None,
        ),
        346: ("CWL", "undokumentiert_346", "DPT_unknown", False, "", None),
        349: ("CWL", "undokumentiert_349", "DPT_unknown", False, "", None),
        351: ("CWL", "undokumentiert_351", "DPT_unknown", False, "", None),
        350: ("CWL", "undokumentiert_351", "DPT_unknown", False, "", None),
        352: ("CWL", "undokumentiert_352", "DPT_unknown", False, "", None),
        353: ("CWL", "undokumentiert_353", "DPT_unknown", False, "", None),
        354: ("CWL", "undokumentiert_354", "DPT_unknown", False, "", None),
        355: (
            "BM2",
            "Erkennung verfügbarer Geräte 1",
            "DPT_Value_2_Ucount",
            False,
            "",
            None,
        ),
        356: (
            "BM2",
            "Erkennung verfügbarer Geräte 2",
            "DPT_Value_2_Ucount",
            False,
            "",
            None,
        ),
        357: (
            "BM2",
            "Unterscheidung Heizgerätetyp (HG1)",
            "DPT_Value_1_Ucount",
            False,
            "",
            None,
        ),
        358: (
            "BM2",
            "Erkennung vorhandener Warmwasserkreise",
            "DPT_Value_1_Ucount",
            False,
            "",
            None,
        ),
        359: (
            "BM2",
            "Unterscheidung Heizgerätetyp (HG2)",
            "DPT_Value_1_Ucount",
            False,
            "",
            None,
        ),
        360: (
            "BM2",
            "Unterscheidung Heizgerätetyp (HG3)",
            "DPT_Value_1_Ucount",
            False,
            "",
            None,
        ),
        361: (
            "BM2",
            "Unterscheidung Heizgerätetyp (HG4)",
            "DPT_Value_1_Ucount",
            False,
            "",
            None,
        ),
        364: (
            "HG1",
            "Kesselsolltemperatur HG1 – lesen",
            "DPT_Value_Temp",
            False,
            "C",
            None,
        ),
        365: (
            "HG1",
            "Kesselsolltemperatur HG2 – lesen",
            "DPT_Value_Temp",
            False,
            "C",
            None,
        ),
        366: (
            "HG1",
            "Kesselsolltemperatur HG3 – lesen",
            "DPT_Value_Temp",
            False,
            "C",
            None,
        ),
        367: (
            "HG1",
            "Kesselsolltemperatur HG4 – lesen",
            "DPT_Value_Temp",
            False,
            "C",
            None,
        ),
        368: (
            "BM2",
            "Vorlaufsolltemperatur dir. HK – lesen",
            "DPT_Value_Temp",
            False,
            "C",
            None,
        ),
        369: (
            "BM2",
            "Mischersolltemperatur MK1 – lesen ",
            "DPT_Value_Temp",
            False,
            "C",
            None,
        ),
        370: (
            "BM2",
            "Mischersolltemperatur MK2 – lesen ",
            "DPT_Value_Temp",
            False,
            "C",
            None,
        ),
        371: (
            "BM2",
            "Mischersolltemperatur MK3 – lesen ",
            "DPT_Value_Temp",
            False,
            "C",
            None,
        ),
        372: ("SYM", "Zuletzt aktiver Störcode", "DPT_Value_1_Ucount", False, "", None),
    }

    DT_MIN = 0
    # index of min value allowed by datatype according to ism8 doc
    DT_MAX = 1
    # index of max value allowed by datatype according to ism8 doc
    DT_TYPE = 2
    # index of python datatype
    DT_STEP = 3
    # index of step value according to ism8 doc
    DT_UNIT = 4
    # index of datatype unit according to ism8 doc

    DATATYPES = {
        "DPT_Switch": (0, 1, int, 1, None),
        "DPT_Bool": (0, 1, int, 1, None),
        "DPT_Enable": (0, 1, int, 1, None),
        "DPT_OpenClose": (0, 1, int, 1, None),
        "DPT_Scaling": (0.00, 100.00, float, 100 / 255, "%"),
        "DPT_Value_Temp": (-273.00, 670760.00, float, 1 / 100, "C"),
        "DPT_Value_Tempd": (-670760.00, 670760.00, float, 1 / 100, "K"),
        "DPT_Tempd": (-670760.00, 670760.00, float, 1 / 100, "K"),
        "DPT_Value_Pres": (0, 670760.00, float, 1 / 100, "Pa"),
        "DPT_Power": (-670760.00, 670760.00, float, 1 / 100, "kW"),
        "DPT_Value_Volume_Flow": (-670760.00, 670760.00, float, 1 / 100, "l/h"),
        "DPT_TimeOfDay": (None, None, type(time), None, None),
        "DPT_Date": (None, None, datetime, None, None),
        "DPT_Value_1_Ucount": (0, 255, int, 1, None),
        "DPT_Value_2_Ucount": (0, 65535, int, 1, None),
        "DPT_FlowRate_m3/h": (-2147483647, 2147483647, int, 1 / 10000, "m3/h"),
        "DPT_HVACMode": (0, 4, int, 1, None),
        "DPT_DHWMode": (0, 4, int, 1, None),
        "DPT_HVACContrMode": (0, 20, int, 1, None),
    }

    HVACModes = {
        0: "Auto",
        1: "Comfort",
        2: "Standby",
        3: "Economy",
        4: "Building Protection",
    }

    HVACContrModes = {
        0: "Auto",
        1: "Heat",
        2: "Morning Warmup",
        3: "Cool",
        4: "Night Purge",
        5: "Precool",
        6: "Off",
        7: "Test",
        8: "Emergency Heat",
        9: "Fan Only",
        10: "Free Cool",
        11: "Ice",
        12: "Maximum Heating Mode",
        13: "Economic Heat/Cool Mode",
        14: "Dehumidification",
        15: "Calibration Mode",
        16: "Emergency Cool Mode",
        17: "Emergency Steam Mode",
        20: "NoDem",
    }

    DHWModes = {0: "Auto", 1: "LegioProtect", 2: "Normal", 3: "Reduced", 4: "Off"}

    @staticmethod
    def get_device(dp_id):
        """returns device name from private array of sensor-readings"""
        return Ism8.DATAPOINTS.get(dp_id, ["", "", "", "", ""])[Ism8.DP_DEVICE]

    @staticmethod
    def get_name(dp_id):
        """returns sensor name from private array of sensor-readings"""
        return Ism8.DATAPOINTS.get(dp_id, ["", "", "", "", ""])[Ism8.DP_NAME]

    @staticmethod
    def get_type(dp_id):
        """returns sensor type from private array of sensor-readings"""
        return Ism8.DATAPOINTS.get(dp_id, ["", "", "", "", ""])[Ism8.DP_TYPE]

    @staticmethod
    def is_writable(dp_id) -> bool:
        """returns sensor type from private array of sensor-readings"""
        return Ism8.DATAPOINTS.get(dp_id, ["", "", "", "", ""])[Ism8.DP_RW]

    @staticmethod
    def get_value_area(dp_id) -> Optional[list[Any]]:
        """returns sensor type from private array of sensor-readings"""
        return Ism8.DATAPOINTS.get(dp_id, ["", "", "", "", ""])[Ism8.DP_VALUE_AREA]

    @staticmethod
    def get_min_value(dp_id: int) -> Any:
        """returns min value allowed for datapoint"""
        datatype = Ism8.DATAPOINTS.get(dp_id, ["", "", "", "", ""])[Ism8.DP_TYPE]
        return Ism8.DATATYPES.get(datatype, ["", "", "", "", ""])[Ism8.DT_MIN]

    @staticmethod
    def get_max_value(dp_id: int) -> Any:
        """returns min value allowed for datapoint"""
        datatype = Ism8.DATAPOINTS.get(dp_id, ["", "", "", "", ""])[Ism8.DP_TYPE]
        return Ism8.DATATYPES.get(datatype, ["", "", "", "", ""])[Ism8.DT_MAX]

    @staticmethod
    def get_datatype(dp_id: int) -> Any:
        """returns python datatype allowed for datapoint"""
        datatype = Ism8.DATAPOINTS.get(dp_id, ["", "", "", "", ""])[Ism8.DP_TYPE]
        return Ism8.DATATYPES.get(datatype, ["", "", "", "", ""])[Ism8.DT_TYPE]

    @staticmethod
    def get_step_value(dp_id: int) -> Any:
        """returns step value for datapoint"""
        datatype = Ism8.DATAPOINTS.get(dp_id, ["", "", "", "", ""])[Ism8.DP_TYPE]
        return Ism8.DATATYPES.get(datatype, ["", "", "", "", ""])[Ism8.DT_STEP]

    @staticmethod
    def get_unit(dp_id: int) -> Any:
        """returns unit for datapoint"""
        datatype = Ism8.DATAPOINTS.get(dp_id, ["", "", "", "", ""])[Ism8.DP_TYPE]
        return Ism8.DATATYPES.get(datatype, ["", "", "", "", ""])[Ism8.DT_UNIT]

    @staticmethod
    def get_all_sensors():
        """returns pointer all possible values of ISM8 datapoints"""
        return Ism8.DATAPOINTS

    @staticmethod
    def decode_HVACMode(input: int) -> str:
        return Ism8.HVACModes.get(input, "unbekannter Modus")

    @staticmethod
    def encode_HVACMode(input: str) -> Optional[bytearray]:
        for key in Ism8.HVACModes:
            if Ism8.HVACModes[key].lower() == input.lower().strip():
                return bytearray([key])
        _LOGGER.error("HVAC Mode %s is not valid", input)
        return None

    @staticmethod
    def decode_Scaling(input: int) -> float:
        # take byte value and multiply by 100/255
        return 100 / 255 * input

    @staticmethod
    def encode_Scaling(input: float) -> bytearray:
        # take byte value and multiply by 100/255
        return bytearray([round(input / (100 / 255))])

    @staticmethod
    def decode_DHWMode(input: int) -> str:
        return Ism8.DHWModes.get(input, "unbekannter Modus")

    @staticmethod
    def encode_DHWMode(input: str) -> Optional[bytearray]:
        for key in Ism8.DHWModes:
            if Ism8.DHWModes[key].lower() == input.lower().strip():
                return bytearray([key])
        _LOGGER.error("DHW mode %s is not valid", input)
        return None

    @staticmethod
    def decode_HVACContrMode(input: int) -> str:
        return Ism8.HVACContrModes.get(input, "unbekannter Modus")

    @staticmethod
    def encode_HVACContrMode(input: str) -> Optional[bytearray]:
        for key in Ism8.HVACContrModes:
            if Ism8.HVACContrModes[key].lower() == input.lower().strip():
                return bytearray([key])
        _LOGGER.error("HVAC Control mode %s is not valid", input)
        return None

    @staticmethod
    def decode_Bool(input: int) -> bool:
        # take 1st bit and cast to Bool
        return bool(input & 0b1)

    @staticmethod
    def encode_Bool(input: bool) -> bytearray:
        return bytearray([int(input)])

    @staticmethod
    def decode_Int(input: int) -> int:
        return int(input)

    @staticmethod
    def decode_ScaledInt(input: int) -> float:
        return float(0.0001 * input)

    @staticmethod
    def decode_Float(input: int) -> float:
        _sign = (input & 0b1000000000000000) >> 15
        _exponent = (input & 0b0111100000000000) >> 11
        _mantisse = input & 0b0000011111111111
        if _sign == 1:
            _mantisse = -(~(_mantisse - 1) & 0x07FF)
        decoded_float = float(0.01 * (2**_exponent) * _mantisse)
        _LOGGER.debug("decoded %s -> %s", input, decoded_float)
        return decoded_float

    @staticmethod
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
        for bit in data:
            encoded_float.append(bit)
        _LOGGER.debug("encoded %s -> %s", input, encoded_float)
        return encoded_float

    def __init__(self):
        self._dp_values = {}
        # the datapoint-values (IDs matching the list above) are stored here
        self._transport = None
        self._connected = False
        self._LOGGER = _LOGGER

    def factory(self):
        """
        returns reference to itself for using in protocol_factory with
        create_server
        """
        return self

    def request_all_datapoints(self):
        """send 'request all datapoints' to ISM8"""
        req_msg = bytearray(Ism8.ISM_REQ_DP_MSG)
        self._LOGGER.debug("Sending REQ_DP: %s ", self.__encode_bytes(req_msg))
        self._transport.write(req_msg)

    def connection_made(self, transport):
        """is called as soon as an ISM8 connects to server"""
        _peername = transport.get_extra_info("peername")
        self._LOGGER.info("Connection from ISM8: %s", _peername)
        self._transport = transport
        self._connected = True

    def data_received(self, data):
        """is called whenever data is ready"""
        _header_ptr = 0
        msg_length = 0
        self._LOGGER.debug("Raw data received: %s", self.__encode_bytes(data))
        while _header_ptr < len(data):
            _header_ptr = data.find(Ism8.ISM_HEADER, _header_ptr)
            if _header_ptr >= 0:
                if len(data[_header_ptr:]) >= 9:
                    # smallest processable data:
                    # hdr plus 5 bytes=>at least 9 bytes
                    msg_length = 256 * data[_header_ptr + 4] + data[_header_ptr + 5]
                    # msg_length comes in bytes 4 and 5
                else:
                    msg_length = len(data) + 1

            # 2 possible outcomes here: Buffer is to short for message=>abort
            # buffer is larger => than msg: process 1 message,
            # then continue loop
            if len(data) < _header_ptr + msg_length:
                self._LOGGER.debug("Buffer shorter than expected / broken Message.")
                self._LOGGER.debug("Discarding: %s ", data[_header_ptr:])
                # setting Ptr to end of data will end loop
                _header_ptr = len(data)
            else:
                # send ACK to ISM8 according to API: ISM Header,
                # then msg-length(17), then ACK w/ 2 bytes from original msg
                ack_msg = bytearray(Ism8.ISM_ACK_DP_MSG)
                ack_msg[12] = data[_header_ptr + 12]
                ack_msg[13] = data[_header_ptr + 13]
                self._LOGGER.debug("Sending ACK: %s ", self.__encode_bytes(ack_msg))
                self._transport.write(ack_msg)
                # process message without header (first 10 bytes)
                self.process_msg(data[_header_ptr + 10 : _header_ptr + msg_length])

                # prepare to get next message; advance Ptr to next Msg
                _header_ptr += msg_length

    def process_msg(self, msg):
        """
        Processes received datagram(s) according to ISM8 API specification
        into message length, command, values delivered
        """
        max_dp = msg[4] * 256 + msg[5]
        # number of DATAPOINTS are coded into bytes 4 and 5 of message
        i = 0
        # byte counter
        dp_nbr = 1
        # datapoint counter
        while dp_nbr <= max_dp:
            self._LOGGER.debug("DP %d / %d in datagram:", dp_nbr, max_dp)
            dp_id = msg[i + 6] * 256 + msg[i + 7]
            # dp_command = msg[i + 8]
            # to be implemented for writing values to ISM8
            dp_length = msg[i + 9]
            dp_raw_value = bytearray(msg[i + 10 : i + 10 + dp_length])
            self._LOGGER.debug(
                "Processing DP-ID %s, %s bytes: message: %s",
                dp_id,
                dp_length,
                dp_raw_value,
            )
            self.extract_datapoint(dp_id, dp_length, dp_raw_value)
            # now advance byte counter and datapoint counter
            dp_nbr += 1
            i = i + 10 + dp_length

    def __validate_value_for_dp(self, dp_id: int, value: Any) -> bool:
        """
        validate if dp with given value
        """
        if dp_id not in Ism8.DATAPOINTS:

            self._LOGGER.error("unknown datapoint: %s, value: %s", dp_id, value)
            return False
        if not Ism8.DATAPOINTS[dp_id][Ism8.DP_RW]:

            self._LOGGER.error("datapoint %s not writable", dp_id)
            return False
        if isinstance(value, self.get_datatype(dp_id)):
            self._LOGGER.error(
                "value has invalid datatype %s, valid datatype is %s",
                type(value),
                self.get_datatype(dp_id),
            )
            return False

        if type(value) != str:
            if value < self.get_min_value(dp_id) or self.get_max_value(dp_id) < value:

                self._LOGGER.error(
                    "value %d is out of range(%d < n < %d)",
                    value,
                    self.get_min_value(dp_id),
                    self.get_max_value(dp_id),
                )
                return False
        return True

    def send_dp_value(self, dp_id: int, value: Any) -> None:
        """ """
        if not self.__validate_value_for_dp(dp_id, value):

            return

        if not self._connected or self._transport is None:

            self._LOGGER.error("No Connection to ISM8 Module")
            return
        dp_type = Ism8.DATAPOINTS[dp_id][Ism8.DP_TYPE]
        encoded_value = 0b0

        if dp_type in ("DPT_Switch", "DPT_Bool", "DPT_Enable", "DPT_OpenClose"):

            encoded_value = Ism8.encode_Bool(value)
        elif dp_type == "DPT_HVACMode":

            encoded_value = Ism8.encode_HVACMode(value)
        elif dp_type == "DPT_Scaling":

            encoded_value = Ism8.encode_Scaling(value)
        elif dp_type == "DPT_DHWMode":

            encoded_value = Ism8.encode_DHWMode(value)
        elif dp_type == "DPT_HVACContrMode":

            encoded_value = Ism8.encode_HVACContrMode(value)
        elif dp_type in (
            "DPT_Value_Temp",
            "DPT_Value_Tempd",
            "DPT_Tempd",
            "DPT_Value_Pres",
            "DPT_Power",
            "DPT_Value_Volume_Flow",
        ):

            encoded_value = Ism8.encode_Float(value)
        elif dp_type in ("DPT_ActiveEnergy", "DPT_ActiveEnergy_kWh"):

            encoded_value = Ism8.encode_Int(value)
        else:

            self._LOGGER.error("datatype unknown, using INT: %s ", dp_type)
            encoded_value = Ism8.encode_Int(value)
        self._LOGGER.debug("encoded DP %s : %s = %s\n", dp_id, value, encoded_value)

        # prepare frame with obj info
        update_msg = bytearray()
        update_msg.extend(Ism8.ISM_HEADER)
        update_msg.extend((0).to_bytes(2, byteorder="big"))
        update_msg.extend(Ism8.ISM_CONN_HEADER)
        update_msg.extend(Ism8.ISM_SERVICE_TRANSMIT)
        update_msg.extend(dp_id.to_bytes(2, byteorder="big"))
        update_msg.extend((1).to_bytes(2, byteorder="big"))
        update_msg.extend(dp_id.to_bytes(2, byteorder="big"))
        update_msg.extend((0).to_bytes(1, byteorder="big"))
        update_msg.extend((len(encoded_value)).to_bytes(1, byteorder="big"))
        update_msg.extend(encoded_value)
        frame_size = len(update_msg).to_bytes(2, byteorder="big")
        update_msg[4] = frame_size[0]
        update_msg[5] = frame_size[1]

        # send message
        self._LOGGER.debug(
            "send message dp %d from val %s to %s\n%s",
            dp_id,
            self.read(dp_id),
            value,
            self.__encode_bytes(update_msg),
        )
        self._transport.write(update_msg)

    def extract_datapoint(self, dp_id: int, length: int, raw_bytes: bytearray) -> None:
        """
        decodes a single value according to API;
        receives raw bytes from network and
        decodes them according to API data type
        """
        result = 0
        for single_byte in raw_bytes:
            result = result * 256 + int(single_byte)

        dp_type = "DPT_unknown"
        if dp_id in Ism8.DATAPOINTS:
            dp_type = Ism8.DATAPOINTS[dp_id][Ism8.DP_TYPE]
        else:
            self._LOGGER.error("unknown datapoint: %s, data:%s", dp_id, result)

        if dp_type in ("DPT_Switch", "DPT_Bool", "DPT_Enable", "DPT_OpenClose"):
            self._dp_values.update({dp_id: Ism8.decode_Bool(result)})

        elif dp_type == "DPT_HVACMode":
            self._dp_values.update({dp_id: Ism8.decode_HVACMode(result)})

        elif dp_type == "DPT_Scaling":
            self._dp_values.update({dp_id: Ism8.decode_Scaling(result)})

        elif dp_type == "DPT_DHWMode":
            self._dp_values.update({dp_id: Ism8.decode_DHWMode(result)})

        elif dp_type == "DPT_HVACContrMode":
            self._dp_values.update({dp_id: Ism8.decode_HVACContrMode(result)})

        elif dp_type in (
            "DPT_Value_Temp",
            "DPT_Value_Tempd",
            "DPT_Tempd",
            "DPT_Value_Pres",
            "DPT_Power",
            "DPT_Value_Volume_Flow",
        ):
            self._dp_values.update({dp_id: Ism8.decode_Float(result)})

        elif dp_type in ("DPT_ActiveEnergy", "DPT_ActiveEnergy_kWh"):
            self._dp_values.update({dp_id: Ism8.decode_Int(result)})

        else:
            self._LOGGER.debug("datatype unknown, using INT: %s ", dp_type)
            self._dp_values.update({dp_id: Ism8.decode_Int(result)})

        self._LOGGER.debug(
            "decoded DP %s : %s = %s\n",
            dp_id,
            Ism8.DATAPOINTS.get(dp_id, "unknown DP"),
            self._dp_values[dp_id],
        )

    def connection_lost(self, exc):
        """
        Is called when connection ends. closes socket.
        """
        self._LOGGER.debug("ISM8 closed the connection.Stopping")
        self._connected = False
        self._transport.close()

    def read(self, dp_id):
        """
        Returns sensor value from private array of sensor-readings
        """
        if dp_id in self._dp_values.keys():
            return self._dp_values[dp_id]
        else:
            return None

    def __encode_bytes(self, msg: bytes) -> str:
        """encode the byte array too make it more readable"""
        msg_hex = msg.hex()
        n = 0
        ret = ""
        while n < len(msg_hex):
            ret += msg_hex[n]
            n += 1
            if (n % 2) == 0:
                ret += " "
        return ret.strip()


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    _LOGGER = logging.getLogger(__name__)

    # for testing purposes only, relies on debug output
    myProtocol = Ism8()
    for keys, values in myProtocol.get_all_sensors().items():
        _LOGGER.debug("%s:  %s" % (keys, values))

    _eventloop = asyncio.get_event_loop()
    coro = _eventloop.create_server(myProtocol.factory, "127.0.0.1", 5000)
    _server = _eventloop.run_until_complete(coro)
    # Serve requests until Ctrl+C is pressed
    _LOGGER.debug("Waiting for ISM8 connection on %s", _server.sockets[0].getsockname())
    _eventloop.run_forever()