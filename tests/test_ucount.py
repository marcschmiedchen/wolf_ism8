import logging

import wolf_ism8 as wolf

# raw telegrams captured from an ISM8i with FW 1.90 (see issue #94 of
# home-assistant-wolf_ism8)
MSG_DP372 = bytes.fromhex(
    "06:20:f0:80:00:15:04:00:00:00:f0:06:01:74:00:01:01:74:03:01:00".replace(":", "")
)
MSG_DP355 = bytes.fromhex(
    "06:20:f0:80:00:16:04:00:00:00:f0:06:01:63:00:01:01:63:03:02:01:00".replace(":", "")
)


class FakeTransport:
    """minimal transport, records what the ISM8 object writes back"""

    def __init__(self):
        self.written = []

    def get_extra_info(self, name):
        return ("192.168.0.10", 50000) if name == "peername" else None

    def write(self, data):
        self.written.append(bytes(data))

    def close(self):
        pass


def test_ucount_datapoints_are_decoded(caplog):
    caplog.set_level(logging.INFO)
    ism8 = wolf.Ism8()
    transport = FakeTransport()
    ism8.connection_made(transport)
    ism8.data_received(MSG_DP372)  # DPT_Value_1_Ucount, 1 byte
    ism8.data_received(MSG_DP355)  # DPT_Value_2_Ucount, 2 bytes
    assert ism8.read_sensor(372) == 0
    assert ism8.read_sensor(355) == 256
    # every message is acknowledged
    assert len(transport.written) == 2
    # decoded explicitly, not via the "not implemented" INT fallback
    assert "not implemented" not in caplog.text
