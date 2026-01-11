import logging
from typing import Any

"""
This module provides utilities for parsing and representing logging levels.
It includes a LogLevel container and a robust parsing function that handles
integers, strings, and numeric strings with support for defaults.
"""

_UNSET = object()


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


def get(value: Any, default_value: str | int | None = _UNSET) -> LogLevel | None:
    """
    Converts a given value into a LogLevel object.

    Args:
        value: The value to convert. Can be an integer, a string name, or
            a numeric string.
        default_value: The value to return if parsing fails. If _UNSET (default),
            raises a ValueError on failure.

    Returns:
        A LogLevel instance if conversion is successful.
    """
    if value is not None:
        if isinstance(value, int):
            level_no = value
            level_name = logging.getLevelName(level_no)
            if isinstance(level_name, str) and level_name and not level_name.startswith("Level "):
                return LogLevel(level_name, level_no)
        else:
            if level_name := str(value):
                level_name = level_name.upper()
                level_no = logging.getLevelName(level_name)
                if isinstance(level_no, int):
                    return LogLevel(level_name, level_no)
                elif level_name.isdigit():
                    return get(int(level_name), default_value)
    if default_value is None:
        return None
    elif default_value is _UNSET:
        raise ValueError(f"{LogLevel.__name__} not found: {value}")
    return get(default_value)


if "__main__" == __name__:
    print(get(logging.INFO))
    print(get("20"))
    print(get("-1", None))
    print(get("-1"))
