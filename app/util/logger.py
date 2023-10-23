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

    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create base logger
    logger = logging.getLogger(log_id)
    return logger
