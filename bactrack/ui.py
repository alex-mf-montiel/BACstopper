"""Terminal UI components for BACtrack tests."""
import os


class ColorScheme:
    """Customizable color scheme."""
    def __init__(self, header="96", countdown="93", blow="92", analyzing="94",
                 result_sober="92", result_under="93", result_over="91"):
        self.header = f"\033[{header}m"
        self.countdown = f"\033[{countdown}m"
        self.blow = f"\033[{blow}m"
        self.analyzing = f"\033[{analyzing}m"
        self.result_sober = f"\033[{result_sober}m"
        self.result_under = f"\033[{result_under}m"
        self.result_over = f"\033[{result_over}m"
        self.reset = "\033[0m"
        self.bold = "\033[1m"


SCHEMES = {
    "default": ColorScheme(),
    "matrix": ColorScheme(header="92", countdown="92", blow="92", analyzing="92"),
    "retro": ColorScheme(header="95", countdown="96", blow="93", analyzing="94"),
    "minimal": ColorScheme(header="97", countdown="97", blow="97", analyzing="97"),
}


class TerminalUI:
    """Terminal UI for breath tests."""
    def __init__(self, color_scheme="default"):
        self.colors = SCHEMES.get(color_scheme, SCHEMES["default"]) if isinstance(color_scheme, str) else color_scheme

    def clear(self):
        os.system('clear' if os.name != 'nt' else 'cls')

    def show_header(self):
        c = self.colors
        print(f"\n{c.header}{'='*60}{c.reset}")
        print(f"{c.bold}{c.header}                    BACtrack Breath Test{c.reset}")
        print(f"{c.header}{'='*60}{c.reset}\n")

    def show_connecting(self):
        self.clear()
        self.show_header()
        print(f"{self.colors.countdown}🔍 Scanning for BACtrack device...{self.colors.reset}\n")

    def show_connected(self, address):
        self.clear()
        self.show_header()
        print(f"{self.colors.blow}✅ Connected to device{self.colors.reset}\n")

    def show_get_ready(self):
        self.clear()
        self.show_header()
        c = self.colors
        print(f"\n{c.bold}{c.countdown}")
        print("        ╔════════════════════════════════╗")
        print("        ║         GET READY...           ║")
        print("        ╚════════════════════════════════╝")
        print(f"{c.reset}\n")

    def show_countdown(self, seconds):
        self.clear()
        self.show_header()
        c = self.colors
        print(f"\n{c.bold}{c.countdown}")
        print("        ╔════════════════════════════════╗")
        print(f"        ║         Warming Up: {seconds:2d}         ║")
        print("        ╚════════════════════════════════╝")
        print(f"{c.reset}\n")

    def show_blow_now(self):
        self.clear()
        self.show_header()
        c = self.colors
        print(f"\n{c.bold}{c.blow}")
        print("        ╔════════════════════════════════╗")
        print("        ║        💨 BLOW NOW! 💨         ║")
        print("        ╚════════════════════════════════╝")
        print(f"{c.reset}\n")

    def show_keep_blowing(self, seconds):
        self.clear()
        self.show_header()
        c = self.colors
        print(f"\n{c.bold}{c.blow}")
        print("        ╔════════════════════════════════╗")
        print("        ║      Keep Blowing...           ║")
        print("        ╚════════════════════════════════╝")
        print(f"{c.reset}\n")
        filled = 5 - seconds
        bar = "█" * (6 * filled) + "░" * (30 - 6 * filled)
        print(f"        {c.blow}[{bar}]{c.reset}")
        print(f"        {c.countdown}{seconds} seconds remaining{c.reset}\n")

    def show_analyzing(self):
        self.clear()
        self.show_header()
        c = self.colors
        print(f"\n{c.bold}{c.analyzing}")
        print("        ╔════════════════════════════════╗")
        print("        ║      🔬 Analyzing...           ║")
        print("        ╚════════════════════════════════╝")
        print(f"{c.reset}\n")

    def show_result(self, bac):
        self.clear()
        self.show_header()
        c = self.colors
        color = c.result_sober if bac == 0.0 else (c.result_under if bac < 0.08 else c.result_over)
        status = "Sober" if bac == 0.0 else ("Under Legal Limit" if bac < 0.08 else "Over Legal Limit")
        print(f"\n{c.bold}{color}")
        print("        ╔════════════════════════════════╗")
        print(f"        ║      BAC: {bac:.4f}%           ║")
        print(f"        ║      {status:^22}      ║")
        print("        ╚════════════════════════════════╝")
        print(f"{c.reset}\n")

    def show_error(self, message):
        self.clear()
        self.show_header()
        print(f"\n{self.colors.result_over}❌ {message}{self.colors.reset}\n")

    def update_from_notification(self, notification):
        """Update UI based on notification."""
        msg_type = notification['type']
        if msg_type == 'countdown':
            self.show_countdown(notification.get('value', 0))
        elif msg_type == 'start_blow':
            self.show_blow_now()
        elif msg_type == 'keep_blowing':
            self.show_keep_blowing(notification.get('value', 0))
        elif msg_type == 'analyzing':
            self.show_analyzing()
        elif msg_type in ['cancelled', 'blow_error']:
            self.show_error(notification['message'])
