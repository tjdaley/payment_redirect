"""
database.py - Class for access our persistent data store for publicdataws.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from datetime import datetime
import os
import re

from pymongo import ASCENDING, MongoClient
from bson.objectid import ObjectId

import pandas as pd

from util.logger import get_logger

try:
    DB_URL = os.environ["DB_URL"]
except KeyError as e:
    get_logger('database').fatal(
            "Database connection string environment variable is not set: %s",
            str(e))
    exit()

DB_NAME = 'payment_redirect'
USER_TABLE = 'users'
CLIENTS_TABLE = 'clients'
CONTACTS_TABLE = 'contacts'
ADMIN_TABLE = 'admins'

# Flag values for get_clients()
MEDIATION_RETAINER_DUE = 'M'
TRIAL_RETAINER_DUE = 'T'
EVERGREEN_PAYMENT_DUE = 'E'


class MissingFieldException(Exception):
    def __init__self(self, message: str):
        return super(message)


class Database(object):
    """
    Encapsulates a database accessor that is agnostic as to the underlying
    database product or implementation, e.g. mongo, mysql, dynamodb, flat
    files, etc.
    """
    database_connection = None

    def __init__(self):
        """
        Instance initializer.
        """
        self.client = None
        self.dbconn = Database.database_connection
        self.logger = get_logger('database')
        self.last_inserted_id = None

    def connect(self) -> bool:
        """
        Connect to the underlying datastore.

        Returns:
            (bool): True if successful, otherwise False.
        """
        if self.dbconn:
            return

        success = False

        try:
            # pep8: disable E501
            self.logger.debug(
                "Connecting to database %s at %s",
                DB_NAME,
                DB_URL)
            client = MongoClient(DB_URL)
            dbconn = client[DB_NAME]
            self.client = client
            self.dbconn = dbconn
            Database.database_connection = dbconn
            self.logger.info("Connected to database.")
            success = True
        except Exception as e:
            self.logger.error("Error connecting to database: %s", e)

        return success

    def test_connection(self) -> bool:
        """
        Test the underlying connection.

        Returns:
            (bool): True if connection is OK.
        """
        try:
            self.client.admin.command('ismaster')
            status = True
        except Exception as e:
            self.logger.error("Error testing DB conenction: %s", e)
            status = False

        return status

    def get_admin_record(self, email: str) -> dict:
        """
        Retrieve the admin record associated with the given email.
        The admin record will have a list call 'for', which is a list
        of attorney initials for which the admin user is an administrator.
        For attorneys, this list will probably just have their initials,
        e.g. ['TJD']. For paralegals, it will probably have a list with
        an entry for each attorney she or he supports, e.g. ['TJD', 'BSL']
        """
        # Create lookup filter
        filter_ = {'email': email.lower()}

        # Locate matching admin record
        document = self.dbconn[ADMIN_TABLE].find_one(filter_)
        return document

    def get_authorizations(self, email: str) -> list:
        """
        Retrieve a list of authorizations for the user identified by *email*.
        """
        admin_record = self.get_admin_record(email)
        return list(admin_record.get('authorizations', []))

    def get_contact(self, id: str) -> dict:
        """
        Return a contact record given an ID.

        Args:
            id (str): The mongodb ID of the contact to retrieve
        Returns:
            (dict): The located document or None
        """
        filter_ = {'_id': ObjectId(id)}
        document = self.dbconn[CONTACTS_TABLE].find_one(filter_)
        return document

    def get_contacts(self, email: str, page_num: int = 1, page_size: int = 25) -> list:
        """
        Retrieve a list of contacts viewable by this admin user.
        This method supports pagination.

        Args:
            email (str): Email address of admin user.
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

        contacts = self.dbconn[CONTACTS_TABLE].find({}).sort(order_by).skip(skips).limit(page_size)

        if not contacts:
            return None, None

        return list(contacts)

    def get_users(self, email: str) -> list:
        """
        Return a list of users whom the user is authorized to manage.

        Args:
            email (str): Email address of user who requested the query
        Returns:
            (list): Of admins docs.
        """
        admin_record = self.get_admin_record(email)
        groups = list(admin_record.get('groups', []))

        filter_ = {
            '$and': [
                {'groups': {'$in': groups}},
                {'active_flag': {'$eq': 'Y'}}
            ]
        }

        documents = list(self.dbconn[ADMIN_TABLE].find(filter_).sort([('last_name', ASCENDING), ('first_name', ASCENDING), ('email', ASCENDING)]))
        return documents

    def get_user(self, email: str, user_id: str) -> dict:
        """
        Return an admin record given an ID.

        Args:
            email (str): Email address of user who requested the query
            user_id (str): _id of admin record to retrieve
        Returns:
            (dict): Admins record or None
        """
        admin_record = self.get_admin_record(email)
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
        document = self.dbconn[ADMIN_TABLE].find_one(filter_)
        return document

    def save_user(self, fields) -> dict:
        """
        Save an admin record
        NOTE: if *fields* is missing 'active_flag', it will be set to 'N' (inactive).
        """
        doc = multidict2dict(fields)

        # Fix the flags
        flag_fields = ['active_flag']
        for field in flag_fields:
            if field in doc:
                doc[field] = 'Y'
            else:
                doc[field] = 'N'

        # Dump the dict before saving it
        for key, value in doc.items():
            print(f"{key} = {value}")

        # Determine client name for status message
        if 'first_name' in doc:
            client_name = doc['first_name']
        else:
            client_name = 'User'

        # Insert new admin record
        if doc['_id'] == '0':
            del doc['_id']
            result = self.dbconn[ADMIN_TABLE].insert_one(doc)
            if result.inserted_id:
                message = f"User record added for {client_name}"
                return {'success': True, 'message': message}
            message = "Failed to add new user record"
            return {'success': False, 'message': message}

        # Update existing client record
        filter_ = {'_id': ObjectId(doc['_id'])}
        del doc['_id']
        result = self.dbconn[ADMIN_TABLE].update_one(filter_, {'$set': doc})
        if result.modified_count == 1:
            message = f"{client_name}'s record updated"
            return {'success': True, 'message': message}

        message = f"{client_name}'s record did not update ({result.modified_count})"
        return {'success': False, 'message': message}

    def get_clients(self, email: str, flag: str = None) -> list:
        """
        Return a list of client records where the email provided
        is one of the admin_users of the client record.

        Args:
            email (str): Email address of user who requested the query
            flag (str): 'M' for clients who owe a mediation retainer
                        'T' for clients to who a trial retainer
                        'E' for clients who just have an evergreen payment due
                        None for all clients
        Returns:
            (list): Of client docs.
        """
        filter_ = {
            '$and': [
                {'admin_users': {'$elemMatch': {'$eq': email}}},
                {'active_flag': {'$eq': 'Y'}}
            ]
        }

        # See if we have a flag to add to the filter
        if flag:
            if flag == MEDIATION_RETAINER_DUE:
                filter_['$and'].append({'mediation_retainer_flag': {'$eq': 'Y'}})
                filter_['$and'].append({'trial_retainer_flag': {'$eq': 'N'}})
            elif flag == TRIAL_RETAINER_DUE:
                filter_['$and'].append({'trial_retainer_flag': {'$eq': 'Y'}})
                filter_['$and'].append({'mediation_retainer_flag': {'$eq': 'N'}})
            elif flag == EVERGREEN_PAYMENT_DUE:
                filter_['$and'].append({'trial_retainer_flag': {'$eq': 'N'}})
                filter_['$and'].append({'mediation_retainer_flag': {'$eq': 'N'}})
            else:
                return {}

        documents = list(self.dbconn[CLIENTS_TABLE].find(filter_))
        return documents

    def get_clients_as_csv(self, email: str) -> str:
        """
        Return the client list as a CSV string.
        """
        documents = self.get_clients(email)
        clients = clients_to_dataframe(documents)

        # Drop columns that don't need to be downloaded
        clients = clients.drop(columns=['_id', 'admin_users', 'check_digit', 'client_dl', 'client_ssn', 'active_flag'])

        # Create and return CSV file.
        csv_export = clients.to_csv(sep=",")
        return csv_export

    def get_client(self, client_id) -> dict:
        """
        Return a client record given a client ID.
        """
        # Create lookup filter
        filter_ = {}
        filter_['_id'] = ObjectId(client_id)

        # Locate matching client document
        document = self.dbconn[CLIENTS_TABLE].find_one(filter_)
        return document

    def get_client_by_ssn(self, ssn, dl) -> dict:
        """
        Return a client record given a SSN and Driver's License.
        """
        # Create lookup filter
        filter_ = {}
        try:
            filter_['client_ssn'] = ssn
            filter_['client_dl'] = dl
        except ValueError:
            return None

        # Locate matching client document
        document = self.dbconn[CLIENTS_TABLE].find_one(filter_)
        return document

    def save_client(self, fields, user_email) -> dict:
        """
        Save a client record, if the user is permitted to do so.
        NOTE: if *fields* is missing 'active_flag', it will be set to 'N' (inactive).
        """
        doc = multidict2dict(fields)
        csv_to_list(doc, ['attorney_initials', 'admin_users'])

        # Make sure we have the correct check digit
        if 'client_ssn' in doc and 'client_dl' in doc:
            doc['check_digit'] = correct_check_digit(doc['client_ssn'], doc['client_dl'])

        # Clean up dollar amount strings and convert them to numbers
        dollar_fields = ['payment_due', 'target_retainer', 'trial_retainer', 'mediation_retainer', 'refresh_trigger', 'trust_balance', 'orig_trust_balance']
        str_to_dollars(doc, dollar_fields)

        # Set the trust balance update date/time
        if 'trust_balance' in doc and 'orig_trust_balance' in doc and doc['trust_balance'] != doc['orig_trust_balance']:
            doc['trust_balance_update'] = datetime.now()
        if 'orig_trust_balance' in doc:
            del doc['orig_trust_balance']

        # Fix the flags
        flag_fields = ['active_flag', 'trial_retainer_flag', 'mediation_retainer_flag']
        set_missing_flags(doc, flag_fields)

        # Determine client name for status message
        if 'client_name' in doc:
            client_name = doc['client_name']
        else:
            client_name = 'Client'

        # Insert new client record
        if doc['_id'] == '0':
            del doc['_id']
            # Create a reference field
            doc['reference'] = f"Client ID {doc['billing_id']}"
            result = self.dbconn[CLIENTS_TABLE].insert_one(doc)
            if result.inserted_id:
                message = f"Client record added for {client_name}"
                return {'success': True, 'message': message}
            message = "Failed to add new client record"
            return {'success': False, 'message': message}

        # Update existing client record
        filter_ = {'_id': ObjectId(doc['_id'])}
        del doc['_id']
        result = self.dbconn[CLIENTS_TABLE].update_one(filter_, {'$set': doc})
        if result.modified_count == 1:
            message = f"{client_name}'s record updated"
            return {'success': True, 'message': message}

        message = f"No updates applied to {client_name}'s record({result.modified_count})"
        return {'success': False, 'message': message}


