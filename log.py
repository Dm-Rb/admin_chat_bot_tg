import logging
from logging.handlers import RotatingFileHandler


def setup_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Log rotation (maximum 5 files, 2MB each)
    file_handler = RotatingFileHandler(
        'app.log', maxBytes=2 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)

    # output to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()
