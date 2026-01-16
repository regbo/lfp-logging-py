# lfp-logging

A simple, zero-dependency logging utility for Python that provides lazy-initialization and automatic configuration.

## Features

- **Zero Dependencies**: Built entirely on the Python standard library.
- **Lazy Initialization**: Logging is only configured when the first log message is actually handled. It uses a patching mechanism that stays out of the way until a log is emitted.
- **Automatic Name Discovery**: Automatically determines logger names based on the caller's class, module, or file name.
- **Smart Default Handlers**:
  - `INFO` messages are sent to `stdout` for clean output.
  - All other levels (`DEBUG`, `WARNING`, `ERROR`, `CRITICAL`) are sent to `stderr` with detailed formatting.
- **Explicit Override Support**: If you call `logging.basicConfig()` yourself, `lfp-logging` will automatically back off and let your configuration take priority.
- **Flexible Configuration**: Supports configuration via environment variables or system arguments.

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
from lfp_logging.logs import logger

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

The logging level and formats can be controlled using environment variables or command-line arguments.

### Environment Variables

- `LOG_LEVEL`: Set the global log level. Accepts names (e.g., `DEBUG`, `INFO`) or numeric values (e.g., `10`, `20`).
- `LOG_FORMAT_DATE`: Custom date format (default: `%Y-%m-%d %H:%M:%S`).
- `LOG_FORMAT_STDOUT`: Custom format for stdout (INFO messages).
- `LOG_FORMAT_STDERR`: Custom format for stderr (all other messages).

### System Arguments

- `--log-level`: Set the log level via command line (e.g., `python app.py --log-level 10`). This takes precedence over environment variables.

## Development

This project uses `uv` for dependency management and `pytest` for testing.

### Running Tests

```bash
uv run pytest
```
