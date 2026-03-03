import logging

# centralized logging configuration
LOG_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(message)s"

logging.basicConfig(
    format=LOG_FORMAT,
    level=logging.INFO,
)

# helper to get a logger with request_id support

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    return logger
