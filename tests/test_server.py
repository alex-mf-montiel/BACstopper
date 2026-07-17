import asyncio
import json
import unittest

from fastapi import HTTPException

from bactrack.server import (
    TERMINAL_STATUSES,
    TestManager,
    create_app,
    format_sse,
    normalize_status,
)


class ControlledClient:
    release = None

    def __init__(self):
        self.disconnected = False

    async def connect(self):
        return True

    async def take_test(self, callback):
        await type(self).release.wait()
        callback(
            {
                "type": "result",
                "message": "BAC Result: 0.0208%",
                "value": 0.0208,
                "raw_value": 208,
                "raw_hex": "8130d00000d4014800ef058b0a31061a00",
                "bytes": [],
            }
        )
        return 0.0208

    async def disconnect(self):
        self.disconnected = True


class ErrorClient:
    async def connect(self):
        raise RuntimeError("device unavailable")

    async def disconnect(self):
        pass


class StatusNormalizationTests(unittest.TestCase):
    def test_all_public_notification_mappings(self):
        expected = {
            "countdown": "countdown",
            "start_blow": "blow",
            "keep_blowing": "blow",
            "analyzing": "analyzing",
            "finalizing": "analyzing",
            "wrapping_up": "analyzing",
            "result": "complete",
            "cancelled": "cancelled",
            "blow_error": "blow_error",
            "timeout": "timeout",
            "error": "error",
        }
        self.assertEqual({key: normalize_status(key) for key in expected}, expected)
        self.assertIsNone(normalize_status("unknown"))


class ServerLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        ControlledClient.release = asyncio.Event()

    async def asyncTearDown(self):
        ControlledClient.release.set()
        await asyncio.sleep(0)

    async def test_concurrent_test_is_rejected_with_http_409(self):
        app = create_app(client_factory=ControlledClient)
        route = next(
            route
            for route in app.routes
            if getattr(route, "path", None) == "/tests" and "POST" in route.methods
        )
        await route.endpoint(None)

        with self.assertRaises(HTTPException) as raised:
            await route.endpoint(None)

        self.assertEqual(raised.exception.status_code, 409)

    async def test_state_serialization_and_terminal_result(self):
        manager = TestManager(client_factory=ControlledClient)
        initial = await manager.create_test(metadata={"source": "test-suite"})
        self.assertEqual(
            set(initial),
            {
                "test_id",
                "status",
                "message",
                "bac",
                "raw_result_packet",
                "latest_raw_notification",
                "notification_history",
                "error",
                "metadata",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(initial["metadata"], {"source": "test-suite"})

        await asyncio.sleep(0)
        ControlledClient.release.set()
        await manager.records[initial["test_id"]].task
        final = manager.get_test(initial["test_id"])

        self.assertEqual(final["status"], "complete")
        self.assertEqual(final["bac"], 0.0208)
        self.assertEqual(
            final["raw_result_packet"], "8130d00000d4014800ef058b0a31061a00"
        )
        self.assertEqual(final["latest_raw_notification"], final["raw_result_packet"])
        self.assertEqual(len(final["notification_history"]), 1)
        json.dumps(final)

    async def test_exception_reaches_terminal_error_state(self):
        manager = TestManager(client_factory=ErrorClient)
        initial = await manager.create_test()

        await manager.records[initial["test_id"]].task
        final = manager.get_test(initial["test_id"])

        self.assertIn(final["status"], TERMINAL_STATUSES)
        self.assertEqual(final["status"], "error")
        self.assertEqual(final["error"], "device unavailable")

    async def test_subscription_emits_current_and_terminal_states(self):
        manager = TestManager(client_factory=ControlledClient)
        initial = await manager.create_test()
        queue = manager.subscribe(initial["test_id"])

        self.assertEqual((await queue.get())["status"], "scanning")
        await asyncio.sleep(0)
        self.assertEqual((await queue.get())["status"], "connected")

        ControlledClient.release.set()
        terminal = await queue.get()
        self.assertEqual(terminal["status"], "complete")
        self.assertTrue(format_sse(terminal).startswith("event: terminal\ndata: "))
        self.assertTrue(format_sse(terminal).endswith("\n\n"))


if __name__ == "__main__":
    unittest.main()
