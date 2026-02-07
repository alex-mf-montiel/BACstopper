"""
BACtrack - Bluetooth breathalyzer client for BACtrack devices.
"""

from .client import BACtrackClient
from .ui import TerminalUI, ColorScheme, SCHEMES

__version__ = "1.0.0"
__all__ = ["BACtrackClient", "TerminalUI", "ColorScheme", "SCHEMES"]
