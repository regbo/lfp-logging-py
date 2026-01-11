import inspect
import logging
import os
import pathlib
import sys
import threading
import types
from typing import Any, Callable, Mapping

"""
This module provides a lazy-initialization logging utility that automatically
configures logging handlers for stdout and stderr based on environment variables
and system arguments.

It includes functionality for:
- Automatic logger name discovery from caller frames.
- Separate handling for INFO messages (stdout) and other levels (stderr).
- Flexible log level parsing from strings, integers, and environment variables.
"""

LOG_LEVEL_DEFAULT = logging.INFO
LOG_LEVEL_ENV_NAME = "LOG_LEVEL"
LOG_LEVEL_SYS_ARG_NAME = "--log-level"
LOG_LEVEL_PARSE_ENVIRON_ENV_NAME = "LOG_LEVEL_PARSE_ENVIRON"
LOG_LEVEL_PARSE_SYS_ARGS_ENV_NAME = "LOG_LEVEL_PARSE_SYS_ARGS"

_LOG_LEVEL_NAME_NO_MATCH_PREFIX = "Level "
_BOOL_VALUES = {False: ["false", "no", "off", "0"], True: ["true", "yes", "on", "1"]}
_INIT_COMPLETE = False
_INIT_LOCK = threading.Lock()


class LogLevel:
    """
    A container for logging level information, mapping a human-readable name
     to its corresponding integer value.
    """

    def __init__(self, name: str, level: int) -> None:
        self.name = name
        self.level = level

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, level={self.level!r})"

    def __str__(self) -> str:
        return self.name


class _LazyLogger(logging.Logger):
    """
    A logger subclass that delays basic configuration until the first log
    message is handled. This ensures that logging is only configured if it is
    actually used.
    """

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)
        self._handler: logging.Logger | None = None

    def handle(self, record: logging.LogRecord) -> None:
        """
        Overrides the handle method to trigger basic configuration if it
        hasn't been run yet.
        """
        if self._handler is None:
            global _INIT_COMPLETE
            if not _INIT_COMPLETE:
                with _INIT_LOCK:
                    if not _INIT_COMPLETE:
                        _logging_basic_config()
                        _INIT_COMPLETE = True
            handler = logging.getLogger(self.name)
            if handler is self:
                raise ValueError(f"Logger name registered to self:{self.name}")
            self._handler = handler
        self._handler.handle(record)


def logger(*names: Any) -> logging.Logger:
    """
    Returns a logger instance. If basic configuration has not been completed,
    it returns a _LazyLogger instance that will trigger configuration on first
    use. If configuration is already complete, it returns a standard
    logging.Logger instance.

    If names are provided, it attempts to use the first valid name. If no name
    is provided or none are valid, it attempts to automatically determine a
    suitable name from the caller's stack frame.

    Args:
        *names: Potential names for the logger. The first valid name found
            (not None, not "__main__") will be used.

    Returns:
        A logging.Logger instance (either _LazyLogger or standard Logger).
    """
    name: str | None = None
    if names:
        for n in names:
            if name := _parse_logger_name(n):
                break
    if not name:
        current_module = __name__
        current_frame = inspect.currentframe()
        caller_frame = current_frame.f_back if current_frame else None
        try:
            # Try to get class name if called from an instance method
            name = _frame_attribute(
                caller_frame, "f_locals", "self", "__class__", "__name__"
            )
            if not name:
                # Try to get class name if called from a class method
                name = _frame_attribute(caller_frame, "f_locals", "cls", "__name__")
            if not name:
                # Fallback to module name derived from filename
                name = _parse_logger_name(
                    _frame_attribute(caller_frame, "f_code", "co_filename")
                )

        finally:
            # Clean up frames to avoid reference cycles
            del current_frame
            del caller_frame
        if not name:
            name = current_module
    return _LazyLogger(name) if not _INIT_COMPLETE else logging.getLogger(name)


def log_level(value: Any) -> LogLevel | None:
    """
    Converts a given value into a LogLevel object.

    Args:
        value: The value to convert. Can be an integer (e.g., 20),
            a string (e.g., 'INFO'), or a numeric string (e.g., '20').

    Returns:
        A LogLevel instance if conversion is successful, otherwise None.
    """
    if value is None:
        return None
    if isinstance(value, int):
        level_no = value
        level_name = logging.getLevelName(level_no)
        # Check if the level name is valid and not just "Level X"
        if (
                isinstance(level_name, str)
                and level_name
                and not level_name.startswith(_LOG_LEVEL_NAME_NO_MATCH_PREFIX)
        ):
            return LogLevel(level_name, level_no)
    else:
        level_name = str(value)
        if level_name:
            level_name = level_name.upper()
            level_no = logging.getLevelName(level_name)
            if isinstance(level_no, int):
                return LogLevel(level_name, level_no)
            elif level_name.isdigit():
                return log_level(int(level_name))

    return None


