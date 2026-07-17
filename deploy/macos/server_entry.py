"""Application entry point executed by the bundled Python process."""

import os
import plistlib
import site
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
with (APP_ROOT / "Contents" / "Info.plist").open("rb") as info_file:
    INFO = plistlib.load(info_file)

REPO_ROOT = Path(INFO["BACstopRepositoryPath"])
VENV_ROOT = Path(INFO["BACstopVirtualenvPath"])
VENV_SITE_PACKAGES = (
    VENV_ROOT
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
)
site.addsitedir(str(VENV_SITE_PACKAGES))
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
sys.stdout = (LOG_DIR / "server.log").open("a", buffering=1)
sys.stderr = (LOG_DIR / "server.error.log").open("a", buffering=1)

import uvicorn  # noqa: E402


uvicorn.run(
    "bactrack.server:app",
    host=os.environ.get("BACSTOP_HOST", "0.0.0.0"),
    port=int(os.environ.get("BACSTOP_PORT", "8000")),
)
