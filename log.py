import logging
from logging.handlers import RotatingFileHandler


def setup_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Ротация логов (не более 5 файлов по 2MB каждый)
    file_handler = RotatingFileHandler(
        'app.log', maxBytes=2 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Вывод в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()
