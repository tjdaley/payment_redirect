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
import time

from pymongo import MongoClient, ReturnDocument
from bson.objectid import ObjectId
from bson.errors import InvalidId

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
        filter_ = {'admin_users': {'$elemMatch': {'$eq': email}}}
        documents = self.dbconn[CLIENTS_TABLE].find(filter_)
        return documents

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
            filter_['client_ssn'] = int(ssn)
            filter_['client_dl'] = int(dl)
        except ValueError:
            return None

        # Locate matching client document
        document = self.dbconn[CLIENTS_TABLE].find_one(filter_)
        return document

    def save_client(self, fields, user_email) -> dict:
        """
        Save a client record, if the user is permitted to do so.
        """
        return {'success': True, 'message': "Client record updated"}
