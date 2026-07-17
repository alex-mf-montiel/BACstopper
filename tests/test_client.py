import unittest

from bactrack.client import BACtrackClient


class ResultDecoderTests(unittest.TestCase):
    def test_result_raw_value_matches_bytes_used_for_bac(self):
        packet = bytes.fromhex(
            "81 30 d0 00 00 d4 01 48 00 ef 05 8b 0a 31 06 1a 00"
        )

        decoded = BACtrackClient()._decode_notification(packet)

        self.assertEqual(decoded["type"], "result")
        self.assertEqual(decoded["raw_value"], 208)
        self.assertEqual(decoded["value"], 0.0208)
        self.assertEqual(decoded["raw_hex"], packet.hex())

    def test_status_notification_retains_raw_packet(self):
        packet = bytes.fromhex("80 01 05 00 15 e7")

        decoded = BACtrackClient()._decode_notification(packet)

        self.assertEqual(decoded["type"], "countdown")
        self.assertEqual(decoded["raw_hex"], packet.hex())
        self.assertEqual(decoded["bytes"], ["80", "01", "05", "00", "15", "e7"])


if __name__ == "__main__":
    unittest.main()
