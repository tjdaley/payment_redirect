"""
db_queue.py - Class for access our task queue collection.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2023 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from datetime import datetime

from util.database import Database
from util.logger import get_logger


COLLECTION_NAME = 'task_queue'


class DbQueue(Database):
    """
    Encapsulates a database accessor for the task queue.
    """
    def __init__(self):
        """
        Class initializer.
        """
        super().__init__(COLLECTION_NAME)
        self.logger = get_logger('db_queue')

    def queue_image_conversion(
            self,
            tmp_folder: str,
            client_id: str,
            user_email: str,
            params: dict
    ) -> dict:
        """
        Queue an image conversion task.
        """
        doc = {
            'task_type': 'image_conversion',
            'tmp_folder': tmp_folder,
            'client_id': client_id,
            'user_email': user_email,
            'params': params,
            'status': 'queued',
            'created': datetime.now(),
        }
        result = self.dbconn[COLLECTION_NAME].insert_one(doc)
        if result.inserted_id:
            return {'success': True, 'message': 'Image conversion task queued'}
        return {'success': False, 'message': 'Failed to queue image conversion task'}
