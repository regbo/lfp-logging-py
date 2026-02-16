import logging
import os

from lfp_logging import log_level, logs

if __name__ == "__main__":
    os.environ["LOG_LEVEL"] = "DEBUG"
    LOG = logs.logger(__name__)
    for k, _ in logging.getLevelNamesMapping().items():
        level = log_level.get(k)
        LOG.log(level.level, f"Test output {k}")
