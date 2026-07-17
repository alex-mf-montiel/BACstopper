import asyncio
import unittest

from bactrack.client import BACtrackClient


class ResultDecoderTests(unittest.TestCase):
    def test_result_raw_value_matches_bytes_used_for_bac(self):
        packet = bytes.fromhex(
            "81 30 d0 00 00 d4 01 48 00 ef 05 8b 0a 31 06 1a 00"
        )

        decoded = BACtrackClient._decode_notification(packet)

        self.assertEqual(decoded["type"], "result")
        self.assertEqual(decoded["raw_value"], 208)
        self.assertEqual(decoded["value"], 0.0208)
        self.assertEqual(decoded["raw_hex"], packet.hex())

    def test_status_notification_retains_raw_packet(self):
        packet = bytes.fromhex("80 01 05 00 15 e7")

        decoded = BACtrackClient._decode_notification(packet)

        self.assertEqual(decoded["type"], "countdown")
        self.assertEqual(decoded["raw_hex"], packet.hex())
        self.assertEqual(decoded["bytes"], ["80", "01", "05", "00", "15", "e7"])

    def test_low_battery_status_is_a_terminal_device_error(self):
        decoded = BACtrackClient._decode_notification(bytes.fromhex("80 0a 00 00 15 e7"))

        self.assertEqual(decoded["type"], "error")
        self.assertEqual(decoded["error_code"], "low_battery")
        self.assertEqual(
            decoded["message"],
            "BACtrack battery is too low to start a test",
        )


class HangingNotifyClient:
    is_connected = True

    async def start_notify(self, characteristic, callback):
        await asyncio.sleep(1)


class HangingWriteClient:
    is_connected = True

    def __init__(self):
        self.stopped = False

    async def start_notify(self, characteristic, callback):
        pass

    async def write_gatt_char(self, characteristic, value, response):
        await asyncio.sleep(1)

    async def stop_notify(self, characteristic):
        self.stopped = True


class DeviceErrorClient:
    is_connected = True

    async def start_notify(self, characteristic, callback):
        self.callback = callback

    async def write_gatt_char(self, characteristic, value, response):
        self.callback(characteristic, bytes.fromhex("80 0a 00 00 15 e7"))

    async def stop_notify(self, characteristic):
        pass


class GattTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_notification_subscription_has_a_bounded_timeout(self):
        client = BACtrackClient()
        client.client = HangingNotifyClient()
        client.GATT_OPERATION_TIMEOUT = 0.01

        with self.assertRaisesRegex(
            asyncio.TimeoutError,
            "Timed out subscribing to BACtrack notifications",
        ):
            await client.take_test()

    async def test_start_command_write_has_a_bounded_timeout(self):
        fake_client = HangingWriteClient()
        client = BACtrackClient()
        client.client = fake_client
        client.GATT_OPERATION_TIMEOUT = 0.01

        with self.assertRaisesRegex(
            asyncio.TimeoutError,
            "Timed out writing the BACtrack start command",
        ):
            await client.take_test()

        self.assertTrue(fake_client.stopped)

    async def test_device_error_finishes_without_waiting_for_timeout(self):
        notifications = []
        client = BACtrackClient()
        client.client = DeviceErrorClient()

        result = await client.take_test(callback=notifications.append, timeout=1)

        self.assertIsNone(result)
        self.assertEqual(notifications[0]["error_code"], "low_battery")


if __name__ == "__main__":
    unittest.main()
