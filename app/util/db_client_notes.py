"""
db_client_notes.py - Class for access our persistent data store for client notes.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from datetime import datetime
import json  # noqa
from pymongo import ASCENDING
from bson.objectid import ObjectId

from util.database import Database

COLLECTION_NAME = 'notes'


class DbClientNotes(Database):
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

    def get_list(self, email: str, clients_id: str, where: dict = {}, page_num: int = 1, page_size: int = 25) -> list:
        """
        Retrieve a list of notes viewable by this admin user.
        This method supports pagination.

        Args:
            email (str): Email address of admin user.
            clients_id (str): ID of client for whom to retrieve notes
            where (dict): Filter
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=25)
        Returns:
            (list): List of documents from 'notes' or None
        """

        skips = page_size * (page_num - 1)

        order_by = [
            ('created_date', ASCENDING)
        ]

        where = {
            '$and': [
                where,
                {'client_id': ObjectId(clients_id)}
            ]
        }

        contacts = self.dbconn[COLLECTION_NAME].find(where).sort(order_by).skip(skips).limit(page_size)

        if not contacts:
            return None

        return list(contacts)

    def search(self, email: str, clients_id: str, query: str, page_num: int = 1, page_size: int = 25) -> list:
        """
        Search for notes matching the words in *query*.

        Args:
            email (str): Email of user performing the search.
            clients_id (str): ID of client for whom to retrieve notes
            query (str): Query string from user
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=25)
        Returns:
            (list): List of docs or None
        """
        search_fields = [
            'text',
            'tags']
        search_words = query.split()
        conditions = []
        for search_field in search_fields:
            for search_word in search_words:
                regex = f'.*{search_word}.*'
                conditions.append({search_field: {'$regex': regex, '$options': 'i'}})

        where = {'$or': conditions}

        return self.get_list(
            email=email,
            clients_id=clients_id,
            where=where,
            page_num=page_num,
            page_size=page_size
        )

    def save(self, email: str, doc: dict) -> dict:
        """
        Save a notes record
        """
        doc['clients_id'] = ObjectId(doc['clients_id'])
        doc['last_editor'] = email
        doc['last_edit_date'] = datetime.now()

        # Insert new contact record
        if doc['_id'] == '0':
            del doc['_id']
            doc['created_by'] = email
            doc['created_date'] = datetime.now()

            result = self.dbconn[COLLECTION_NAME].insert_one(doc)
            if result.inserted_id:
                message = "Note added"
                return {'success': True, 'message': message}
            message = "Failed to add new note"
            return {'success': False, 'message': message}

        # Update existing contact record
        filter_ = {'_id': ObjectId(doc['_id'])}
        del doc['_id']
        result = self.dbconn[COLLECTION_NAME].update_one(filter_, {'$set': doc})
        if result.modified_count == 1:
            message = "Note updated"
            return {'success': True, 'message': message}

        message = f"Note did not update ({result.modified_count})"
        return {'success': False, 'message': message}
