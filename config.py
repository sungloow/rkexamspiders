import tomllib
import os
from pathlib import Path

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.toml"


def get_config() -> dict:
    path = Path(os.environ.get("CONFIG_PATH", _DEFAULT_CONFIG_PATH))
    with open(path, "rb") as f:
        return tomllib.load(f)


def get_cto_account(subject_name: str) -> tuple[str, str]:
    cfg = get_config()
    account = cfg.get("cto", {}).get(subject_name, {})
    return account.get("account", ""), account.get("password", "")


config = get_config()
