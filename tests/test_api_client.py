import json
import unittest

from bactrack.api_client import parse_sse


class SSEParserTests(unittest.TestCase):
    def test_parses_state_and_terminal_events(self):
        states = [
            {"status": "countdown", "message": "Warming up... 3s"},
            {"status": "complete", "message": "BAC Result", "bac": 0.0004},
        ]
        lines = []
        for event_name, state in zip(("state", "terminal"), states):
            lines.extend(
                [
                    f"event: {event_name}\n".encode(),
                    f"data: {json.dumps(state)}\n".encode(),
                    b"\n",
                ]
            )

        self.assertEqual(list(parse_sse(lines)), list(zip(("state", "terminal"), states)))

    def test_parses_final_event_without_trailing_blank_line(self):
        lines = [b"event: terminal\n", b'data: {"status":"error"}\n']

        self.assertEqual(
            list(parse_sse(lines)),
            [("terminal", {"status": "error"})],
        )


if __name__ == "__main__":
    unittest.main()
