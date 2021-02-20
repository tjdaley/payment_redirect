"""
db_clients_contacts.py - Class to access the clients/contacts intersection collection.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2021 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from datetime import datetime
import json  # noqa
from pymongo import ASCENDING
from bson.objectid import ObjectId

from util.database import Database
from util.db_clients import DbClients
from util.db_contacts import DbContacts

COLLECTION_NAME = 'clients_contacts'


class DbClientsContacts(Database):
    """
    Encapsulates a database accessor for clients_contacts
    """
    DBCLIENTS = DbClients()
    DBCONTACTS = DbContacts()

    permitted_cols = [
        'clients_id', 'contacts_id', 'email_cc', 'role', 'notes',
        'last_editor', 'last_edit_date',
        'created_by', 'created_date',
        'active'
    ]

    def get_one(self, id: str) -> dict:
        """
        Return a client contact record given an ID.

        Args:
            id (str): The mongodb ID of the client/contact document to retrieve
        Returns:
            (dict): The located document or None
        """
        filter_ = {'_id': ObjectId(id)}
        document = self.dbconn[COLLECTION_NAME].find_one(filter_)
        if document:
            client = DbClientsContacts.DBCLIENTS.get_one(document['clients_id'])
            document['_client'] =  client
            contact = DbClientsContacts.DBCONTACTS.get_one(document['contacts_id'])
            document['_contact'] = contact
        return document

    def get_list(self, email: str, clients_id: str, where: dict = None, page_num: int = 1, page_size: int = 50) -> list:
        """
        Retrieve a list of client/contacts viewable by this admin user.
        This method returns contacts by case. For cases by contact, call get_clients()
        This method supports pagination.

        Args:
            email (str): Email address of admin user.
            clients_id (str): ID of client for whom to retrieve contacts
            where (dict): Filter
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=50)
        Returns:
            (list): List of documents from 'clients_contacts' or None
        """

        skips = page_size * (page_num - 1)

        order_by = [
            ('contact_sort', ASCENDING)
        ]

        if where:
            filter_ = {
                '$and': [
                    where,
                    {'clients_id': ObjectId(clients_id)},
                    {'active': True}
                ]
            }
        else:
            filter_ = {'clients_id': ObjectId(clients_id), 'active': True}

        contacts = self.dbconn[COLLECTION_NAME].find(filter_).sort(order_by).skip(skips).limit(page_size)

        if not contacts:
            return None
        contacts = list(contacts)

        # Join the two tables.
        # The underscore indicates that the data in that column are read-only
        for contact in contacts:
            _client = DbClientsContacts.DBCLIENTS.get_one(contact['clients_id'])
            contact['_client'] =  _client
            _contact = DbClientsContacts.DBCONTACTS.get_one(contact['contacts_id'])
            contact['_contact'] = _contact
            if contact.get('email_cc', None) is None:
                contact['email_cc'] = _contact.get('email_cc', '')

        return list(contacts)

    def get_clients(self, email: str, contacts_id: str, where: dict = None, page_num: int = 1, page_size: int = 50) -> list:
        """
        Retrieve a list of client/contacts viewable by this admin user.
        This method returns cases by contact. For contacts by case, call get_list()
        This method supports pagination.

        Args:
            email (str): Email address of admin user.
            contacts_id (str): ID of contact for whom to retrieve clients
            where (dict): Filter
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=50)
        Returns:
            (list): List of documents from 'clients_contacts' or None
        """

        skips = page_size * (page_num - 1)

        order_by = [
            ('client_sort', ASCENDING)
        ]

        if where:
            filter_ = {
                '$and': [
                    where,
                    {'contacts_id': ObjectId(contacts_id)}
                ]
            }
        else:
            filter_ = {'contacts_id': ObjectId(contacts_id)}

        contacts = self.dbconn[COLLECTION_NAME].find(filter_).sort(order_by).skip(skips).limit(page_size)

        if not contacts:
            return None

        # Join the two tables.
        # The underscore indicates that the data in that column are read-only
        for contact in contacts:
            client = DbClientsContacts.DBCLIENTS.get_one(contact['clients_id'])
            contact['_client'] =  client
            contact = DbClientsContacts.DBCONTACTS.get_one(contact['contacts_id'])
            contact['_contact'] = contact

        contacts = list(contacts)

    def has_any(self, clients_id: str) -> bool:
        """
        See if there are any contacts for this client. This is used in rendering the UI.

        Args:
            clients_id (str): ID of client for whom we are to check for contacts.

        Returns:
            (bool): True if there are notes; otherwise False
        """
        notes = self.dbconn[COLLECTION_NAME].find_one({'clients_id': ObjectId(clients_id)})
        if notes:
            return True
        return False

    def unlink(self, email: str, clients_id: str, contacts_id: str) -> bool:
        """
        Mark a clients_contacts intersection record as inactive.

        Args:
            email (str): Email of user requesting the unlink.
            clients_id (str): Clients_ID to be unlinked
            contacts_id (str): Contacts_ID to be unlinked

        Returns:
            (bool): True if successful, otherwise False
        """
        filter_ = {
            'clients_id': ObjectId(clients_id),
            'contacts_id': ObjectId(contacts_id)
        }
        result = self.dbconn[COLLECTION_NAME].update_one(filter_, {'$set': {'active': False}})
        return result.modified_count == 1

    def relink(self, email: str, clients_id: str, contacts_id: str) -> bool:
        """
        Mark a clients_contacts intersection record as active.

        Args:
            email (str): Email of user requesting the unlink.
            clients_id (str): Clients_ID to be unlinked
            contacts_id (str): Contacts_ID to be unlinked

        Returns:
            (bool): True if successful, otherwise False
        """
        filter_ = {
            'clients_id': ObjectId(clients_id),
            'contacts_id': ObjectId(contacts_id)
        }
        result = self.dbconn[COLLECTION_NAME].update_one(filter_, {'$set': {'active': True}})
        return result.modified_count == 1

    def was_linked(self, clients_id: str, contacts_id: str) -> bool:
        """
        Check is a contact is or was ever linked linked to a client.

        Args:
            clients_id (str): Clients_ID to be queried
            contacts_id (str): Contacts_ID to be queried

        Returns:
            (bool): True if linked now or in the past, otherwise False
        """
        filter_ = {
            'clients_id': ObjectId(clients_id),
            'contacts_id': ObjectId(contacts_id)
        }
        doc_count = self.dbconn[COLLECTION_NAME].count_documents(filter_)
        print("@@@ Doc Count", doc_count, filter_)
        return doc_count != 0

    def save(self, email: str, unfiltered_doc: dict) -> dict:
        """
        Save a clients_contacts record
        """
        # Perseve string versions for is_linked and relink functions
        clients_id_str = unfiltered_doc['clients_id']
        contacts_id_str = unfiltered_doc['contacts_id']

        # Convert IDs to a saveable format and note who requested this insert/update
        unfiltered_doc['clients_id'] = ObjectId(unfiltered_doc['clients_id'])
        unfiltered_doc['contacts_id'] = ObjectId(unfiltered_doc['contacts_id'])
        unfiltered_doc['last_editor'] = email
        unfiltered_doc['last_edit_date'] = datetime.now()
        _id = unfiltered_doc.get('_id', '0')

        # Remove read-only and junk fields.
        # In non-intersection collections, we let the application grow the documents in
        # the collection as it wants, taking advantage of the non-prescriptive nature of
        # the no-sql database. Here, we're trying to keep an intersection table from
        # denormalizing the database to the point that we lose track of ground-truth.
        doc = {k:unfiltered_doc[k] for k in DbClientsContacts.permitted_cols if k in unfiltered_doc}

        # Default to active when linking in a new contact
        if 'active' not in doc:
            doc['active'] = True

        # Now add some sort hints for retrieval
        client = DbClientsContacts.DBCLIENTS.get_one(doc['clients_id'])
        contact = DbClientsContacts.DBCONTACTS.get_one(doc['contacts_id'])
        doc['client_sort'] = _sort_hint(client['name'])
        doc['contact_sort'] = _sort_hint(contact['name'])

        # Insert new clients_contacts record
        if _id == '0':
            # If there is an inactive link, reactivate it . . .
            if self.was_linked(clients_id_str, contacts_id_str):
                self.relink('', clients_id_str, contacts_id_str)
                message = "Contact relinked to client"
                return {'success': True, 'message': message}

            # . . . Otherwise, insert a new record.
            doc['created_by'] = email
            doc['created_date'] = datetime.now()

            result = self.dbconn[COLLECTION_NAME].insert_one(doc)
            if result.inserted_id:
                message = "Contact added"
                return {'success': True, 'message': message}
            message = "Failed to add new contact"
            return {'success': False, 'message': message}

        # Update existing clients_contacts record
        filter_ = {'_id': ObjectId('_id')}
        result = self.dbconn[COLLECTION_NAME].update_one(filter_, {'$set': doc})
        if result.modified_count == 1:
            message = "Client contact updated"
            return {'success': True, 'message': message}

        message = f"No updates were applied to this client contact ({result.modified_count})"
        return {'success': False, 'message': message}


def _sort_hint(name: dict) -> str:
    pad_length = 15
    pad_char = ' '
    fname = name.get('first_name')[0:pad_length].ljust(pad_length, pad_char)
    lname = name.get('last_name')[0:pad_length].ljust(pad_length, pad_char)
    mname = name.get('middle_name')[0:pad_length].ljust(pad_length, pad_char)
    return f'{lname}{fname}{mname}'
