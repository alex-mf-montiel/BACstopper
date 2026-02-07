# BACtrack Bluetooth Protocol Documentation

## Overview
This document describes the reverse-engineered Bluetooth LE protocol for BACtrack breathalyzers.

## Connection Details

**Service UUID:** `862bfff0-7d59-4359-8b59-a96db28bc679`
**Characteristic UUID:** `862bfff1-7d59-4359-8b59-a96db28bc679`
**Properties:** Write, Notify

## Commands

### Start Test
**Command:** `0x00 0x01`
**Description:** Initiates a breath test sequence

## Notifications (Device → Client)

All notifications are 6 bytes in the format:
```
[PREFIX_BYTE_1] [PREFIX_BYTE_2] [DATA] [0x00] [0x15] [0xE7]
```

The last 3 bytes (`0x00 0x15 0xE7`) appear to be a consistent footer/checksum.

### Status Codes

| Prefix | Hex | Type | Data Byte | Description |
|--------|-----|------|-----------|-------------|
| `8001` | `80 01` | Countdown | Seconds (0-5) | Warmup countdown before test starts |
| `8002` | `80 02` | Start Blow | `00` | Signal to begin blowing (device beeps) |
| `8003` | `80 03` | Keep Blowing | Seconds (0-5) | Continue blowing, seconds remaining |
| `8004` | `80 04` | Analyzing | `00` | Device is analyzing the breath sample |
| `8005` | `80 05` | Finalizing | `00` | Finalizing the results |
| `8006` | `80 06` | Wrapping Up | `00` | Test wrapping up |
| `8007` | `80 07` | Cancelled | `00` | Test was cancelled or timed out |
| `8008` | `80 08` | Blow Error | `00` | Insufficient breath detected |
| `81xx` | `81 ...` | **BAC Result** | See below | Blood Alcohol Content result |

### BAC Result Format

When the prefix is `0x81`, the packet contains the BAC result. **Note:** This packet is 17 bytes long.

```
[0x81] [??] [LOW_BYTE] [HIGH_BYTE] [... more data ...]
```

- **Bytes 2-3** contain a 16-bit **little-endian** unsigned integer
- Divide this value by **10,000** to get the BAC percentage

**Example:**
```
Packet: 81 30 D0 00 00 D4 01 48 00 EF 05 8B 0A 31 06 1A 00
Bytes 2-3: 0xD0 0x00 = 208 (decimal, little-endian)
BAC: 208 / 10000 = 0.0208%
```

**Another example:**
```
Packet: 81 30 20 00 00 ...
Bytes 2-3: 0x20 0x00 = 32 (decimal, little-endian)
BAC: 32 / 10000 = 0.0032%
```

**Zero BAC:**
```
Packet: 81 DC 07 00 00 CF 01 0B 00 9F 05 64 09 B8 05 00 00
Bytes 2-3: 0x07 0x00 = 7 (decimal, little-endian)
BAC: 7 / 10000 = 0.0007% ≈ 0.00%
```

## Typical Test Flow

1. **Client** sends `0x0001` (start test command)
2. **Device** sends `8001 05` (5 second countdown)
3. **Device** sends `8001 04` (4 seconds...)
4. **Device** sends `8001 03` (3 seconds...)
5. **Device** sends `8001 02` (2 seconds...)
6. **Device** sends `8001 01` (1 second...)
7. **Device** sends `8002 00` (begin blow - **BEEPS**)
   - *User must blow here!*
8. **Device** sends `8003 05` (keep blowing, 5 seconds left)
9. **Device** sends `8003 04` (keep blowing, 4 seconds...)
10. ...continues until blow complete...
11. **Device** sends `8004 00` (analyzing)
12. **Device** sends `8005 00` (finalizing)
13. **Device** sends `81 xx xx xx YY YY` (**BAC RESULT**)

## Error Cases

### Timeout (No Blow)
If user doesn't blow within ~20 seconds of the beep:
- **Device** sends `8007 00` (cancelled)

### Insufficient Breath
If user doesn't blow hard/long enough:
- **Device** sends `8008 00` (blow error)

## Implementation Notes

1. The characteristic supports both **write** and **notify** operations
2. Subscribe to notifications **before** sending the start command
3. The test takes approximately 30-40 seconds total
4. User must blow **immediately** when the device beeps (after `8002` message)
5. Blowing requires steady, continuous breath for 4-5 seconds
6. The device will auto-off after a period of inactivity

## References

- Reverse engineered from BACtrack C6 model
- Protocol verified through live Bluetooth capture
- Compatible with `bleak` Python library on macOS
