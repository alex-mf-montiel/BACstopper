"""
BACtrack Bluetooth Client - Clean implementation based on reverse engineered protocol
"""
import asyncio
from bleak import BleakScanner, BleakClient
from typing import Optional, Callable
import struct


class BACtrackClient:
    """Client for communicating with BACtrack breathalyzers via Bluetooth LE."""

    # Service and characteristic UUIDs
    SERVICE_UUID = "862bfff0-7d59-4359-8b59-a96db28bc679"
    CHAR_UUID = "862bfff1-7d59-4359-8b59-a96db28bc679"

    # Command to start a breath test
    CMD_START_TEST = bytes.fromhex("0001")

    def __init__(self, device_address: Optional[str] = None):
        """
        Initialize BACtrack client.

        Args:
            device_address: Bluetooth address of device. If None, will scan for any BACtrack device.
        """
        self.device_address = device_address
        self.client: Optional[BleakClient] = None
        self.bac_result: Optional[float] = None
        self._test_complete = asyncio.Event()

    async def find_device(self) -> str:
        """Scan for and return address of first BACtrack device found."""
        if self.device_address:
            return self.device_address

        devices = await BleakScanner.discover(timeout=10.0)

        for device in devices:
            if device.name and "bactrack" in device.name.lower():
                self.device_address = device.address
                return device.address

        raise RuntimeError("No BACtrack device found")

    async def connect(self) -> bool:
        """Connect to the BACtrack device."""
        address = await self.find_device()
        self.client = BleakClient(address, timeout=20.0)
        await self.client.connect()
        return self.client.is_connected

    async def disconnect(self):
        """Disconnect from the device."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    def _decode_notification(self, data: bytes) -> dict:
        """
        Decode a notification from the device.

        Returns:
            dict with 'type', 'message', and optional 'value' keys
        """
        # Always include full hex for debugging
        full_hex = data.hex()
        byte_array = [f"{b:02x}" for b in data]

        if len(data) < 2:
            return {"type": "unknown", "message": "Invalid packet", "raw_hex": full_hex, "bytes": byte_array}

        hex_str = data.hex()
        prefix = hex_str[:4]

        # Countdown/warmup
        if prefix == "8001" and len(data) >= 3:
            seconds = data[2]
            return {"type": "countdown", "message": f"Warming up... {seconds}s", "value": seconds}

        # Begin blowing
        elif prefix == "8002":
            return {"type": "start_blow", "message": "BEGIN BLOWING NOW!"}

        # Keep blowing
        elif prefix == "8003" and len(data) >= 3:
            remaining = data[2]
            return {"type": "keep_blowing", "message": f"Keep blowing... {remaining}s", "value": remaining}

        # Analyzing
        elif prefix == "8004":
            return {"type": "analyzing", "message": "Analyzing sample..."}

        # Finalizing
        elif prefix == "8005":
            return {"type": "finalizing", "message": "Finalizing results..."}

        # Wrapping up
        elif prefix == "8006":
            return {"type": "wrapping_up", "message": "Test wrapping up..."}

        # Cancelled/timeout
        elif prefix == "8007":
            return {"type": "cancelled", "message": "Test cancelled or timed out"}

        # Blow error (insufficient breath)
        elif prefix == "8008":
            return {"type": "blow_error", "message": "Blow error - insufficient breath detected"}

        # BAC Result
        elif hex_str.startswith("81") and len(data) >= 5:
            # Try parsing from different byte positions and divisors
            # Let's examine all possibilities
            attempts = {}

            # Bytes 2-3
            if len(data) >= 4:
                val_2_3 = struct.unpack("<H", data[2:4])[0]
                attempts["bytes_2_3"] = {
                    "raw": val_2_3,
                    "div_100": val_2_3 / 100.0,
                    "div_1000": val_2_3 / 1000.0,
                    "div_10000": val_2_3 / 10000.0,
                }

            # Bytes 3-4
            if len(data) >= 5:
                val_3_4 = struct.unpack("<H", data[3:5])[0]
                attempts["bytes_3_4"] = {
                    "raw": val_3_4,
                    "div_100": val_3_4 / 100.0,
                    "div_1000": val_3_4 / 1000.0,
                    "div_10000": val_3_4 / 10000.0,
                }

            # Bytes 4-5 (old wrong guess)
            if len(data) >= 6:
                val_4_5 = struct.unpack("<H", data[4:6])[0]
                attempts["bytes_4_5"] = {
                    "raw": val_4_5,
                    "div_100": val_4_5 / 100.0,
                    "div_1000": val_4_5 / 1000.0,
                    "div_10000": val_4_5 / 10000.0,
                }

            # CORRECT: Bytes 2-3 with divisor 10000
            val_2_3 = struct.unpack("<H", data[2:4])[0]
            bac_percent = val_2_3 / 10000.0

            return {
                "type": "result",
                "message": f"BAC Result: {bac_percent:.4f}%",
                "value": bac_percent,
                "raw_hex": full_hex,
                "bytes": byte_array,
                "raw_value": val_3_4
            }

        # Unknown
        else:
            return {"type": "unknown", "message": f"Unknown: {hex_str}", "raw_hex": full_hex, "bytes": byte_array}

    async def take_test(
        self,
        callback: Optional[Callable[[dict], None]] = None,
        timeout: float = 50.0
    ) -> Optional[float]:
        """
        Perform a breath test.

        Args:
            callback: Optional function to call for each notification.
                     Receives decoded notification dict.
            timeout: Maximum time to wait for test completion (seconds)

        Returns:
            BAC result as float, or None if test failed/was cancelled
        """
        if not self.client or not self.client.is_connected:
            raise RuntimeError("Not connected to device")

        self.bac_result = None
        self._test_complete.clear()

        # Internal notification handler
        def notification_handler(sender, data: bytes):
            decoded = self._decode_notification(data)

            # Call user callback if provided
            if callback:
                callback(decoded)

            # Check if test is complete
            if decoded["type"] == "result":
                self.bac_result = decoded["value"]
                self._test_complete.set()
            elif decoded["type"] in ["cancelled", "blow_error"]:
                self._test_complete.set()

        # Subscribe to notifications
        await self.client.start_notify(self.CHAR_UUID, notification_handler)

        try:
            # Send start command
            await self.client.write_gatt_char(self.CHAR_UUID, self.CMD_START_TEST, response=True)

            # Wait for test to complete or timeout
            try:
                await asyncio.wait_for(self._test_complete.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                if callback:
                    callback({"type": "timeout", "message": "Test timed out"})

        finally:
            # Unsubscribe
            await self.client.stop_notify(self.CHAR_UUID)

        return self.bac_result


# Example usage
async def main():
    """Example of using the BACtrack client."""

    def print_status(notification: dict):
        """Print status updates during test."""
        print(f"  {notification['message']}")

    client = BACtrackClient()

    try:
        # Find and connect
        print("🔍 Scanning for BACtrack device...")
        await client.connect()
        print(f"✅ Connected to {client.device_address}\n")

        # Perform test
        print("🚀 Starting breath test...")
        print("   (Blow when it beeps!)\n")

        result = await client.take_test(callback=print_status)

        # Display result
        print()
        if result is not None:
            print(f"🎯 Final BAC: {result:.4f}%")
        else:
            print("❌ Test failed or was cancelled")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        await client.disconnect()
        print("\n🔌 Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
