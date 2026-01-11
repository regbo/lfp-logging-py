import logging
from unittest.mock import MagicMock, patch

from lfp_logging.logs import (
    LogLevel,
    _LazyLogger,
    _parse_bool,
    _parse_log_level_environ,
    _parse_log_level_sys_args,
    log_level,
    logger,
)


def test_log_level_class():
    """Test the LogLevel container class."""
    ll = LogLevel("INFO", 20)
    assert ll.name == "INFO"
    assert ll.level == 20
    assert str(ll) == "INFO"
    assert repr(ll) == "LogLevel(name='INFO', level=20)"


def test_log_level_parsing():
    """Test the log_level parsing function."""
    # Test valid string levels
    info = log_level("INFO")
    assert info.name == "INFO"
    assert info.level == logging.INFO

    # Test valid integer levels
    debug = log_level(10)
    assert debug.name == "DEBUG"
    assert debug.level == logging.DEBUG

    # Test numeric strings
    warning = log_level("30")
    assert warning.name == "WARNING"
    assert warning.level == logging.WARNING

    # Test custom mapping or aliases
    warn = log_level("WARNING")
    assert warn.name == "WARNING"
    assert warn.level == logging.WARNING

    # Test "warn" alias and case insensitivity
    warn_alias = log_level("warn")
    assert warn_alias.level == logging.WARNING
    assert warn_alias.name == "WARN"

    # Test case insensitivity for other levels
    info_case = log_level("iNfO")
    assert info_case.name == "INFO"
    assert info_case.level == logging.INFO

    # Test invalid levels
    assert log_level("INVALID") is None
    assert log_level(None) is None
    assert log_level(999) is None


def test_parse_bool():
    """Test the _parse_bool helper function."""
    assert _parse_bool(True) is True
    assert _parse_bool(False) is False
    assert _parse_bool("true") is True
    assert _parse_bool("off") is False
    assert _parse_bool("1") is True
    assert _parse_bool("0") is False
    assert _parse_bool(None) is None
    assert _parse_bool("invalid") is None


def test_logger_explicit_name():
    """Test creating a logger with an explicit name."""
    my_logger = logger("test_logger")
    assert isinstance(my_logger, _LazyLogger)
    assert my_logger.name == "test_logger"


def test_logger_auto_name():
    """Test automatic logger name discovery."""
    # Test discovery from a module
    my_logger = logger()
    # It should be tests.test_logs because it takes stem and parent name
    assert my_logger.name == "tests.test_logs"


class SampleClass:
    def get_logger(self):
        return logger()


def test_logger_auto_name_class():
    """Test automatic logger name discovery from within a class."""
    obj = SampleClass()
    my_logger = obj.get_logger()
    # If it fails to get SampleClass, it falls back to tests.test_logs
    # We want to see if it can get SampleClass
    assert my_logger.name == "SampleClass"


@patch("lfp_logging.logs._logging_basic_config")
def test_lazy_logger_initialization(mock_config):
    """Test that _LazyLogger triggers configuration on first log."""
    from lfp_logging import logs

    logs._INIT_COMPLETE = False

    l = _LazyLogger("test_lazy")
    assert l._handler is None

    # Mock the internal handler to avoid real logging side effects
    with patch("logging.getLogger") as mock_get_logger:
        mock_handler = MagicMock()
        mock_get_logger.return_value = mock_handler

        # Create a record and handle it
        record = logging.LogRecord(
            "test_lazy", logging.INFO, "path", 1, "msg", None, None
        )
        l.handle(record)

        # Verify basic config was called
        mock_config.assert_called_once()
        # Verify it now has a handler and called its handle method
        assert l._handler is not None
        mock_handler.handle.assert_called_once_with(record)


@patch("logging.basicConfig")
@patch("os.environ.get")
def test_logging_basic_config_call(mock_env_get, mock_basic_config):
    """Test the internal _logging_basic_config function."""
    from lfp_logging import logs

    # Reset the initialization state for the test
    logs._INIT_COMPLETE = False

    # Mock environment variables
    mock_env_get.side_effect = lambda key, default: {
        "LOG_LEVEL": "DEBUG",
        "LOG_LEVEL_PARSE_ENVIRON": "true",
    }.get(key, default)

    logs._logging_basic_config()

    # Verify basicConfig was called with expected level
    mock_basic_config.assert_called_once()
    args, kwargs = mock_basic_config.call_args
    assert kwargs["level"] == logging.DEBUG
    assert len(kwargs["handlers"]) == 2


@patch("os.environ.get")
def test_parse_log_level_environ_disabled(mock_env_get):
    """Test that LOG_LEVEL is ignored when LOG_LEVEL_PARSE_ENVIRON is false."""
    mock_env_get.side_effect = lambda key, default=None: {
        "LOG_LEVEL": "DEBUG",
        "LOG_LEVEL_PARSE_ENVIRON": "false",
    }.get(key, default)

    assert _parse_log_level_environ() is None


@patch("os.environ.get")
def test_parse_log_level_sys_args_disabled(mock_env_get):
    """Test that sys args are ignored when LOG_LEVEL_PARSE_SYS_ARGS is false."""
    mock_env_get.side_effect = lambda key, default=None: {
        "LOG_LEVEL_PARSE_SYS_ARGS": "false",
    }.get(key, default)

    with patch("sys.argv", ["script.py", "--log-level", "DEBUG"]):
        assert _parse_log_level_sys_args() is None
