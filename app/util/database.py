"""
database.py - Class for access our persistent data store for publicdataws.

@author Thomas J. Daley, J.D.
@version 0.0.1
@Copyright (c) 2019 by Thomas J. Daley, J.D. All Rights Reserved.
TODO: This needs to operate as a singleton.
      At this time, we have lots of individual database connections--one for
      each time this class is imported.

Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from datetime import datetime, timedelta
import json
import os
from operator import itemgetter
import re
import time

from pymongo import MongoClient, ReturnDocument
from bson.objectid import ObjectId
from bson.errors import InvalidId

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
ADMIN_TABLE = 'admins'


class MissingFieldException(Exception):
    def __init__self(self, message: str):
        return super(message)


class Database(object):
    """
    Encapsulates a database accessor that is agnostic as to the underlying
    database product or implementation, e.g. mongo, mysql, dynamodb, flat
    files, etc.
    """

    def __init__(self):
        """
        Instance initializer.
        """
        self.client = None
        self.dbconn = None
        self.logger = get_logger('database')
        self.last_inserted_id = None

    def connect(self) -> bool:
        """
        Connect to the underlying datastore.

        Returns:
            (bool): True if successful, otherwise False.
        """
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

    def get_clients(self, email: str) -> list:
        """
        Return a list of client records where the email provided
        is one of the admin_users of the client record.
        """
        filter_ = {
            '$and': [
                {'admin_users': {'$elemMatch': {'$eq': email}}},
                {'active_flag': {'$eq': 'Y'}}
            ]
        }
        documents = self.dbconn[CLIENTS_TABLE].find(filter_)
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
        """
        doc = multidict2dict(fields)
        # Convert CSVs to lists
        doc['attorney_initials'] = fields['attorney_initials'].strip().upper().split(',')
        doc['admin_users'] = fields['admin_users'].strip().lower().split(',')

        # Clean up dollar amount
        # This lets user input the number however they want...currency symbols, commas, or not.
        doc['payment_due'] = re.sub('[^0-9.]', '', doc['payment_due'])

        # Make sure we have the correct check digit
        doc['check_digit'] = correct_check_digit(doc['client_ssn'], doc['client_dl'])

        # Convert numbers from strings
        dollar_amounts = ['payment_due', 'target_retainer', 'trial_retainer', 'mediation_retainer', 'refresh_trigger']
        for field in dollar_amounts:
            try:
                if field in doc and doc[field]:
                    doc[field] = float(doc[field])
            except Exception as e:
                return {'success': False, 'message': f"Invalid {field} amount: {str(e)}"}

        # Fix the flags
        flag_fields = ['active_flag', 'trial_retainer_flag', 'mediation_retainer_flag']
        for field in flag_fields:
            if field in doc:
                doc[field] = 'Y'
            else:
                doc[field] = 'N'

        # Dump the dict before saving it
        for key, value in doc.items():
            print(f"{key} = {value}")

        # Insert new client record
        if doc['_id'] == '0':
            del doc['_id']
            # Create a reference field
            doc['reference'] = f"Client ID {doc['billing_id']}"
            result = self.dbconn[CLIENTS_TABLE].insert_one(doc)
            if result.inserted_id:
                message = f"Client record added for {fields['client_name']}"
                return {'success': True, 'message': message}
            message = "Failed to add new client record"
            return {'success': False, 'message': message}

        # Update existing client record
        filter_ = {'_id': ObjectId(doc['_id'])}
        del doc['_id']
        result = self.dbconn[CLIENTS_TABLE].update_one(filter_, {'$set': doc})
        if result.modified_count == 1:
            message = f"{fields['client_name']}'s record updated"
            return {'success': True, 'message': message}

        client_name = fields['client_name']
        message = f"{client_name}'s record failed to update ({result.modified_count})"
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
    for num, client in enumerate(documents):
        client_id = str(client['_id'])
        client['_id'] = client_id
        client['payment_link'] = f"{our_pay_url}{client['client_ssn']}{client['client_dl']}{client['check_digit']}"
        series_obj = pd.Series(client, name=client_id)
        clients = clients.append(series_obj)
    return clients
