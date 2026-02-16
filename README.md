# lfp-logging

A simple, zero-dependency logging utility for Python that provides lazy-initialization and automatic configuration.

## Features

- **Zero Dependencies**: Built entirely on the Python standard library.
- **Lazy Initialization**: Logging is only configured when the first log message is actually handled. It uses a patching mechanism that stays out of the way until a log is emitted.
- **Automatic Name Discovery**: Automatically determines logger names based on the caller's class, module, or file name.
- **Smart Default Handlers**:
  - `INFO` messages are sent to `stderr` (along with all other levels) by default.
  - Detailed formatting including timestamps, levels, and line numbers.
- **ANSI Colors**: Automatic color support for terminals, with overrides for popular IDEs (VSCode, PyCharm) and CI environments.
- **Explicit Override Support**: If you call `logging.basicConfig()` yourself, `lfp-logging` will automatically back off and let your configuration take priority.
- **Flexible Configuration**: Supports configuration via environment variables.

## Installation

You can install `lfp-logging` directly from GitHub using `pip`:

```bash
pip install git+https://github.com/regbo/lfp-logging-py.git
```

Or add it to your `pyproject.toml` dependencies:

```toml
dependencies = [
    "lfp_logging @ git+https://github.com/regbo/lfp-logging-py.git"
]
```

## Quick Start

```python
from lfp_logging import logger

# The logger name is automatically discovered as the class name "MyService"
class MyService:
    def __init__(self):
        self.log = logger()
    
    def do_something(self):
        self.log.info("Starting task...")
        self.log.warning("Something might be wrong.")

# You can specify one or more potential names. 
# The first valid name (non-empty, not "__main__") will be used.
log = logger(None, "__main__", "my_app")
log.info("Hello World!") # Uses "my_app"
```

## Configuration

The logging level and formats can be controlled using environment variables.

### Environment Variables

- `LOG_LEVEL`: Set the global log level. Accepts names (e.g., `DEBUG`, `INFO`) or numeric values (e.g., `10`, `20`).
- `LOG_FORMAT`: Custom log format string (standard Python logging format).
- `LOG_FORMAT_DATE`: Custom date format (default: `%Y-%m-%d %H:%M:%S`).
- `LOG_FORMAT_COLOR`: Global ANSI color code for all levels.
- `LOG_FORMAT_COLOR_<LEVEL>`: Level-specific ANSI color code (e.g., `LOG_FORMAT_COLOR_DEBUG`).
- `LOG_CONFIG_LAZY`: Defer logging configuration until the first log message is emitted (default: `false`). Set to `true`, `1`, `yes`, or `on` to enable.

### System Arguments

The `--log-level` argument is no longer supported directly by the core configuration, but can be implemented by the user by setting the `LOG_LEVEL` environment variable before the first log call.

## Development

This project uses `uv` for dependency management and `pytest` for testing.

### Running Tests

```bash
uv run pytest
```
