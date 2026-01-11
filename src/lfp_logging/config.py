import logging
import os
import sys

from lfp_logging import log_level
from lfp_logging.log_level import LogLevel

"""
This module manages the logging configuration by reading from environment
variables and system arguments. It provides defaults that can be overridden
by the user via the standard environment variable names.
"""

LOG_LEVEL_DEFAULT = logging.INFO
LOG_FORMAT_DATE_DEFAULT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT_DEFAULT = "%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s"

LOG_LEVEL_SYS_ARG_NAME = "--log-level"

LOG_LEVEL_ENV_NAME = "LOG_LEVEL"
LOG_FORMAT_DATE_ENV_NAME = "LOG_FORMAT_DATE"
LOG_FORMAT_STDOUT_ENV_NAME = "LOG_FORMAT_STDOUT"
LOG_FORMAT_STDERR_ENV_NAME = "LOG_FORMAT_STDERR"


def level() -> LogLevel:
    """
    Retrieves the global log level from system arguments or environment variables.
    System arguments take precedence over environment variables.
    """
    value = os.environ.get(LOG_LEVEL_ENV_NAME, None)
    for idx in range(1, len(sys.argv)):
        arg = sys.argv[idx]
        if arg == LOG_LEVEL_SYS_ARG_NAME:
            value = sys.argv[idx + 1] if idx < len(sys.argv) - 1 else None
    return log_level.get(value, LOG_LEVEL_DEFAULT)


def date_format():
    """Returns the date format string for logging timestamps."""
    return os.environ.get(LOG_FORMAT_DATE_ENV_NAME, None) or LOG_FORMAT_DATE_DEFAULT


def stdout_format():
    """Returns the log format string for stdout (typically INFO level)."""
    return os.environ.get(LOG_FORMAT_STDOUT_ENV_NAME, None) or LOG_FORMAT_DEFAULT


def stderr_format():
    """Returns the log format string for stderr (non-INFO levels)."""
    return os.environ.get(LOG_FORMAT_STDERR_ENV_NAME, None) or LOG_FORMAT_DEFAULT