def multidict2dict(d) -> dict:
    """
    Create a dict from the given multidict.
    We get multidicts from Flask and have to convert them
    to dicts to modify them here.
    """
    return {key: value for key, value in d.items()}


CHECK_DIGITS = os.environ.get('CHECK_DIGITS', 'QPWOEIRUTYALSKDJFHGZMXNCBV')
CHECK_DIGITS_LENGTH = len(CHECK_DIGITS)


def correct_check_digit(ssn: str, dl: str) -> str:
    s = f'{ssn}{dl}'
    total = 0
    try:
        for letter in s:
            total += int(letter)
    except ValueError:
        return ''

    check_index = total % CHECK_DIGITS_LENGTH
    return CHECK_DIGITS[check_index]


def clients_to_dataframe(documents: dict):
    """
    Convert result set to dataframe.
    """
    our_pay_url = os.environ.get('OUR_PAY_URL')
    clients = pd.DataFrame(columns=[])
    # pylint: disable=unused-variable
    for num, client in enumerate(documents):
        # pylint: enable=unused-variable
        client_id = str(client['_id'])
        client['_id'] = client_id
        client['payment_link'] = f"{our_pay_url}{client['client_ssn']}{client['client_dl']}{client['check_digit']}"
        series_obj = pd.Series(client, name=client_id)
        clients = clients.append(series_obj)
    return clients


def csv_to_list(doc: dict, csv_fields: list):
    """
    Convert the fields where a user can type a comma-separated-list into
    an actual list.
    """
    for field in csv_fields:
        if field in doc:
            doc[field] = doc[field].strip().upper().split(',')


def str_to_dollars(doc: dict, dollar_fields: list):
    """
    Convert strings to dollar amounts.
    """
    for field in dollar_fields:
        try:
            if field in doc and doc[field]:
                doc[field] = re.sub(r'[^0-9.\-]', '', doc[field])
                doc[field] = float(doc[field])
        except Exception as e:
            return {'success': False, 'message': f"Invalid {field} amount: {str(e)}"}


def set_missing_flags(doc: dict, flag_fields: list):
    """
    Set missing flags to 'N'
    """
    for field in flag_fields:
        if field in doc:
            doc[field] = 'Y'
        else:
            doc[field] = 'N'
