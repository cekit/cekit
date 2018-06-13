import logging
import sys

import colorlog


# Source: http://stackoverflow.com/questions/1383254/logging-streamhandler-and-standard-streams
# Adjusted
class SingleLevelFilter(logging.Filter):
    def __init__(self, passlevel, reject):
        self.passlevel = passlevel
        self.reject = reject

    def filter(self, record):
        if self.reject:
            return (record.levelno > self.passlevel)
        else:
            return (record.levelno <= self.passlevel)


def setup_logging():
    handler_out = logging.StreamHandler(sys.stdout)
    handler_err = logging.StreamHandler(sys.stderr)

    handler_out.addFilter(SingleLevelFilter(logging.INFO, False))
    handler_err.addFilter(SingleLevelFilter(logging.INFO, True))

    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

    handler_out.setFormatter(formatter)
    handler_err.setFormatter(formatter)

    logger = logging.getLogger("cekit")
    logger.addHandler(handler_out)
    logger.addHandler(handler_err)

    for package in ["pykwalify.rule"]:
        log = logging.getLogger(package)
        log.setLevel(logging.INFO)
