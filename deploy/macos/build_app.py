"""Build a signed BACstop Server app around the active virtualenv Python."""

import argparse
import os
import plistlib
import shutil
import subprocess
from pathlib import Path


def build_app(output: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    venv = next(
        (
            candidate
            for candidate in (repo_root / ".venv", repo_root / "venv")
            if (candidate / "bin" / "python").exists()
        ),
        None,
    )
    if venv is None:
        raise SystemExit("Virtualenv not found; expected .venv/ or venv/")
    python = venv / "bin" / "python"

    source_dir = Path(__file__).resolve().parent
    temporary = output.with_name(f".{output.name}.tmp")
    if temporary.exists():
        shutil.rmtree(temporary)

    macos_dir = temporary / "Contents" / "MacOS"
    resources_dir = temporary / "Contents" / "Resources"
    macos_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)

    resolved_python = Path(os.path.realpath(python))
    executable = macos_dir / "BACstopServer"
    shutil.copy2(resolved_python, executable)
    executable.chmod(0o755)

    # Apple's Command Line Tools Python launcher resolves its framework library
    # relative to the executable when it lives inside an application bundle.
    framework_library = resolved_python.parent.parent / "Python3"
    if framework_library.exists():
        shutil.copy2(framework_library, temporary / "Contents" / "Python3")

    shutil.copy2(source_dir / "server_entry.py", resources_dir / "server_entry.py")

    with (source_dir / "Info.plist").open("rb") as source:
        info = plistlib.load(source)
    info["BACstopRepositoryPath"] = str(repo_root)
    info["BACstopVirtualenvPath"] = str(venv)
    with (temporary / "Contents" / "Info.plist").open("wb") as destination:
        plistlib.dump(info, destination, sort_keys=False)

    subprocess.run(
        ["codesign", "--force", "--deep", "--sign", "-", str(temporary)],
        check=True,
    )
    if output.exists():
        shutil.rmtree(output)
    temporary.rename(output)
    print(f"Built {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "BACstop Server.app",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    build_app(args.output.expanduser().resolve())


if __name__ == "__main__":
    main()
