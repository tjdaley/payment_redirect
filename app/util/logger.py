# logger.py - Return a logger for this app.
"""
Create a logger for this ap.

Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
import logging
import os
import dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
dotenv.load_dotenv(dotenv_path)


def get_logger(identifier: str = None):
    """
    Instantiate a logger instance.

    Args:
        identifier (str): Sub-identifier for a module's logging [optional]

    Returns:
        Instance of logger
    """
    log_id = os.environ.get('LOG_ID')
    if identifier:
        log_id = f'{log_id}.{identifier}'

    debug = int(os.environ.get('DEBUG', '0'))
    if debug == 1:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create base logger
    logger = logging.getLogger(log_id)
    logger.setLevel(log_level)

    # Inquire where to send log messages
    log_to_file = int(os.environ.get('LOG_TO_FILE', '0')) == 1
    log_to_console = int(os.environ.get('LOG_TO_CONSOLE', '0')) == 1

    # File logger
    if log_to_file:
        log_file_name = os.environ.get('LOG_FILE', 'application.log')
        fh = logging.FileHandler(log_file_name)
        fh.setLevel(log_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # Console logger
    if log_to_console:
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger
