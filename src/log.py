import os
import logging

import structlog


def configure_logging():
    logging.basicConfig()
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f"),
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    log_level = {"DEBUG": logging.DEBUG, "INFO": logging.INFO}
    logger = structlog.wrap_logger(logging.getLogger(""))
    logger.setLevel(log_level.get(os.environ.get("LOGLEVEL", 'INFO')))
