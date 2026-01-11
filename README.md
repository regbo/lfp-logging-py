# lfp-logging

A simple, zero-dependency logging utility for Python that provides lazy-initialization and automatic configuration.

## Features

- **Zero Dependencies**: Built entirely on the Python standard library.
- **Lazy Initialization**: Logging is only configured when the first log message is actually handled. Subsequent calls to `logger()` after initialization return standard `logging.Logger` instances.
- **Automatic Name Discovery**: Automatically determines logger names based on the caller's class or module.
- **Smart Default Handlers**:
  - `INFO` messages are sent to `stdout` for clean output.
  - All other levels (`DEBUG`, `WARNING`, `ERROR`, `CRITICAL`) are sent to `stderr` with detailed formatting including timestamps, levels, and line numbers.
- **Flexible Configuration**: Supports log level configuration via environment variables or system arguments.

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

# Or specify a name explicitly
log = logger("my_app")
log.info("Hello World!")
```

## Configuration

The logging level can be controlled using environment variables or command-line arguments.

### Environment Variables

- `LOG_LEVEL`: Set the global log level. Accepts names (e.g., `DEBUG`, `INFO`) or numeric values (e.g., `10` for DEBUG, `20` for INFO).
- `LOG_LEVEL_PARSE_ENVIRON`: Set to `false` to disable parsing the `LOG_LEVEL` environment variable.

### System Arguments

- `--log-level`: Set the log level via command line. Accepts names (e.g., `DEBUG`) or numeric values (e.g., `10`). Example: `python app.py --log-level 10`.
- `LOG_LEVEL_PARSE_SYS_ARGS`: Set this environment variable to `false` to disable parsing system arguments.

## Development

This project uses `uv` for dependency management and `pytest` for testing.

### Running Tests

```bash
uv run pytest
```
