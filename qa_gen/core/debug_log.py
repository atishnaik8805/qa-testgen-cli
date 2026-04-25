import datetime
from pathlib import Path

_LOG_PATH = Path.home() / ".qa-gen" / "debug.log"


def log(message: str) -> None:
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _LOG_PATH.exists():
        _LOG_PATH.touch(mode=0o600)
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")
