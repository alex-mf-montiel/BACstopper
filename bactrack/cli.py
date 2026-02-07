"""CLI interface for BACtrack breathalyzer."""
import asyncio
import os
import shutil
import stat
import sys
from pathlib import Path
import typer
from .client import BACtrackClient
from .ui import TerminalUI

app = typer.Typer(help="BACtrack breathalyzer CLI")


@app.command()
def test(
    theme: str = typer.Option("default", "--theme", "-t", help="UI theme"),
    no_ui: bool = typer.Option(False, "--no-ui", help="Disable UI"),
):
    """Take a breath test with full UI."""
    asyncio.run(run_test_with_ui(theme, no_ui))


@app.command()
def check(
    threshold: float = typer.Option(0.08, "--threshold", "-t", help="BAC threshold %"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """Check BAC threshold (for git hooks). Exit 0=pass, 1=fail, 2=error."""
    sys.exit(asyncio.run(run_check(threshold, quiet)))


VALID_SPICE = ("verde", "hot", "diablo")
VALID_HOOKS = ("pre-commit", "pre-push")


@app.command()
def install(
    repo: str = typer.Option(".", "--repo", "-r", help="Path to git repo"),
    threshold: float = typer.Option(0.0, "--threshold", help="BAC threshold"),
    spice: str = typer.Option("hot", "--spice", "-s", help="Spice level: verde, hot, diablo"),
    hook: str = typer.Option("pre-push", "--hook", help="Hook type: pre-commit or pre-push"),
):
    """Install BACstop git hook into a repo."""
    repo_path = Path(repo).resolve()
    git_dir = repo_path / ".git"

    if not git_dir.is_dir():
        print(f"  Not a git repo: {repo_path}")
        raise typer.Exit(1)

    if spice not in VALID_SPICE:
        print(f"  Invalid spice: {spice}. Choose from: {', '.join(VALID_SPICE)}")
        raise typer.Exit(1)

    if hook not in VALID_HOOKS:
        print(f"  Invalid hook: {hook}. Choose from: {', '.join(VALID_HOOKS)}")
        raise typer.Exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    dest = hooks_dir / hook

    # Find the bundled hook script
    hook_src = Path(__file__).resolve().parent.parent / "hooks" / "bacstop-hook"
    if not hook_src.exists():
        print(f"  Hook source not found at {hook_src}")
        raise typer.Exit(1)

    # Remove any existing BACstop hook in the other slot
    other_hook = "pre-commit" if hook == "pre-push" else "pre-push"
    other_dest = hooks_dir / other_hook
    if other_dest.exists():
        other_content = other_dest.read_text()
        if "BACstop" in other_content:
            other_dest.unlink()
            print(f"  Removed old BACstop {other_hook} hook.")

    if dest.exists():
        print(f"  Overwriting existing {hook} hook.")

    shutil.copy2(hook_src, dest)
    dest.chmod(dest.stat().st_mode | stat.S_IEXEC)

    # Write .bacstop config
    config_file = repo_path / ".bacstop"
    config_file.write_text(
        f"threshold={threshold:.2f}\n"
        f"spice={spice}\n"
        f"hook={hook}\n"
    )

    spice_desc = {
        "verde": "informational only, always allows",
        "hot": "blocks if BAC below threshold",
        "diablo": "blocks AND destroys your changes",
    }

    print()
    print(f"  BACstop installed!")
    print(f"  Hook:      {dest}")
    print(f"  Threshold: {threshold:.2f}%")
    print(f"  Spice:     {spice} ({spice_desc[spice]})")
    print()
    if spice == "diablo":
        print(f"  !! DIABLO MODE: failing the check will DESTROY your changes !!")
        print()


@app.command()
def uninstall(
    repo: str = typer.Option(".", "--repo", "-r", help="Path to git repo"),
):
    """Remove BACstop git hook from a repo."""
    repo_path = Path(repo).resolve()
    hooks_dir = repo_path / ".git" / "hooks"
    removed = False

    for hook_name in VALID_HOOKS:
        hook_path = hooks_dir / hook_name
        if hook_path.exists():
            content = hook_path.read_text()
            if "BACstop" in content:
                hook_path.unlink()
                print(f"  Removed BACstop {hook_name} hook.")
                removed = True

    if not removed:
        print("  No BACstop hooks found.")

    config = repo_path / ".bacstop"
    if config.exists():
        config.unlink()
        print("  Removed .bacstop config.")


@app.command()
def info():
    """Show device information."""
    asyncio.run(show_device_info())


async def run_test_with_ui(theme: str, no_ui: bool):
    """Run test with UI."""
    ui = TerminalUI(theme) if not no_ui else None
    client = BACtrackClient()
    try:
        (ui.show_connecting() if ui else print("Connecting..."))
        await client.connect()
        await asyncio.sleep(1)
        if ui:
            ui.show_connected(client.device_address)
            await asyncio.sleep(2)
            ui.show_get_ready()
            await asyncio.sleep(2)
        result = await client.take_test(
            callback=ui.update_from_notification if ui else lambda n: print(n['message']),
            timeout=60.0
        )
        if result is not None:
            (ui.show_result(result) if ui else print(f"\nBAC: {result:.4f}%"))
            await asyncio.sleep(5) if ui else None
        else:
            (ui.show_error("Test failed") if ui else print("Test failed"))
    except Exception as e:
        (ui.show_error(str(e)) if ui else print(f"Error: {e}"))
        sys.exit(1)
    finally:
        await client.disconnect()


async def run_check(threshold: float, quiet: bool) -> int:
    """Check BAC against threshold."""
    client = BACtrackClient()
    try:
        print(f"🔍 Checking BAC (threshold: {threshold:.2f}%)...") if not quiet else None
        await client.connect()
        result = await client.take_test(
            callback=lambda n: None if quiet else print(f"  {n['message']}"),
            timeout=60.0
        )
        if result is None:
            print("❌ Test failed") if not quiet else None
            return 2
        print(f"\n📊 BAC: {result:.4f}%") if not quiet else None
        if result >= threshold:
            print(f"✅ Above threshold - ALLOWED") if not quiet else None
            return 0
        else:
            print(f"🚫 Below threshold - BLOCKED") if not quiet else None
            return 1
    except Exception as e:
        print(f"❌ Error: {e}") if not quiet else None
        return 2
    finally:
        await client.disconnect()


async def show_device_info():
    """Show device info."""
    client = BACtrackClient()
    try:
        print("🔍 Scanning...")
        await client.connect()
        print(f"\n✅ Device found!")
        print(f"   Address: {client.device_address}")
        print(f"   Service: {client.SERVICE_UUID}")
        print(f"   Characteristic: {client.CHAR_UUID}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await client.disconnect()


def main():
    app()


if __name__ == "__main__":
    main()
