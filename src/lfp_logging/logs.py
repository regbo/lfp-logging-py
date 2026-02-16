import contextlib
import inspect
import logging
import pathlib
import sys
import threading
import types
from typing import IO, Any, Callable, Optional

from lfp_logging import config

"""
This module provides a lazy-initialization logging utility that automatically
configures logging handlers with ANSI color support.

The core design allows for "zero-config" logging that stays out of the way of
other configuration attempts. It achieves this by patching loggers on creation:
1. `logger()` returns a standard `logging.Logger` but patches its `isEnabledFor`
   method.
2. The first time a log level check occurs, `logging.basicConfig` is called
   automatically with a default handler (stderr) and a custom color formatter.
3. `logging.basicConfig` is also temporarily patched; if the user calls it
   later, it will remove the default handler to ensure the user's explicit
   configuration always wins.

It includes functionality for:
- Automatic logger name discovery from caller frames (classes, modules, filenames).
- ANSI color support for terminals and IDEs (VSCode, PyCharm, etc.).
- Transparent lazy initialization that supports multi-threaded environments.
"""

_HANDLE_PATCH_MARKER = ("_lfp_logging_handle_patch", object())
_PYTHON_FILE_EXTENSION = ".py"


class _InitContext(threading.Event):
    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()

    def call(self, fn: Callable, *args, set: bool = True) -> bool:
        if not self.is_set():
            with self._lock:
                if not self.is_set():
                    fn(*args)
                    if set:
                        self.set()
                    return True
        return False


_HANDLE_PATCH_CTX = _InitContext()
_BASIC_CONFIG_PATCH_CTX = _InitContext()
_BASIC_CONFIG_UNPATCH_CTX = _InitContext()


class _Formatter(logging.Formatter):
    """
    Custom logging formatter that adds ANSI color codes to log messages
    based on the log level and terminal support.
    """

    def __init__(self, stream: IO):
        super().__init__(config.LOG_FORMAT.get(), config.LOG_FORMAT_DATE.get())
        self.stream = stream

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = config.color(self.stream, record)
        if color is None:
            return message
        return f"{color}{message}" + "\x1b[0m"


def logger(*names: Any) -> logging.Logger:
    """
    Returns a standard logging.Logger instance, patched to trigger lazy
    initialization of the default logging configuration on first use.

    If names are provided, it attempts to use the first valid name. If no name
    is provided or none are valid, it attempts to automatically determine a
    suitable name from the caller's stack frame.

    Args:
        *names: Potential names for the logger. The first valid name found
            (not None, not "__main__") will be used.

    Returns:
        A logging.Logger instance patched for lazy initialization.
    """
    name: Optional[str] = None
    if names:
        for n in names:
            if name := _logger_name(n):
                break
    if not name:
        current_frame = inspect.currentframe()
        caller_frame = current_frame.f_back if current_frame else None
        try:
            if caller_frame:
                if (instance := caller_frame.f_locals.get("self", None)) is not None:
                    with contextlib.suppress(Exception):
                        name = _logger_name(instance.__class__.__name__)
                if (
                    not name
                    and (cls := caller_frame.f_locals.get("cls", None)) is not None
                ):
                    with contextlib.suppress(Exception):
                        name = _logger_name(cls.__name__)
                if (
                    not name
                    and (co_filename := caller_frame.f_code.co_filename) is not None
                ):
                    name = _logger_name(co_filename)
        finally:
            # Clean up frames to avoid reference cycles
            del current_frame
            del caller_frame
        if not name:
            name = __name__
    logger_obj = logging.getLogger(name)
    if config.LOG_CONFIG_LAZY.get():
        _HANDLE_PATCH_CTX.call(_logger_handle_patch, logger_obj, set=False)
    else:
        _BASIC_CONFIG_PATCH_CTX.call(_logging_basic_config_patch)
    return logger_obj


def _logger_handle_patch(logger_obj: logging.Logger):
    """
    Patches a logger's isEnabledFor method to trigger basic configuration.

    This is the entry point for the lazy initialization. It marks the logger
    as patched and replaces its isEnabledFor method with a wrapper that
    will call _logging_basic_config_patch once.
    """
    marker_name, marker_value = _HANDLE_PATCH_MARKER
    if getattr(logger_obj, marker_name, None) is marker_value:
        return
    setattr(logger_obj, marker_name, marker_value)

    _orig_is_enabled_for: Callable = logger_obj.isEnabledFor

    def _is_enabled_for(self: logging.Logger, level) -> bool:
        _BASIC_CONFIG_PATCH_CTX.call(_logging_basic_config_patch)
        _HANDLE_PATCH_CTX.set()
        self.isEnabledFor = _orig_is_enabled_for

        return _orig_is_enabled_for(level)

    logger_obj.isEnabledFor = types.MethodType(_is_enabled_for, logger_obj)


def _logging_basic_config_patch():
    """
    Initializes default logging handlers and patches logging.basicConfig.

    This function is called exactly once when the first log message (or check)
    is processed. It sets up stdout/stderr handlers and replaces
    logging.basicConfig with a wrapper that ensures user-provided configuration
    can override these defaults.
    """
    log_level_no = config.LOG_LEVEL.get().level
    handler = _create_logging_handler()

    logging.basicConfig(
        level=log_level_no,
        handlers=[handler],
    )

    # ensure that all handlers added
    if handler not in logging.root.handlers:
        return

    _orig_basic_config: Callable = logging.basicConfig

    def _basic_config_unpatch():
        root = logging.root
        for h in root.handlers[:]:
            if h is handler:
                root.removeHandler(h)
                h.close()

    def _basic_config(**kwargs):
        _BASIC_CONFIG_UNPATCH_CTX.call(_basic_config_unpatch)
        logging.basicConfig = _orig_basic_config
        _orig_basic_config(**kwargs)

    logging.basicConfig = _basic_config


def _create_logging_handler() -> logging.Handler:
    """
    Creates the default StreamHandler (stderr) with the custom color formatter.
    """
    stream = sys.stderr
    handler = logging.StreamHandler(stream)
    handler.setFormatter(_Formatter(stream))
    return handler


def _logger_name(value: Any) -> Optional[str]:
    """
    Parses and cleans a potential logger name.

    It ignores "__main__", converts file paths ending in ".py" to a
    "parent.stem" format, and replaces spaces with underscores.

    Args:
        value: The value to parse as a logger name.

    Returns:
        A cleaned string name if valid, otherwise None.
    """
    if value is None or value == "__main__":
        return None

    name = str(value) if value else None
    if not name or name == "__main__":
        return None

    if name.lower().endswith(_PYTHON_FILE_EXTENSION):
        with contextlib.suppress(Exception):
            path = pathlib.Path(name)
            if path_name := path.stem:
                if parent_name := path.parent.name if path.parent else None:
                    path_name = f"{parent_name}.{path_name}"
                if path_name := "".join(
                    c if c.isalnum() or c == "." else "_" for c in path_name
                ):
                    return path_name
    return name
