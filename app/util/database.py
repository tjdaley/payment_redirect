"""
database.py - Class for access our persistent data store for publicdataws.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import os
import re

from pymongo import MongoClient

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
        self.connect()

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


def multidict2dict(d) -> dict:
    """
    Create a dict from the given multidict.
    We get multidicts from Flask and have to convert them
    to dicts to modify them here.
    """
    return {key: value for key, value in d.items()}


def csv_to_list(doc: dict, csv_fields: list):
    """
    Convert the fields where a user can type a comma-separated-list into
    an actual list.
    """
    for field in csv_fields:
        if field in doc:
            doc[field] = doc[field].strip().lower().split(',')


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


def do_upgrades():
    pass
