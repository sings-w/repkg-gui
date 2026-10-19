import json
import os
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home() / ".config"))) / "RePKG_GUI"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "repkg_exe_path": "",
    "default_output_dir": str(Path.home() / "Desktop" / "RePKG_Output"),
    "last_input_path": "",
    "last_mode": "single",
    "history": [],
}


def load() -> dict:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}
    return {**DEFAULTS, **data}


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_history(cfg: dict, input_path: str, output_path: str, mode: str) -> None:
    history = cfg.setdefault("history", [])
    history.insert(
        0,
        {
            "input": input_path,
            "output": output_path,
            "mode": mode,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        },
    )
    cfg["history"] = history[:10]
