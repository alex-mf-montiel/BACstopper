# BACtrack Bluetooth Client

✅ **Fully reverse-engineered** BACtrack Bluetooth protocol
✅ **Beautiful terminal UI** with customizable themes
✅ **Git hook support** for BAC-gated commits
✅ **Modular design** - use as library or CLI

## Installation

```bash
pip install -e .
```

## CLI Commands

### Take a Test

```bash
# With full UI (default theme)
bactrack test

# With custom theme
bactrack test --theme matrix
bactrack test --theme retro
bactrack test --theme minimal

# No UI (just output)
bactrack test --no-ui
```

### Check BAC (Git Hook)

```bash
bactrack check --threshold 0.08
```

**Exit codes:**
- `0` - BAC >= threshold (ALLOWED)
- `1` - BAC < threshold (BLOCKED)
- `2` - Test failed/error

### Device Info

```bash
bactrack info
```

## Git Hook

BACstop ships with a git hook that runs a breathalyzer check before commit or push.

### Quick Install

```bash
# Default: pre-push hook, hot spice, 0.00 threshold
bactrack install

# Pre-commit hook with diablo spice at 0.05%
bactrack install --hook pre-commit --spice diablo --threshold 0.05

# Install into a different repo
bactrack install --repo /path/to/repo --spice verde
```

### Spice Levels

| Spice | What happens when BAC is below threshold |
|-------|------------------------------------------|
| **verde** | Shows your BAC but lets you through anyway |
| **hot** | Blocks the commit/push |
| **diablo** | Blocks AND **destroys your changes** (restores staged files on pre-commit, hard resets to upstream on pre-push) |

### Hook Type

| Option | When it runs |
|--------|-------------|
| `--hook pre-commit` | Before every `git commit` |
| `--hook pre-push` | Before every `git push` |

### Configuration

The `.bacstop` config file is created automatically and uses key=value format:

```
threshold=0.05
spice=hot
hook=pre-push
```

Commit it to share settings with your team. Environment variables override the file:

| Variable | Overrides |
|----------|-----------|
| `BACSTOP_THRESHOLD` | `threshold` |
| `BACSTOP_SPICE` | `spice` |

### Uninstall

```bash
bactrack uninstall
```

### Manual Install

```bash
cp hooks/bacstop-hook .git/hooks/pre-push   # or pre-commit
chmod +x .git/hooks/pre-push
cat > .bacstop << 'EOF'
threshold=0.05
spice=hot
hook=pre-push
EOF
```

## Library Usage

### Basic Test

```python
from bactrack import BACtrackClient
import asyncio

async def main():
    client = BACtrackClient()
    await client.connect()

    result = await client.take_test(
        callback=lambda n: print(n['message'])
    )

    print(f"BAC: {result:.4f}%")
    await client.disconnect()

asyncio.run(main())
```

### With Terminal UI

```python
from bactrack import BACtrackClient, TerminalUI
import asyncio

async def main():
    ui = TerminalUI("matrix")
    client = BACtrackClient()

    ui.show_connecting()
    await client.connect()
    ui.show_connected(client.device_address)
    ui.show_get_ready()

    result = await client.take_test(
        callback=ui.update_from_notification
    )

    ui.show_result(result)
    await client.disconnect()

asyncio.run(main())
```

### Custom Color Theme

```python
from bactrack import ColorScheme, TerminalUI

my_theme = ColorScheme(
    header="95",       # Magenta
    countdown="93",    # Yellow
    blow="92",         # Green
    analyzing="94",    # Blue
    result_sober="92",
    result_under="93",
    result_over="91",
)

ui = TerminalUI(my_theme)
```

**ANSI color codes:** 91=Red, 92=Green, 93=Yellow, 94=Blue, 95=Magenta, 96=Cyan, 97=White

## Protocol

See [PROTOCOL.md](PROTOCOL.md) for complete Bluetooth protocol documentation.

## Project Structure

```
new_attempt/
├── bactrack/
│   ├── __init__.py      # Package exports
│   ├── client.py        # BACtrack Bluetooth client
│   ├── ui.py            # Terminal UI components
│   └── cli.py           # Typer CLI commands
├── pyproject.toml       # Package config
├── PROTOCOL.md          # Protocol documentation
└── README.md            # This file
```

## License

MIT
