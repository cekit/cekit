import logging
import os
import sys

# CentOS 7 does not have colorlog RPM for Python3
no_color = False
try:
    import colorlog
except ImportError:
    no_color = True


# Source: http://stackoverflow.com/questions/1383254/logging-streamhandler-and-standard-streams
# Adjusted
class SingleLevelFilter(logging.Filter):
    def __init__(self, passlevel, reject):
        self.passlevel = passlevel
        self.reject = reject

    def filter(self, record):
        if self.reject:
            return record.levelno > self.passlevel
        else:
            return record.levelno <= self.passlevel


def setup_logging(color=True):
    handler_out = logging.StreamHandler(sys.stdout)
    handler_err = logging.StreamHandler(sys.stderr)

    handler_out.addFilter(SingleLevelFilter(logging.INFO, False))
    handler_err.addFilter(SingleLevelFilter(logging.INFO, True))

    if no_color or not color or os.environ.get("NO_COLOR"):
        formatter = logging.Formatter(
            "%(asctime)s %(filename)s:%(lineno)-10s %(levelname)-5s %(message)s"
        )
    else:
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s %(filename)s:%(lineno)-10s %(levelname)-5s %(message)s"
        )

    handler_out.setFormatter(formatter)
    handler_err.setFormatter(formatter)

    logger = logging.getLogger("cekit")
    # Reset all handlers
    logger.handlers = []
    logger.addHandler(handler_out)
    logger.addHandler(handler_err)

    for package in ["pykwalify.rule"]:
        log = logging.getLogger(package)
        log.setLevel(logging.INFO)
