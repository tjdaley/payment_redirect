"""
db_users.py - Class for access our persistent data store for users.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from pymongo import ASCENDING
from bson.objectid import ObjectId

from util.database import Database, multidict2dict, set_missing_flags, normalize_telephone_number
from util.db_admins import DbAdmins
from util.logger import get_logger


COLLECTION_NAME = 'admins'


class DbUsers(Database):
    """
    Encapsulates a database accessor for admin users
    """
    db_admins = DbAdmins()

    def get_list(self, email: str) -> list:
        """
        Return a list of users whom the user is authorized to manage.

        Args:
            email (str): Email address of user who requested the query
        Returns:
            (list): Of admins docs.
        """
        admin_record = DbUsers.db_admins.admin_record(email)
        groups = list(admin_record.get('groups', []))

        filter_ = {
            '$and': [
                {'groups': {'$in': groups}},
                {'active_flag': {'$eq': 'Y'}}
            ]
        }

        order_by = [
            ('name.last_name', ASCENDING),
            ('name.first_name', ASCENDING),
            ('email', ASCENDING)
        ]

        documents = list(self.dbconn[COLLECTION_NAME].find(filter_).sort(order_by))
        return documents

    def get_one(self, email: str, user_id: str) -> dict:
        """
        Return an admin record given an ID.

        Args:
            email (str): Email address of user who requested the query
            user_id (str): _id of admin record to retrieve
        Returns:
            (dict): Admins record or None
        """
        admin_record = DbUsers.db_admins.admin_record(email)
        groups = list(admin_record.get('groups', []))

        # Create lookup filter
        # Select admin with given ID *if* the admin is active and
        # the requesting user is permitted to retrieve the record
        filter_ = {
            '$and': [
                {'groups': {'$in': groups}},
                {'active_flag': {'$eq': 'Y'}},
                {'_id': {'$eq': ObjectId(user_id)}}
            ]
        }

        # Locate matching admin document
        document = self.dbconn[COLLECTION_NAME].find_one(filter_)
        return document

    def save(self, fields) -> dict:
        """
        Save an admin record
        NOTE: if *fields* is missing 'active_flag', it will be set to 'N' (inactive).
        """
        doc = multidict2dict(fields)

        # Determine user's name for status message
        if 'first_name' in doc:
            user_name = doc['first_name']
        else:
            user_name = 'User'

        # Clean up fields
        try:
            if 'email' in doc:
                doc['email'] = doc['email'].strip().lower()
            if 'ring_central_username' in doc:
                doc['ring_central_username'] = normalize_telephone_number(doc['ring_central_username'])
        except Exception as e:
            get_logger('.database.users').warn("Error during clean up: %s", str(e))
            get_logger('.database.users').exception(e)

        # Insert new admin record
        if doc['_id'] == '0':
            del doc['_id']

            # Fix the flags
            flag_fields = ['active_flag', 'prompt_on_dial_flag']
            set_missing_flags(doc, flag_fields)

            result = self.dbconn[COLLECTION_NAME].insert_one(doc)
            if result.inserted_id:
                message = f"User record added for {user_name}"
                return {'success': True, 'message': message}
            message = "Failed to add new user record"
            return {'success': False, 'message': message}

        # Update existing admin record
        filter_ = {'_id': ObjectId(doc['_id'])}
        del doc['_id']
        # doc['active_flag'] = 'Y'
        set_missing_flags(doc, ['active_flag', 'prompt_on_dial_flag'])
        result = self.dbconn[COLLECTION_NAME].update_one(filter_, {'$set': doc})
        if result.modified_count == 1:
            message = f"{user_name}'s record updated"
            return {'success': True, 'message': message}

        message = f"No updates applied to {user_name}'s record ({result.modified_count})"
        return {'success': False, 'message': message}
