"""
Module for gathering info from Wolf Heating System via ISM8 adapter
"""

import logging
import asyncio

class Ism8(asyncio.Protocol):
    """
    This protocol class is invoked to listen to message from ISM8 module and
    feed data into internal data array
    """

    ISM_HEADER = b'\x06\x20\xf0\x80'
    ISM_CONN_HEADER = b'\x04\x00\x00\x00'
    ISM_ACK = b'\xF0\x86\x00\x00\x00\x00\x00'
    ISM_REQ_DP =b'\x06\x20\xF0\x80\x00\x16\x04\x00\x00\x00\xF0\xD0'
    ISM_POLL = b'\x06\x20\xF0\x80\x00\x16\x04\x00\x00\x00\xF0\xD0'
    # constant byte arrays for creating ISM8 network messages

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

    DATAPOINTS = {
        1: ('HG1', 'Stoerung', 'DPT_Switch', False, ''),
        2: ('HG1', 'Betriebsart', 'DPT_HVACContrMode', False, ''),
        3: ('HG1', 'Brennerleistung', 'DPT_Scaling', False, '%'),
        4: ('HG1', 'Kesseltemperatur', 'DPT_Value_Temp', False, 'C'),
        5: ('HG1', 'Sammlertemperatur', 'DPT_Value_Temp', False, 'C'),
        6: ('HG1', 'Ruecklauftemperatur', 'DPT_Value_Temp', False, 'C'),
        7: ('HG1', 'Warmwassertemperatur', 'DPT_Value_Temp', False, 'C'),
        8: ('HG1', 'Aussentemperatur', 'DPT_Value_Temp', False, 'C'),
        9: ('HG1', 'Status Brenner', 'DPT_Switch', False, ''),
        10: ('HG1', 'Status Heizkreispumpe', 'DPT_Switch', False, ''),
        11: ('HG1', 'Status Speicherladepumpe', 'DPT_Switch', False, ''),
        12: ('HG1', 'Status 3W-Umschaltventil', 'DPT_OpenClose', False, ''),
        13: ('HG1', 'Anlagendruck', 'DPT_Value_Pres', False, 'Pa'),
        14: ('HG2', 'Stoerung', 'DPT_Switch', False, ''),
        15: ('HG2', 'Betriebsart', 'DPT_HVACContrMode', False, ''),
        16: ('HG2', 'Brennerleistung', 'DPT_Scaling', False, '%'),
        17: ('HG2', 'Kesseltemperatur', 'DPT_Value_Temp', False, 'C'),
        18: ('HG2', 'Sammlertemperatur', 'DPT_Value_Temp', False, 'C'),
        19: ('HG2', 'Ruecklauftemperatur', 'DPT_Value_Temp', False, 'C'),
        20: ('HG2', 'Warmwassertemperatur', 'DPT_Value_Temp', False, 'C'),
        21: ('HG2', 'Aussentemperatur', 'DPT_Value_Temp', False, 'C'),
        22: ('HG2', 'Status Brenner', 'DPT_Switch', False, ''),
        23: ('HG2', 'Status Heizkreispumpe', 'DPT_Switch', False, ''),
        24: ('HG2', 'Status Speicherladepumpe', 'DPT_Switch', False, ''),
        25: ('HG2', 'Status 3W-Umschaltventil', 'DPT_OpenClose', False, ''),
        26: ('HG2', 'Anlagendruck', 'DPT_Value_Pres', False, 'Pa'),
        27: ('HG3', 'Stoerung', 'DPT_Switch', False, ''),
        28: ('HG3', 'Betriebsart', 'DPT_HVACContrMode', False, ''),
        29: ('HG3', 'Brennerleistung', 'DPT_Scaling', False, '%'),
        30: ('HG3', 'Kesseltemperatur', 'DPT_Value_Temp', False, 'C'),
        31: ('HG3', 'Sammlertemperatur', 'DPT_Value_Temp', False, 'C'),
        32: ('HG3', 'Ruecklauftemperatur', 'DPT_Value_Temp', False, 'C'),
        33: ('HG3', 'Warmwassertemperatur', 'DPT_Value_Temp', False, 'C'),
        34: ('HG3', 'Aussentemperatur', 'DPT_Value_Temp', False, 'C'),
        35: ('HG3', 'Status Brenner', 'DPT_Switch', False, ''),
        36: ('HG3', 'Status Heizkreispumpe', 'DPT_Switch', False, ''),
        37: ('HG3', 'Status Speicherladepumpe', 'DPT_Switch', False, ''),
        38: ('HG3', 'Status 3W-Umschaltventil', 'DPT_OpenClose', False, ''),
        39: ('HG3', 'Anlagendruck', 'DPT_Value_Pres', False, 'Pa'),
        40: ('HG4', 'Stoerung', 'DPT_Switch', False, ''),
        41: ('HG4', 'Betriebsart', 'DPT_HVACContrMode', False, ''),
        42: ('HG4', 'Brennerleistung', 'DPT_Scaling', False, '%'),
        43: ('HG4', 'Kesseltemperatur', 'DPT_Value_Temp', False, 'C'),
        44: ('HG4', 'Sammlertemperatur', 'DPT_Value_Temp', False, 'C'),
        45: ('HG4', 'Ruecklauftemperatur', 'DPT_Value_Temp', False, 'C'),
        46: ('HG4', 'Warmwassertemperatur', 'DPT_Value_Temp', False, 'C'),
        47: ('HG4', 'Aussentemperatur', 'DPT_Value_Temp', False, 'C'),
        48: ('HG4', 'Status Brenner', 'DPT_Switch', False, ''),
        49: ('HG4', 'Status Heizkreispumpe', 'DPT_Switch', False, ''),
        50: ('HG4', 'Status Speicherladepumpe', 'DPT_Switch', False, ''),
        51: ('HG4', 'Status 3W-Umschaltventil', 'DPT_OpenClose', False, ''),
        52: ('HG4', 'Anlagendruck', 'DPT_Value_Pres', False, 'a'),
        53: ('BM1', 'Stoerung', 'DPT_Switch', False, ''),
        54: ('BM1', 'Aussentemperatur', 'DPT_Value_Temp', False, 'C'),
        55: ('BM1', 'Raumtemperatur', 'DPT_Value_Temp', False, 'C'),
        56: ('BM1', 'Warmwassersolltemperatur', 'DPT_Value_Temp', True, 'C'),
        57: ('BM1', 'Programmwahl Heizkreis', 'DPT_HVACMode', True, ''),
        58: ('BM1', 'Programmwahl Warmwasser', 'DPT_DHWMode', True, ''),
        59: ('BM1', 'Heizkreis Zeitprogramm 1', 'DPT_Switch', True, ''),
        60: ('BM1', 'Heizkreis Zeitprogramm 2', 'DPT_Switch', True, ''),
        61: ('BM1', 'Heizkreis Zeitprogramm 3', 'DPT_Switch', True, ''),
        62: ('BM1', 'Warmwasser Zeitprogramm 1', 'DPT_Switch', True, ''),
        63: ('BM1', 'Warmwasser Zeitprogramm 2', 'DPT_Switch', True, ''),
        64: ('BM1', 'Warmwasser Zeitprogramm 3', 'DPT_Switch', True, ''),
        65: ('BM1', 'Sollwertkorrektur', 'DPT_Tempd', True, 'K'),
        66: ('BM1', 'Sparfaktor', 'DPT_Tempd', True, 'K'),
        67: ('BM2', 'Stoerung', 'DPT_Switch', False, ''),
        68: ('BM2', 'Raumtemperatur', 'DPT_Value_Temp', False, 'C'),
        69: ('BM2', 'Warmwassersolltemperatur', 'DPT_Value_Temp', True, 'C'),
        70: ('BM2', 'Programmwahl Mischer', 'DPT_HVACMode', True, ''),
        71: ('BM2', 'Programmwahl Warmwasser', 'DPT_DHWMode', True, ''),
        72: ('BM2', 'Mischer Zeitprogramm 1', 'DPT_Switch', True, ''),
        73: ('BM2', 'Mischer Zeitprogramm 2', 'DPT_Switch', True, ''),
        74: ('BM2', 'Mischer Zeitprogramm 3', 'DPT_Switch', True, ''),
        75: ('BM2', 'Warmwasser Zeitprogramm 1', 'DPT_Switch', True, ''),
        76: ('BM2', 'Warmwasser Zeitprogramm 2', 'DPT_Switch', True, ''),
        77: ('BM2', 'Warmwasser Zeitprogramm 3', 'DPT_Switch', True, ''),
        78: ('BM2', 'Sollwertkorrektur', 'DPT_Tempd', True, 'K'),
        79: ('BM2', 'Sparfaktor', 'DPT_Tempd', True, 'K'),
        80: ('BM3', 'Stoerung', 'DPT_Switch', False, ''),
        81: ('BM3', 'Raumtemperatur', 'DPT_Value_Temp', False, 'C'),
        82: ('BM3', 'Warmwassersolltemperatur', 'DPT_Value_Temp', True, 'C'),
        83: ('BM3', 'Programmwahl Mischer', 'DPT_HVACMode', True, ''),
        84: ('BM3', 'Programmwahl Warmwasser', 'DPT_DHWMode', True, ''),
        85: ('BM3', 'Mischer Zeitprogramm 1', 'DPT_Switch', True, ''),
        86: ('BM3', 'Mischer Zeitprogramm 2', 'DPT_Switch', True, ''),
        87: ('BM3', 'Mischer Zeitprogramm 3', 'DPT_Switch', True, ''),
        88: ('BM3', 'Warmwasser Zeitprogramm 1', 'DPT_Switch', True, ''),
        89: ('BM3', 'Warmwasser Zeitprogramm 2', 'DPT_Switch', True, ''),
        90: ('BM3', 'Warmwasser Zeitprogramm 3', 'DPT_Switch', True, ''),
        91: ('BM3', 'Sollwertkorrektur', 'DPT_Tempd', True, 'K'),
        92: ('BM3', 'Sparfaktor', 'DPT_Tempd', True, 'K'),
        93: ('BM4', 'Stoerung', 'DPT_Switch', False, ''),
        94: ('BM4', 'Raumtemperatur', 'DPT_Value_Temp', False, 'C'),
        95: ('BM4', 'Warmwassersolltemperatur', 'DPT_Value_Temp', True, 'C'),
        96: ('BM4', 'Programmwahl Mischer', 'DPT_HVACMode', True, ''),
        97: ('BM4', 'Programmwahl Warmwasser', 'DPT_DHWMode', True, ''),
        98: ('BM4', 'Mischer Zeitprogramm 1', 'DPT_Switch', True, ''),
        99: ('BM4', 'Mischer Zeitprogramm 2', 'DPT_Switch', True, ''),
        100: ('BM4', 'Mischer Zeitprogramm 3', 'DPT_Switch', True, ''),
        101: ('BM4', 'Warmwasser Zeitprogramm 1', 'DPT_Switch', True, ''),
        102: ('BM4', 'Warmwasser Zeitprogramm 2', 'DPT_Switch', True, ''),
        103: ('BM4', 'Warmwasser Zeitprogramm 3', 'DPT_Switch', True, ''),
        104: ('BM4', 'Sollwertkorrektur', 'DPT_Tempd', True, 'K'),
        105: ('BM4', 'Sparfaktor', 'DPT_Tempd', True, 'K'),
        106: ('KM', 'Stoerung', 'DPT_Switch', False, ''),
        107: ('KM', 'Sammlertemperatur', 'DPT_Value_Temp', False, 'C'),
        108: ('KM', 'Gesamtmodulationsgrad', 'DPT_Scaling', False, '%'),
        109: ('KM', 'Vorlauftemperatur Mischer', 'DPT_Value_Temp', False, 'C'),
        110: ('KM', 'Status Mischerkreispumpe', 'DPT_Switch', False, ''),
        111: ('KM', 'Status Ausgang A1', 'DPT_Enable', False, ''),
        112: ('KM', 'Eingang E1', 'DPT_Value_Temp', False, 'C'),
        113: ('KM', 'Eingang E2', 'DPT_Value_Temp', False, 'C'),
        114: ('MM1', 'Stoerung', 'DPT_Switch', False, ''),
        115: ('MM1', 'Warmwassertemperatur', 'DPT_Value_Temp', False, 'C'),
        116: (
            'MM1', 'Vorlauftemperatur Mischer', 'DPT_Value_Temp', False, 'C'),
        117: ('MM1', 'Status Mischerkreispumpe', 'DPT_Switch', False, ''),
        118: ('MM1', 'Status Ausgang A1', 'DPT_Enable', False, ''),
        119: ('MM1', 'Eingang E1', 'DPT_Value_Temp', False, 'C'),
        120: ('MM1', 'Eingang E2', 'DPT_Value_Temp', False, 'C'),
        121: ('MM2', 'Stoerung', 'DPT_Switch', False, ''),
        122: ('MM2', 'Warmwassertemperatur', 'DPT_Value_Temp', False, 'C'),
        123: (
            'MM2', 'Vorlauftemperatur Mischer', 'DPT_Value_Temp', False, 'C'),
        124: ('MM2', 'Status Mischerkreispumpe', 'DPT_Switch', False, ''),
        125: ('MM2', 'Status Ausgang A1', 'DPT_Enable', False, ''),
        126: ('MM2', 'Eingang E1', 'DPT_Value_Temp', False, 'C'),
        127: ('MM2', 'Eingang E2', 'DPT_Value_Temp', False, 'C'),
        128: ('MM3', 'Stoerung', 'DPT_Switch', False, ''),
        129: ('MM3', 'Warmwassertemperatur', 'DPT_Value_Temp', False, 'C'),
        130: (
            'MM3', 'Vorlauftemperatur Mischer', 'DPT_Value_Temp', False, 'C'),
        131: ('MM3', 'Status Mischerkreispumpe', 'DPT_Switch', False, ''),
        132: ('MM3', 'Status Ausgang A1', 'DPT_Enable', False, ''),
        133: ('MM3', 'Eingang E1', 'DPT_Value_Temp', False, 'C'),
        134: ('MM3', 'Eingang E2', 'DPT_Value_Temp', False, 'C'),
        135: ('SM', 'Stoerung', 'DPT_Switch', False, ''),
        136: ('SM', 'Warmwassertemperatur Solar 1', 'DPT_Value_Temp', False,
              'C'),
        137: ('SM', 'Temperatur Kollektor 1', 'DPT_Value_Temp', False, 'C'),
        138: ('SM', 'Eingang E1', 'DPT_Value_Temp', False, 'C'),
        139: ('SM', 'Eingang E2 (Durchfluss)', 'DPT_Value_Volume_Flow', False,
              'l/h'),
        140: ('SM', 'Eingang E3', 'DPT_Value_Temp', False, 'C'),
        141: ('SM', 'Status Solarkreispumpe SKP1', 'DPT_Switch', False, ''),
        142: ('SM', 'Status Ausgang A1', 'DPT_Enable', False, ''),
        143: ('SM', 'Status Ausgang A2', 'DPT_Enable', False, ''),
        144: ('SM', 'Status Ausgang A3', 'DPT_Enable', False, ''),
        145: ('SM', 'Status Ausgang A4', 'DPT_Enable', False, ''),
        146: ('SM', 'Durchfluss', 'DPT_Value_Volume_Flow', False, 'l/h'),
        147: ('SM', 'aktuelle Leistung', 'DPT_Power', False, 'kW'),
        148: ('CWL', 'Stoerung', 'DPT_Switch', False, ''),
        149: ('CWL', 'Programm', 'DPT_DHWMode', True, ''),
        150: ('CWL', 'Zeitprogramm 1', 'DPT_Switch', True, ''),
        151: ('CWL', 'Zeitprogramm 2', 'DPT_Switch', True, ''),
        152: ('CWL', 'Zeitprogramm 3', 'DPT_Switch', True, ''),
        153: ('CWL', 'Intensivlueftung AN_AUS', 'DPT_Switch', True, ''),
        154: ('CWL', 'Intensivlueftung Startdatum', 'DPT_Date', True, ''),
        155: ('CWL', 'Intensivlueftung Enddatum', 'DPT_Date', True, ''),
        156: ('CWL', 'Intensivlueftung Startzeit', 'DPT_TimeOfDay', True, ''),
        157: ('CWL', 'Intensivlueftung Endzeit', 'DPT_TimeOfDay', True, ''),
        158: ('CWL', 'Zeitw. Feuchteschutz AN_AUS', 'DPT_Switch', True, ''),
        159: ('CWL', 'Zeitw. Feuchteschutz Startdatum', 'DPT_Date', True, ''),
        160: ('CWL', 'Zeitw. Feuchteschutz Enddatum', 'DPT_Date', True, ''),
        161: (
            'CWL', 'Zeitw. Feuchteschutz Startzeit', 'DPT_TimeOfDay', True,
            ''),
        162: (
            'CWL', 'Zeitw. Feuchteschutz Endzeit', 'DPT_TimeOfDay', True, ''),
        163: ('CWL', 'Lueftungsstufe', 'DPT_Scaling', False, '%'),
        164: ('CWL', 'Ablufttemperatur', 'DPT_Value_Temp', False, 'C'),
        165: ('CWL', 'Frischlufttemperatur', 'DPT_Value_Temp', False, 'C'),
        166: ('CWL', 'Durchsatz Zuluft', 'DPT_FlowRate_m3/h', False, 'm3/h'),
        167: ('CWL', 'Durchsatz Abluft', 'DPT_FlowRate_m3/h', False, 'm3/h'),
        168: ('CWL', 'Bypass Initialisierung', 'DPT_Bool', False, ''),
        169: ('CWL', 'Bypass oeffnet_offen', 'DPT_Bool', False, ''),
        170: ('CWL', 'Bypass schliesst_geschlossen', 'DPT_Bool', False, ''),
        171: ('CWL', 'Bypass Fehler', 'DPT_Bool', False, ''),
        172: ('CWL', 'Frost Status: Init_Warte', 'DPT_Bool', False, ''),
        173: ('CWL', 'Frost Status: Kein Frost', 'DPT_Bool', False, ''),
        174: ('CWL', 'Frost Status: Vorwaermer', 'DPT_Bool', False, ''),
        175: ('CWL', 'Frost Status: Fehler', 'DPT_Bool', False, ''),
        176: ('BWL', 'Stoerung', 'DPT_Switch', False, ''),
        177: ('BWL', 'Betriebsart', 'DPT_HVACContrMode', False, ''),
        178: ('BWL', 'Heizleistung', 'DPT_Power', False, 'W'),
        179: ('BWL', 'Kuehlleistung', 'DPT_Power', False, 'W'),
        180: ('BWL', 'Kesseltemperatur', 'DPT_Value_Temp', False, 'C'),
        181: ('BWL', 'Sammlertemperatur', 'DPT_Value_Temp', False, 'C'),
        182: ('BWL', 'Ruecklauftemperatur', 'DPT_Value_Temp', False, 'C'),
        183: ('BWL', 'Warmwassertemperatur', 'DPT_Value_Temp', False, 'C'),
        184: ('BWL', 'Aussentemperatur', 'DPT_Value_Temp', False, 'C'),
        185: ('BWL', 'Status Heizkreispumpe', 'DPT_Switch', False, ''),
        186: ('BWL', 'Status Aux-Pumpe', 'DPT_Switch', False, ''),
        187: ('BWL', '3W-Umschaltventil HZ_WW', 'DPT_OpenClose', False, ''),
        188: ('BWL', '3W-Umschaltventil HZ_K', 'DPT_OpenClose', False, ''),
        189: ('BWL', 'Status E-Heizung', 'DPT_Switch', False, ''),
        190: ('BWL', 'Anlagendruck', 'DPT_Value_Pres', False, 'Pa'),
        191: ('BWL', 'Leistungsaufnahme', 'DPT_Power', False, 'W'),
        192: ('CWL', 'Filterwarnung aktiv', 'DPT_Switch', False, '-'),
        193: ('CWL', 'Filterwarnung zuruecksetzen', 'DPT_Switch', True, '-'),
        194: ('BM1', '1x Warmwasserladung (gobal)', 'DPT_Switch', True, '-'),
        195: ('SM', 'Tagesertrag', 'DPT_ActiveEnergy', False, 'Wh'),
        196: ('SM', 'Gesamtertrag', 'DPT_ActiveEnergy_kWh', False, 'kWh'),
        197: ('HG1', 'Abgastemperatur', 'DPT_Value_Temp', False, 'C'),
        198: ('HG1', 'Leistungsvorgabe', 'DPT_Scaling', True, '%'),
        199: ('HG1', 'Kesseltemperaturvorgabe', 'DPT_Value_Temp', True, 'C'),
        200: ('HG2', 'Abgastemperatur', 'DPT_Value_Temp', False, 'C'),
        201: ('HG2', 'Leistungsvorgabe', 'DPT_Scaling', True, '%'),
        202: ('HG2', 'Kesseltemperaturvorgabe', 'DPT_Value_Temp', True, 'C'),
        203: ('HG3', 'Abgastemperatur', 'DPT_Value_Temp', False, 'C'),
        204: ('HG3', 'Leistungsvorgabe', 'DPT_Scaling', True, '%'),
        205: ('HG3', 'Kesseltemperaturvorgabe', 'DPT_Value_Temp', True, 'C'),
        206: ('HG4', 'Abgastemperatur', 'DPT_Value_Temp', False, 'C'),
        207: ('HG4', 'Leistungsvorgabe', 'DPT_Scaling', True, '%'),
        208: ('HG4', 'Kesseltemperaturvorgabe', 'DPT_Value_Temp', True, 'C'),
        209: ('KM', 'Gesamtmodulationsgradvorgabe', 'DPT_Scaling', True, '%'),
        210: ('KM', 'Sammlertemperaturvorgabe', 'DPT_Value_Temp', True, 'C'),
        354: ('CWL', 'undokumentiert_354', 'DPT_unknown', False, ''),
        355: ('CWL', 'undokumentiert_355', 'DPT_unknown', False, ''),
        356: ('CWL', 'undokumentiert_356', 'DPT_unknown', False, ''),
        357: ('CWL', 'undokumentiert_357', 'DPT_unknown', False, ''),
        358: ('CWL', 'undokumentiert_358', 'DPT_unknown', False, ''),
    }

    HVACModes = {
        0: 'Auto',
        1: 'Comfort',
        2: 'Standby',
        3: 'Economy',
        4: 'Building Protection'
    }
    
    HVACContrModes = {
        0: 'Auto',
        1: 'Heat',
        2: 'Morning Warmup',
        3: 'Cool',
        4: 'Night Purge',
        5: 'Precool',
        6: 'Off',
        7: 'Test',
        8: 'Emergency Heat',
        9: 'Fan Only',
        10:'Free Cool',
        11:'Ice',
        12:'Maximum Heating Mode',
        13:'Economic Heat/Cool Mode',
        14:'Dehumidification',
        15:'Calibration Mode',
        16:'Emergency Cool Mode',
        17:'Emergency Steam Mode',
        20:'NoDem'
    }

    DHWModes = {
        0: 'Auto',
        1: 'LegioProtect',
        2: 'Normal',
        3: 'Reduced',
        4: 'Off'
    }

    @staticmethod
    def get_device(dp_id):
        """ returns device name from private array of sensor-readings """
        return Ism8.DATAPOINTS.get(dp_id, ['','','','',''])[Ism8.DP_DEVICE]

    @staticmethod
    def get_name(dp_id):
        """ returns sensor name from private array of sensor-readings """
        return Ism8.DATAPOINTS.get(dp_id, ['','','','',''])[Ism8.DP_NAME]

    @staticmethod
    def get_type(dp_id):
        """ returns sensor type from private array of sensor-readings """
        return Ism8.DATAPOINTS.get(dp_id, ['','','','',''])[Ism8.DP_TYPE]

    @staticmethod
    def get_unit(dp_id):
        """ returns sensor unit from private array of sensor-readings """
        return Ism8.DATAPOINTS.get(dp_id, ['','','','',''])[Ism8.DP_UNIT]

    @staticmethod
    def get_all_sensors():
        """ returns pointer all possible values of ISM8 datapoints """
        return Ism8.DATAPOINTS

    @staticmethod
    def decode_HVACMode(input):
       return Ism8.HVACModes.get(input, 'unbekannter Modus')

    @staticmethod
    def decode_Scaling(input):
        # take byte value and multiply by 100/255
        return (100 / 255 * input)

    @staticmethod
    def decode_DHWMode(input):
        return Ism8.DHWModes.get(input, 'unbekannter Modus')
    
    @staticmethod
    def decode_HVACContrMode(input):
        return Ism8.HVACContrModes.get(input, 'unbekannter Modus')

    @staticmethod
    def decode_Bool(input):
        # take 1st bit and cast to Bool
        return bool(input & 1)
        
    @staticmethod
    def decode_Int(input):
        return int(input)

    @staticmethod
    def decode_ScaledInt(input):
        return float(0.0001*input)

    @staticmethod
    def decode_Float(input):
        _sign = (input & 0b1000000000000000) >> 15
        _exponent = (input & 0b0111100000000000) >> 11
        _mantisse = input & 0b0000011111111111
        if _sign == 1:
            _mantisse = -(~(_mantisse - 1) & 0x07ff)
        return float(0.01 * (2 ** _exponent) * _mantisse)

    def __init__(self):
        self._dp_values = {}
        # the datapoint-values (IDs matching the list above) are stored here
        self._transport = None
        self._connected = False
        self._LOGGER = logging.getLogger(__name__)

    def factory(self):
        """
        returns reference to itself for using in protocol_factory with
        create_server
        """
        return self

    def request_all_datapoints(self):
        """send 'request all datapoints' to ISM8 """
        req_msg = bytearray(Ism8.ISM_REQ_DP)
        self._LOGGER.debug('Sending REQ_DP: %s ', req_msg)
        self._transport.write(req_msg)

    def connection_made(self, transport):
        """ is called as soon as an ISM8 connects to server """
        _peername = transport.get_extra_info('peername')
        self._LOGGER.info("Connection from ISM8: %s", _peername)
        self._transport = transport
        self._connected = True
        self.request_all_datapoints()

    def data_received(self, data):
        """ is called whenever data is ready """
        _header_ptr = 0
        msg_length = 0
        self._LOGGER.debug('Raw data received: %s', data)
        while _header_ptr < len(data):
            _header_ptr = data.find(Ism8.ISM_HEADER, _header_ptr)
            if _header_ptr >= 0:
                if len(data[_header_ptr:]) >= 9:
                    # smallest processable data:
                    # hdr plus 5 bytes=>at least 9 bytes
                    msg_length = 256 * data[_header_ptr + 4] + data[
                        _header_ptr + 5]
                    # msg_length comes in bytes 4 and 5
                else:
                    msg_length = len(data) + 1

            # 2 possible outcomes here: Buffer is to short for message=>abort
            # buffer is larger => than msg: process 1 message,
            # then continue loop
            if len(data) < _header_ptr + msg_length:
                self._LOGGER.debug(
                    "Buffer shorter than expected / broken Message.")
                self._LOGGER.debug("Discarding: %s ", data[_header_ptr:])
                # setting Ptr to end of data will end loop
                _header_ptr = len(data)
            else:
                # send ACK to ISM8 according to API: ISM Header,
                # then msg-length(17), then ACK w/ 2 bytes from original msg
                ack_msg = bytearray(Ism8.ISM_HEADER)
                ack_msg.append(0x00)
                ack_msg.append(0x11)
                ack_msg.extend(Ism8.ISM_CONN_HEADER)
                ack_msg.extend(Ism8.ISM_ACK)
                ack_msg[12] = data[_header_ptr + 12]
                ack_msg[13] = data[_header_ptr + 13]
                self._LOGGER.debug('Sending ACK: %s ', ack_msg)
                self._transport.write(ack_msg)
                self.process_msg(
                    data[_header_ptr + 10:_header_ptr + msg_length])
                # process message without header (first 10 bytes)

                _header_ptr += msg_length
                # prepare to get next message; advance Ptr to next Msg

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
            self._LOGGER.debug('DP {0:d} / {1:d} in datagram:'.format(
                dp_nbr, max_dp))
            dp_id = msg[i + 6] * 256 + msg[i + 7]
            # dp_command = msg[i + 8]
            # to be implemented for writing values to ISM8
            dp_length = msg[i + 9]
            dp_raw_value = bytearray(msg[i + 10:i + 10 + dp_length])
            self._LOGGER.debug('Processing DP-ID %s, %s bytes: message: %s',
                               dp_id, dp_length, dp_raw_value)
            self.extract_datapoint(dp_id, dp_length, dp_raw_value)
            # now advance byte counter and datapoint counter
            dp_nbr += 1
            i = i + 10 + dp_length

    def extract_datapoint(self, dp_id, length, raw_bytes):
        """
        decodes a single value according to API;
        receives raw bytes from network and
        decodes them according to API data type
        """
        result = 0
        for single_byte in raw_bytes:
            result = result * 256 + int(single_byte)

        dp_type = 'DPT_unknown'
        if dp_id in Ism8.DATAPOINTS:
            dp_type = Ism8.DATAPOINTS[dp_id][Ism8.DP_TYPE]
        else:
            self._LOGGER.error("unknown datapoint: %s, data:%s",
                               dp_id, result)
            
        if dp_type in ("DPT_Switch", "DPT_Bool", "DPT_Enable", "DPT_OpenClose"):
            self._dp_values.update({dp_id: Ism8.decode_Bool(result)})

        elif (dp_type == "DPT_HVACMode"):
            self._dp_values.update({dp_id: Ism8.decode_HVACMode(result)})

        elif (dp_type == "DPT_Scaling"):
            self._dp_values.update({dp_id: Ism8.decode_Scaling(result)})

        elif (dp_type == "DPT_DHWMode"):
            self._dp_values.update({dp_id: Ism8.decode_DHWMode(result)})

        elif (dp_type == "DPT_HVACContrMode"):
            self._dp_values.update({dp_id: Ism8.decode_HVACContrMode(result)})

        elif (dp_type in ("DPT_Value_Temp",
                          "DPT_Value_Tempd",
                          "DPT_Tempd",
                          "DPT_Value_Pres",
                          "DPT_Power",
                          "DPT_Value_Volume_Flow"
                          )):
            self._dp_values.update({dp_id: Ism8.decode_Float(result)})
            
        elif (dp_type in ("DPT_ActiveEnergy", "DPT_ActiveEnergy_kWh" )):
            self._dp_values.update({dp_id: Ism8.decode_Int(result)})
            
        elif (dp_type == "DPT_FlowRate_m3/h"):
            self._dp_values.update({dp_id: Ism8.decode_ScaledInt(result)})

        else:
            self._LOGGER.error('datatype unknown, using INT: %s ', dp_type)
            self._dp_values.update({dp_id: Ism8.decode_Int(result)})

        self._LOGGER.debug('decoded DP %s : %s = %s\n',
                               dp_id, Ism8.DATAPOINTS.get(dp_id,'unknown DP'),
                               self._dp_values[dp_id])

    def connection_lost(self, exc):
        """
        Is called when connection ends. closes socket.
        """
        self._LOGGER.debug('ISM8 closed the connection.Stopping')
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


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    _LOGGER = logging.getLogger(__name__)
    
    # for testing purposes only, relies on debug output
    myProtocol = Ism8()
    for keys, values in myProtocol.get_all_sensors().items():
        _LOGGER.debug("%s:  %s" % (keys, values))

    _eventloop = asyncio.get_event_loop()
    coro = _eventloop.create_server(myProtocol.factory, '', 12004)
    _server = _eventloop.run_until_complete(coro)
    # Serve requests until Ctrl+C is pressed
    _LOGGER.debug('Waiting for ISM8 connection on %s',
                  _server.sockets[0].getsockname())
    _eventloop.run_forever()
