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
import pandas as pd

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
        try:
            filter_ = {'_id': ObjectId(id)}
            document = self.dbconn[COLLECTION_NAME].find_one(filter_)
        except Exception:
            document = None
        return document

    def get_list(self, email: str, where: dict = {}, page_num: int = 1, page_size: int = 25, client_id: str = None) -> list:
        """
        Retrieve a list of contacts viewable by this admin user.
        This method supports pagination.

        Args:
            email (str): Email address of admin user.
            where (dict): Filter
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=25)
            client_id (str): If provided, will filter for this client_id
        Returns:
            (list): List of documents from 'contacts' or None
        """

        skips = page_size * (page_num - 1)

        order_by = [
            ('name.last_name', ASCENDING),
            ('name.first_name', ASCENDING),
            ('organization', ASCENDING)
        ]

        if where and client_id:
            where = {
                '$and': [
                    where,
                    {'linked_client_ids': {'$elemMatch': {'$eq': ObjectId(client_id)}}}
                ]
            }
        elif where and not client_id:
            pass

        elif client_id and not where:
            where = {'linked_client_ids': {'$elemMatch': {'$eq': ObjectId(client_id)}}}
        else:
            where = {}

        contacts = self.dbconn[COLLECTION_NAME].find(where).sort(order_by).skip(skips).limit(page_size)

        if not contacts:
            return None

        return list(contacts)

    def get_list_as_csv(self, email: str, client_id=None) -> str:
        """
        Return the client list as a CSV string.
        """
        if not client_id:
            client_id = None
        documents = self.get_list(email, client_id=client_id)

        # Break out compound fields into individual columns
        for document in documents:
            name = document.get('name', {})
            for key, value in name.items():
                document[key] = value
            address = document.get('address', {})
            for key, value in address.items():
                document[key] = value

        contacts = _to_dataframe(documents)

        # Drop columns that don't need to be downloaded
        contacts = contacts.drop(
            columns=[
                '_id', 'name', 'address', 'linked_client_ids'
            ])

        # Create and return CSV file.
        csv_export = contacts.to_csv(sep=",")
        return csv_export

    def search(self, email: str, query: str, page_num: int = 1, page_size: int = 25, client_id: str = None) -> list:
        """
        Search for contacts matching the words in *query*.

        Args:
            email (str): Email of user performing the search.
            query (str): Query string from user.
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=25)
            client_id (str): If provided, filter for this one client.
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
            page_size=page_size,
            client_id=client_id
        )

    def save(self, email: str, doc: dict) -> dict:
        """
        Save a contact record
        """
        # Determine client name for status message
        try:
            contact_name = f"{doc['name']['first_name']} {doc['name']['middle_name']} {doc['name']['last_name']} {doc['name']['suffix']}"
            contact_name = ' '.join(contact_name.split())
        except Exception:
            contact_name = "Contact"

        # Cleanup telephone numbers
        phone_number_fields = ['office_phone', 'cell_phone', 'fax']
        for field in phone_number_fields:
            if field in doc:
                doc[field] = normalize_telephone_number(doc[field])

        # Cleanup email
        if 'email' in doc:
            doc['email'] = doc['email'].strip().lower()

        # Insert new contact record
        if doc.get('_id', '0') == '0':
            if '_id' in doc:
                del doc['_id']
            doc['linked_client_ids'] = []

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

    def link(self, email: str, client_id: str, contact_id: str):
        """
        Link a contact to a client.
        """
        contact = self.dbconn[COLLECTION_NAME].find({'_id': ObjectId(contact_id)})
        if not contact:
            return {'success': False, 'message': 'Could not find contact ID'}

        new_doc = {}
        if 'linked_client_ids' not in contact:
            new_doc['linked_client_ids'] = []
        else:
            new_doc['linked_client_ids'] = contact['linked_client_ids']

        cl_id = ObjectId(client_id)
        if cl_id in new_doc['linked_client_ids']:
            return {'success': True, 'message': 'Contact was already linked'}

        new_doc['linked_client_ids'].append(cl_id)
        new_doc['_id'] = contact_id
        result = self.save(email, new_doc)
        if result['success']:
            result['message'] = 'Contact successfully linked'
        return result

    def unlink(self, email: str, client_id: str, contact_id: str):
        """
        Unlink a contact from a client.
        """
        contact = self.dbconn[COLLECTION_NAME].find({'_id': ObjectId(contact_id)})
        if not contact:
            return {'success': False, 'message': 'Could not find contact ID'}

        new_doc = {}
        if 'linked_client_ids' not in contact:
            new_doc['linked_client_ids'] = []
        else:
            new_doc['linked_client_ids'] = contact['linked_client_ids']

        cl_id = ObjectId(client_id)
        if cl_id not in new_doc['linked_client_ids']:
            return {'success': True, 'message': 'Contact was not linked'}

        new_doc['linked_client_ids'].remove(cl_id)
        new_doc['_id'] = contact_id
        result = self.save(email, new_doc)
        if result['success']:
            result['message'] = 'Contact successfully unlinked'
        return result


def _to_dataframe(documents: dict):
    """
    Convert result set to dataframe.
    """
    contacts = pd.DataFrame(columns=[])
    # pylint: disable=unused-variable
    for num, contact in enumerate(documents):
        # pylint: enable=unused-variable
        contact_id = str(contact['_id'])
        contact['_id'] = contact_id
        series_obj = pd.Series(contact, name=contact_id)
        contacts = contacts.append(series_obj)
    return contacts