def _logging_basic_config():
    """
    Initialize the logging configuration for the application.

    This function sets up handlers for both stdout (INFO only) and stderr
    (all other levels) with specific formatting and date formats. It uses
    the LOG_LEVEL environment variable or --log-level system argument to
    determine the global logging level, defaulting to INFO.
    """
    date_format = "%Y-%m-%d %H:%M:%S"
    format_stdout = "%(message)s"
    format_stderr = (
        "%(asctime)s.%(msecs)03d | %(levelname)s | %(name)s:%(lineno)d - %(message)s"
    )
    log_level = _parse_log_level_sys_args()
    if log_level is None:
        log_level = _parse_log_level_environ()
    log_level_no = LOG_LEVEL_DEFAULT if log_level is None else log_level.level

    handlers = [
        _log_handler(
            log_level_no,
            sys.stdout,
            format_stdout,
            lambda record: record.levelno == logging.INFO,
        ),
        _log_handler(
            log_level_no,
            sys.stderr,
            format_stderr,
            lambda record: record.levelno != logging.INFO,
        ),
    ]

    logging.basicConfig(
        level=log_level_no,
        datefmt=date_format,
        handlers=handlers,
    )


def _log_handler(
        log_level_no: int,
        stream,
        log_format: str,
        filter_fn: Callable[[logging.LogRecord], bool] | None = None,
) -> logging.Handler:
    """
    Creates a StreamHandler with a specific format and an optional filter.
    """
    handler = logging.StreamHandler(stream)  # type: ignore[arg-type]
    handler.setFormatter(logging.Formatter(log_format))

    def _filter(record: logging.LogRecord) -> bool:
        """
        Filters records based on level and an optional custom filter function.
        """
        if record.levelno >= log_level_no:
            return True if filter_fn is None else filter_fn(record)
        else:
            return False

    handler.addFilter(_filter)
    return handler


def _parse_logger_name(value: Any) -> str | None:
    """
    Parses and cleans a potential logger name.

    It ignores "__main__", converts file paths ending in ".py" to a
    "parent.stem" format, and replaces spaces with underscores.

    Args:
        value: The value to parse as a logger name.

    Returns:
        A cleaned string name if valid, otherwise None.
    """
    if value is not None and "__main__" != value:
        if name := str(value):
            if name.endswith(".py"):
                try:
                    path = pathlib.Path(name)
                except Exception:
                    return name
                if stem := path.stem:
                    name = stem
                    parent = path.parent
                    if parent_name := parent.name if parent else None:
                        name = parent_name + "." + name
                    name = name.replace(" ", "_")
            return name
    return None


def _parse_log_level_sys_args() -> LogLevel | None:
    """
    Parses the log level from system arguments if enabled.
    """
    if _parse_bool(os.environ.get(LOG_LEVEL_PARSE_SYS_ARGS_ENV_NAME, None)) is False:
        return None
    value: str | None = None
    for idx in range(1, len(sys.argv)):
        arg = sys.argv[idx]
        if LOG_LEVEL_SYS_ARG_NAME == arg:
            if idx < len(sys.argv) - 1:
                value = sys.argv[idx + 1]
            else:
                value = None
    return log_level(value)


def _parse_log_level_environ() -> LogLevel | None:
    """
    Parses the log level from environment variables if enabled.
    """
    if _parse_bool(os.environ.get(LOG_LEVEL_PARSE_ENVIRON_ENV_NAME, None)) is False:
        return None
    value = os.environ.get(LOG_LEVEL_ENV_NAME, None)
    return log_level(value)


def _parse_bool(value: Any) -> bool | None:
    """
    Converts various input types to a boolean value.
    """
    if value is None:
        return None
    elif isinstance(value, bool):
        return value
    elif isinstance(value, int):
        return False if value == 0 else True if value == 1 else None
    else:
        value = str(value)
        if value:
            for result, bool_values in _BOOL_VALUES.items():
                for bool_value in bool_values:
                    if value.casefold() == bool_value.casefold():
                        return result
    return None


def _frame_attribute(frame: types.FrameType | None, *path_parts: str) -> str | None:
    """
    Safely retrieves a nested attribute from a frame object or a key from a dictionary.
    """
    value: Any = frame
    for path_part in path_parts:
        if value is None:
            break
        try:
            if isinstance(value, Mapping):
                value = value.get(path_part, None)
            else:
                value = getattr(value, path_part, None)
        except Exception:
            value = None
            break
    return value if isinstance(value, str) else None
