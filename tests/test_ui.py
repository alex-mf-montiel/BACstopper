import io
import unittest
from contextlib import redirect_stdout

from bactrack.ui import TerminalUI


class ResultLayoutTests(unittest.TestCase):
    def test_result_box_has_consistent_width(self):
        ui = TerminalUI()
        ui.clear = lambda: None
        output = io.StringIO()

        with redirect_stdout(output):
            ui.show_result(0.0004)

        box_lines = [line for line in output.getvalue().splitlines() if "║" in line]
        self.assertEqual(
            box_lines,
            [
                "        ║          BAC: 0.0004%          ║",
                "        ║       Under Legal Limit        ║",
            ],
        )
        self.assertEqual({len(line) for line in box_lines}, {42})


if __name__ == "__main__":
    unittest.main()
