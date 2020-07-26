"""
db_contacts.py - Class for access our persistent data store for contacts.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import json  # noqa
import os
from pymongo import ASCENDING
from bson.objectid import ObjectId

from util.logger import get_logger
from util.database import Database, normalize_telephone_number
try:
    DB_URL = os.environ["DB_URL"]
except KeyError as e:
    get_logger('db_admins').fatal(
            "Database connection string environment variable is not set: %s",
            str(e))
    exit()

COLLECTION_NAME = 'contacts'


class DbContacts(Database):
    """
    Encapsulates a database accessor for contacts
    """
    def get_one(self, id: str) -> dict:
        """
        Return a contact record given an ID.

        Args:
            id (str): The mongodb ID of the contact to retrieve
        Returns:
            (dict): The located document or None
        """
        filter_ = {'_id': ObjectId(id)}
        document = self.dbconn[COLLECTION_NAME].find_one(filter_)
        return document

    def get_list(self, email: str, where: dict = {}, page_num: int = 1, page_size: int = 25) -> list:
        """
        Retrieve a list of contacts viewable by this admin user.
        This method supports pagination.

        Args:
            email (str): Email address of admin user.
            where (dict): Filter
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=25)
        Returns:
            (list): List of documents from 'contacts' or None
        """

        skips = page_size * (page_num - 1)

        order_by = [
            ('name.last_name', ASCENDING),
            ('name.first_name', ASCENDING),
            ('organization', ASCENDING)
        ]

        contacts = self.dbconn[COLLECTION_NAME].find(where).sort(order_by).skip(skips).limit(page_size)

        if not contacts:
            return None

        return list(contacts)

    def search(self, email: str, query: str, page_num: int = 1, page_size: int = 25) -> list:
        """
        Search for contacts matching the words in *query*.

        Args:
            email (str): Email of user performing the search.
            query (str): Query string from user
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=25)
        Returns:
            (list): List of docs or None
        """
        search_fields = [
            'name.first_name',
            'name.last_name',
            'name.middle_name',
            'name.suffix',
            'organization',
            'job_title',
            'email',
            'office_phone',
            'cell_phone',
            'address.street',
            'address.city']
        search_words = query.split()
        conditions = []
        for search_field in search_fields:
            for search_word in search_words:
                regex = f'.*{search_word}.*'
                conditions.append({search_field: {'$regex': regex, '$options': 'i'}})

        where = {'$or': conditions}

        return self.get_list(
            email=email,
            where=where,
            page_num=page_num,
            page_size=page_size
        )

    def save(self, email: str, doc: dict) -> dict:
        """
        Save a contact record
        """
        # Determine client name for status message
        contact_name = f"{doc['name']['first_name']} {doc['name']['middle_name']} {doc['name']['last_name']} {doc['name']['suffix']}"
        contact_name = ' '.join(contact_name.split())

        # Cleanup telephone numbers
        phone_number_fields = ['office_phone', 'cell_phone', 'fax']
        for field in phone_number_fields:
            if field in doc:
                doc[field] = normalize_telephone_number(doc[field])

        # Cleanup email
        if 'email' in doc:
            doc['email'] = doc['email'].strip().lower()

        # Insert new contact record
        if doc['_id'] == '0':
            del doc['_id']

            result = self.dbconn[COLLECTION_NAME].insert_one(doc)
            if result.inserted_id:
                message = f"Contact record added for {contact_name}"
                return {'success': True, 'message': message}
            message = "Failed to add new contact record"
            return {'success': False, 'message': message}

        # Update existing contact record
        filter_ = {'_id': ObjectId(doc['_id'])}
        del doc['_id']
        result = self.dbconn[COLLECTION_NAME].update_one(filter_, {'$set': doc})
        if result.modified_count == 1:
            message = f"{contact_name}'s record updated"
            return {'success': True, 'message': message}

        message = f"No updates applied to {contact_name}'s record ({result.modified_count})"
        return {'success': False, 'message': message}
