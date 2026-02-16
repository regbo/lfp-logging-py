import logging
import os
from dataclasses import dataclass
from functools import cache
from typing import IO, Any, Callable, Optional

from lfp_logging import log_level

"""
This module manages the logging configuration by reading from environment
variables. It provides defaults that can be overridden by the user via
the standard environment variable names.

Configuration is handled via `_Config` objects which lazily parse environment
values when requested.
"""


@dataclass
class _Config:
    """
    A generic configuration container that maps an environment variable
    to a parsed value.
    """

    env_name: str
    parser: Callable[[Optional[str]], Any]

    def get(self) -> Any:
        return self.parser(_env_value(self.env_name))


LOG_LEVEL = _Config("LOG_LEVEL", lambda v: log_level.get(v, logging.INFO))
LOG_CONFIG_LAZY = _Config("LOG_CONFIG_LAZY", lambda v: _parse_bool(v))
LOG_FORMAT = _Config(
    "LOG_FORMAT",
    lambda v: v or "%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s",
)
LOG_FORMAT_DATE = _Config("LOG_FORMAT_DATE", lambda v: v or "%Y-%m-%d %H:%M:%S")

_LOG_FORMAT_COLOR_ENV_NAME = "LOG_FORMAT_COLOR"
_LOG_LEVEL_COLORS = {
    "TRACE": "\x1b[90m",
    log_level.get(logging.DEBUG).name: "\x1b[36m",
    log_level.get(logging.INFO).name: "\x1b[38;5;244m",
    log_level.get(logging.WARNING).name: "\x1b[33m",
    log_level.get(logging.ERROR).name: "\x1b[31m",
    log_level.get(logging.CRITICAL).name: "\x1b[1;31m",
}


def color(stream: IO, record: logging.LogRecord) -> Optional[str]:
    """
    Returns the ANSI color code for a given log record if the stream supports it.

    Color selection order:
    1. `LOG_FORMAT_COLOR_<LEVEL>` environment variable.
    2. `LOG_FORMAT_COLOR` environment variable.
    3. Default level-specific colors.
    """
    if not _supports_color(stream):
        return None
    level_obj = log_level.get(record, None)
    if level_obj is None:
        return None
    ansi_color = _env_value(_LOG_FORMAT_COLOR_ENV_NAME + "_" + level_obj.name.upper())
    if ansi_color is None:
        ansi_color = _env_value(_LOG_FORMAT_COLOR_ENV_NAME)
    if ansi_color is None:
        ansi_color = _LOG_LEVEL_COLORS.get(level_obj.name, None)
    return ansi_color


def _supports_color(stream: IO) -> bool:
    """
    Determines if the given stream supports ANSI color output.
    Checks for TTY status, IDE-specific environment variables, and OS capabilities.
    """
    isatty = False
    try:
        if hasattr(stream, "isatty") and stream.isatty():
            isatty = True
    except Exception:
        pass
    if not isatty:
        # VSCode + Cursor
        if _env_value("TERM_PROGRAM") == "vscode":
            return True

        # JetBrains IDEs (PyCharm, IntelliJ)
        if _env_value("PYCHARM_HOSTED") == "1":
            return True

        # Codespaces / remote devcontainers
        if _env_value("CODESPACES") == "true":
            return True

    return _os_supports_color()


@cache
def _os_supports_color() -> bool:
    term = _env_value("TERM")
    if term is None or term == "dumb":
        return False

    ci = _env_value("CI")
    if ci is not None and ci in ("GITHUB_ACTIONS", "GITLAB_CI", "COLORTERM"):
        return False

    if os.name == "nt":
        env = os.environ
        return any(
            k in env for k in ("WT_SESSION", "ANSICON", "ConEmuANSI", "TERM_PROGRAM")
        )

    if _env_value("COLORTERM") is not None:
        return True

    # Known color capable TERM values
    color_terms = (
        "xterm",
        "xterm-color",
        "xterm-256color",
        "screen",
        "screen-256color",
        "tmux",
        "tmux-256color",
        "rxvt-unicode",
        "rxvt-unicode-256color",
        "linux",
    )

    return any(term.startswith(t) for t in color_terms)


def _env_value(name: Any) -> Optional[str]:
    value = os.environ.get(name, None)
    if value:
        value = str(value).strip()
    return value or None


def _parse_bool(value: Any, default: Optional[bool] = False) -> Optional[bool]:
    if value is not None:
        value = str(value).lower().strip()
        if value:
            if value in ("true", "1", "yes", "on"):
                return True
            elif value in ("false", "0", "no", "off"):
                return False
    return default
