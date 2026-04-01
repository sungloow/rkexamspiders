import logging
import logging.handlers
from pathlib import Path

_LOG_DIR = Path(__file__).parent / "logs"
_FMT_DETAIL = "%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s"
_FMT_BRIEF = "%(asctime)s - %(levelname)s - %(message)s"

_FILE_LOGGERS = ("cto", "oems", "wechat", "xisai")
# xisai 额外输出到控制台
_CONSOLE_LOGGERS = {"xisai"}


def _make_rotating_handler(name: str, level: int = logging.DEBUG) -> logging.Handler:
    handler = logging.handlers.RotatingFileHandler(
        _LOG_DIR / f"{name}.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(_FMT_DETAIL))
    handler.setLevel(level)
    return handler


def setup_logging(level: int = logging.DEBUG) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FMT_BRIEF))
    console.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(console)

    for name in _FILE_LOGGERS:
        log = logging.getLogger(name)
        log.setLevel(level)
        log.addHandler(_make_rotating_handler(name))
        if name in _CONSOLE_LOGGERS:
            log.addHandler(console)
        log.propagate = False


setup_logging()

logger = logging.getLogger(__name__)
