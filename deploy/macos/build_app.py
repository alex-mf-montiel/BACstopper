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
    base_prefix = Path(
        subprocess.check_output(
            [str(python), "-c", "import sys; print(sys.base_prefix)"],
            text=True,
        ).strip()
    )
    python_app_executable = (
        base_prefix / "Resources" / "Python.app" / "Contents" / "MacOS" / "Python"
    )
    source_executable = (
        python_app_executable if python_app_executable.exists() else resolved_python
    )
    executable = macos_dir / "BACstopServer"
    shutil.copy2(source_executable, executable)
    executable.chmod(0o755)

    framework_library = base_prefix / "Python3"
    if framework_library.exists():
        shutil.copy2(framework_library, temporary / "Contents" / "Python3")
    if source_executable == python_app_executable:
        subprocess.run(
            [
                "install_name_tool",
                "-change",
                "@executable_path/../../../../Python3",
                "@executable_path/../Python3",
                str(executable),
            ],
            check=True,
        )

    source_config = (venv / "pyvenv.cfg").read_text().splitlines()
    config_lines = [
        f"home = {base_prefix / 'bin'}" if line.startswith("home = ") else line
        for line in source_config
    ]
    (temporary / "Contents" / "pyvenv.cfg").write_text(
        "\n".join(config_lines) + "\n"
    )
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
