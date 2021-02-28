"""
db_client_discovery.py - Class for access our persistent data store for client discovery.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2021 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from datetime import datetime
import json  # noqa
from pymongo import DESCENDING
from bson.objectid import ObjectId

from util.database import Database

DB_NAME = 'discoverybot'
COLLECTION_NAME = 'discovery_requests'


class DbClientDiscovery(Database):
    def __init__(self):
        super().__init__(DB_NAME)
    """
    Encapsulates a database accessor for client notes
    """
    def get_one(self, id: str) -> dict:
        """
        Return a notes record given an ID.

        Args:
            id (str): The mongodb ID of the note document to retrieve
        Returns:
            (dict): The located document or None
        """
        filter_ = {'_id': ObjectId(id)}
        document = self.dbconn[COLLECTION_NAME].find_one(filter_)
        return document

    def get_list(self, email: str, clients_id: str, where: dict = None, page_num: int = 1, page_size: int = 25) -> list:
        """
        Retrieve a list of discovery requests viewable by this admin user.
        This method supports pagination.

        Args:
            email (str): Email address of admin user.
            clients_id (str): ID of client for whom to retrieve discovery requests
            where (dict): Filter
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=25)
        Returns:
            (list): List of documents from 'discovery_requests' or None
        """

        skips = page_size * (page_num - 1)

        order_by = [
            ('time', DESCENDING)
        ]

        if where:
            filter_ = {
                '$and': [
                    where,
                    {'client_id': ObjectId(clients_id)}
                ]
            }
        else:
            filter_ = {'client_id': ObjectId(clients_id)}

        discovery = self.dbconn[COLLECTION_NAME].find(filter_).sort(order_by).skip(skips).limit(page_size)

        if not discovery:
            return None

        return list(discovery)

    def has_any(self, clients_id: str) -> bool:
        """
        See if there are any discovery requests for this client. This is used in rendering the UI.

        Args:
            clients_id (str): ID of client for whom we are to check for discovery requests.
        
        Returns:
            (bool): True if there are discovery requests; otherwise False
        """
        discovery_requests = self.dbconn[COLLECTION_NAME].find_one({'client_id': ObjectId(clients_id)})
        if discovery_requests:
            return True
        return False

    def save(self, email: str, doc: dict) -> dict:
        """
        Save a discovery request record
        """
        doc['client_id'] = ObjectId(doc['clients_id'])
        doc['last_editor'] = email
        doc['last_edit_date'] = datetime.now()

        # Insert new discovery request record
        if doc['_id'] == '0':
            del doc['_id']
            doc['created_by'] = email
            doc['created_date'] = datetime.now()

            result = self.dbconn[COLLECTION_NAME].insert_one(doc)
            if result.inserted_id:
                message = "Discovery requests added"
                return {'success': True, 'message': message}
            message = "Failed to add new discovery request"
            return {'success': False, 'message': message}

        # Update existing discovery request record
        filter_ = {'_id': ObjectId(doc['_id'])}
        del doc['_id']
        result = self.dbconn[COLLECTION_NAME].update_one(filter_, {'$set': doc})
        if result.modified_count == 1:
            message = "Discovery request updated"
            return {'success': True, 'message': message}

        message = f"Discovery request did not update ({result.modified_count})"
        return {'success': False, 'message': message}
