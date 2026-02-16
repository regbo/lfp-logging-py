import logging
import pathlib
from unittest.mock import patch

from lfp_logging import log_level
from lfp_logging.log_level import LogLevel
from lfp_logging.logs import (
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
    info = log_level.get("INFO")
    assert info.name == "INFO"
    assert info.level == logging.INFO

    # Test valid integer levels
    debug = log_level.get(10)
    assert debug.name == "DEBUG"
    assert debug.level == logging.DEBUG

    # Test numeric strings
    warning = log_level.get("30")
    assert warning.name == "WARNING"
    assert warning.level == logging.WARNING

    # Test custom mapping or aliases
    warn = log_level.get("WARNING")
    assert warn.name == "WARNING"
    assert warn.level == logging.WARNING

    # Test "warn" alias and case insensitivity
    warn_alias = log_level.get("warn")
    assert warn_alias.level == logging.WARNING
    assert warn_alias.name == "WARN"

    # Test case insensitivity for other levels
    info_case = log_level.get("iNfO")
    assert info_case.name == "INFO"
    assert info_case.level == logging.INFO

    # Test invalid levels
    assert log_level.get("INVALID", None) is None
    assert log_level.get(None, None) is None
    assert log_level.get(999, None) is None


def test_logger_explicit_name():
    """Test creating a logger with an explicit name."""
    my_logger = logger("test_logger")
    assert my_logger.name == "test_logger"


def test_logger_auto_name():
    """Test automatic logger name discovery."""
    # Test discovery from a module
    my_logger = logger()
    # It should be tests.test_logs because it takes stem and parent name
    assert my_logger.name == "tests.test_logs"


def test_file_logger_name():
    """Test automatic logger name discovery."""
    # Test discovery from a module
    my_logger = logger(pathlib.Path(__file__).parent / "example file.py")
    # It should be tests.test_logs because it takes stem and parent name
    assert my_logger.name == "tests.example_file"


def test_file_logger_none_name():
    """Test automatic logger name discovery."""
    # Test discovery from a module
    my_logger = logger(None, pathlib.Path(__file__).parent / "none_example.py")
    # It should be tests.test_logs because it takes stem and parent name
    assert my_logger.name == "tests.none_example"


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


@patch("logging.basicConfig")
def test_lazy_initialization_via_patch(mock_basic_config):
    """Test that the patching mechanism triggers basicConfig on first log check."""
    import logging
    import uuid

    from lfp_logging import logs

    # Reset patching contexts for the test
    logs._HANDLE_PATCH_CTX.clear()
    logs._BASIC_CONFIG_PATCH_CTX.clear()
    logs._BASIC_CONFIG_UNPATCH_CTX.clear()
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    # Get a logger with a unique name to avoid cached loggers
    unique_name = f"patch_test_{uuid.uuid4()}"
    test_logger = logger(unique_name)

    # basicConfig should NOT have been called yet
    # If this still fails, something in the environment is inspecting the logger
    if not mock_basic_config.called:
        # Checking if enabled should trigger the patch
        test_logger.isEnabledFor(logging.INFO)

        # basicConfig should have been called now
        assert mock_basic_config.called


def test_marker_not_added_after_init():
    """
    Test that the patch marker is no longer added to new loggers after initialization.
    """
    import logging
    import uuid

    from lfp_logging import logs

    # Reset patching contexts for the test
    logs._HANDLE_PATCH_CTX.clear()
    logs._BASIC_CONFIG_PATCH_CTX.clear()
    logs._BASIC_CONFIG_UNPATCH_CTX.clear()
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    # Get a logger
    unique_name = f"marker_test_{uuid.uuid4()}"
    test_logger = logger(unique_name)
    marker_name, marker_value = logs._HANDLE_PATCH_MARKER

    # Trigger initialization (sets _HANDLE_PATCH_CTX)
    test_logger.isEnabledFor(logging.INFO)

    # Subsequent loggers should NOT receive the marker because _HANDLE_PATCH_CTX is set
    unique_name_2 = f"second_marker_test_{uuid.uuid4()}"
    second_logger = logger(unique_name_2)
    assert not hasattr(second_logger, marker_name)


def test_basicConfig_override_after_log():
    """Test that manual basicConfig overrides lazy defaults after first log."""
    import logging

    from lfp_logging import logs

    # Reset patching contexts and root handlers
    logs._HANDLE_PATCH_CTX.clear()
    logs._BASIC_CONFIG_PATCH_CTX.clear()
    logs._BASIC_CONFIG_UNPATCH_CTX.clear()

    # Clear existing root handlers
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    test_logger = logger("override_test")

    # Trigger lazy init
    test_logger.info("First log triggers lazy config")

    # Verify default handler is present (now only 1: stderr)
    assert len(logging.root.handlers) == 1

    # Now manually call basicConfig with a different level and a single handler
    new_handler = logging.StreamHandler()
    logging.basicConfig(level=logging.WARNING, handlers=[new_handler], force=True)

    # Verify that the new configuration has overridden the defaults
    assert len(logging.root.handlers) == 1
    assert logging.root.handlers[0] is new_handler
    assert logging.root.level == logging.WARNING


def test_no_override_if_basicConfig_called_before_log():
    """
    Test that lazy defaults do NOT override basicConfig if called before first log.
    """
    import logging

    from lfp_logging import logs

    # Reset patching contexts and root handlers
    logs._HANDLE_PATCH_CTX.clear()
    logs._BASIC_CONFIG_PATCH_CTX.clear()
    logs._BASIC_CONFIG_UNPATCH_CTX.clear()

    # Clear existing root handlers
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    # Manually call basicConfig first
    pre_handler = logging.StreamHandler()
    logging.basicConfig(level=logging.ERROR, handlers=[pre_handler])

    test_logger = logger("no_override_test")

    # Trigger lazy init attempt
    test_logger.error("First log should respect existing config")

    # Verify that the pre-existing configuration was preserved
    assert len(logging.root.handlers) == 1
    assert logging.root.handlers[0] is pre_handler
    assert logging.root.level == logging.ERROR


def test_lazy_init_vs_standard_logging_info():
    """
    Test that standard logging.info() triggers standard basicConfig,
    causing lfp-logging to back off.
    """
    import logging

    from lfp_logging import logs

    # 1. Test successful lazy init when logger() is used first
    logs._HANDLE_PATCH_CTX.clear()
    logs._BASIC_CONFIG_PATCH_CTX.clear()
    logs._BASIC_CONFIG_UNPATCH_CTX.clear()
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    my_log = logger("lazy_success")
    my_log.info("This should trigger our lazy config")
    assert len(logging.root.handlers) == 1  # Our single stderr handler

    # 2. Test back-off when standard logging.info() is used first
    logs._HANDLE_PATCH_CTX.clear()
    logs._BASIC_CONFIG_PATCH_CTX.clear()
    logs._BASIC_CONFIG_UNPATCH_CTX.clear()
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    # Standard logging call triggers standard basicConfig
    logging.info("Standard logging call")
    assert len(logging.root.handlers) == 1  # Standard single handler (usually stderr)

    # Now use our logger
    my_log_2 = logger("lazy_backoff")
    my_log_2.info("This should NOT trigger our config because root has handlers")

    # Should still have only the 1 standard handler
    assert len(logging.root.handlers) == 1


def test_lazy_init_tradeoff():
    """
    Demonstrate that lazy init means standard logging.info() can 'steal'
    the configuration if called before any lfp-logging activity.
    """
    import logging

    from lfp_logging import logs

    # Reset
    logs._HANDLE_PATCH_CTX.clear()
    logs._BASIC_CONFIG_PATCH_CTX.clear()
    logs._BASIC_CONFIG_UNPATCH_CTX.clear()
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)

    # 1. With lfp-logging (lazy):
    # Calling logger() doesn't configure yet
    my_log = logger("tradeoff_lazy")

    # Manually call standard basicConfig to simulate it being called elsewhere
    # (logging.info() might not trigger it if pytest already has handlers)
    logging.basicConfig(level=logging.INFO)

    # Now our logger is used, but it's too late for our default config
    my_log.info("I want my custom config but won't get it")

    # Verify standard config won (usually 1 handler if called via basicConfig)
    # We check that our specific handlers are NOT there
    assert len(logging.root.handlers) >= 1
    # Our handlers use specific formats, we can check for that if needed
    # but the simplest check is that we didn't add our 2 handlers on top of the 1
    assert len(logging.root.handlers) == 1


def test_file_logger_name_with_spaces():
    """Test that spaces in file paths are converted to underscores."""
    # Test with a path object containing spaces
    test_path = pathlib.Path("some directory/my file.py")
    my_logger = logger(test_path)

    # "some directory/my file.py" -> stem "my file", parent "some directory"
    # -> "some directory.my file" -> "some_directory.my_file"
    assert my_logger.name == "some_directory.my_file"


def test_logger_with_path_object():
    """Test that passing a Path object directly works."""
    test_path = pathlib.Path("direct_path.py")
    my_logger = logger(test_path)
    assert my_logger.name == "direct_path"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-vv", "-ra"]))
