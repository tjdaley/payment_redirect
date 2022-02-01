"""
database.py - Class for access our persistent data store for publicdataws.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import os
import re
from numpy import isin

import phonenumbers
from pymongo import MongoClient
from datetime import date, datetime
from decimal import Decimal
from util.logger import get_logger

try:
    DB_URL = os.environ["DB_URL"]
except KeyError as e:
    get_logger('database').fatal(
            "Database connection string environment variable is not set: %s",
            str(e))
    exit()

DB_NAME = 'payment_redirect'

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
    database_connections = {}
    logger = None

    def __init__(self, db_name: str = DB_NAME):
        """
        Instance initializer.
        """
        if Database.logger is None:
            Database.logger = get_logger('database')
        self.client = None
        self.dbconn = Database.database_connections.get(db_name)
        self.logger = Database.logger
        self.last_inserted_id = None
        self.db_name = db_name
        self.connect()

    def connect(self) -> bool:
        """
        Connect to the underlying datastore.

        Returns:
            (bool): True if successful, otherwise False.
        """
        if self.db_name in Database.database_connections:
            self.dbconn = Database.database_connections[self.db_name]
            self.logger.debug("Reusing connection to %s for %s", self.db_name, self.__class__.__name__)
            return True

        success = False

        try:
            # pep8: disable E501
            self.logger.debug(
                "Connecting to database %s at %s for %s",
                self.db_name,
                DB_URL,
                self.__class__.__name__)
            client = MongoClient(DB_URL)
            dbconn = client[self.db_name]
            self.client = client
            self.dbconn = dbconn
            Database.database_connections[self.db_name] = dbconn
            self.logger.info("Connected to database %s.", self.db_name)
            success = True
        except Exception as e:
            self.logger.error("Error connecting to database %s: %s", self.db_name, e)

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


def multidict2dict(d, blank_dict: dict = None) -> dict:
    """
    Create a dict from the given multidict.
    We get multidicts from Flask and have to convert them
    to dicts to modify them here.
    """
    if blank_dict:
        for key, value in d.items():
            blank_dict[key] = value
        return blank_dict
    return {key: value for key, value in d.items()}


def csv_to_list(doc: dict, csv_fields: list):
    """
    Convert the fields where a user can type a comma-separated-list into
    an actual list. Strip trailing and leading whitespace from items.
    """
    for field in csv_fields:
        if field in doc and isinstance(doc[field], (str)):
            # doc[field] = doc[field].strip().lower().split(',')  # removed 2021.10.28 by TJD
            doc[field] = [k.strip() for k in doc[field].strip().lower().split(',')]


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
            if doc[field] is True or doc[field] in ['y', 'Y']:  # Don't use .upper() because value might be bool
                doc[field] = 'Y'
            else:
                doc[field] = 'N'
        else:
            doc[field] = 'N'


def convert_type(z):
    if isinstance(z, Decimal):
        return float(str(z))
    elif isinstance(z, date):
        return str(z)
    return z


def convert_types(dict_item):
    # This function iterates a dictionary looking for types of Decimal and converts them to float
    # Embedded dictionaries and lists are called recursively.
    if dict_item is None: return None

    if isinstance(dict_item, dict):
        for k, v in list(dict_item.items()):
            if isinstance(v, dict):
                convert_types(v)
            elif isinstance(v, list):
                for l in v:
                    convert_types(l)
            else:
                dict_item[k] = convert_type(v)
    if isinstance(dict_item, list):
        for k, v in enumerate(dict_item):
            if isinstance(v, dict):
                convert_types(v)
            elif isinstance(v, list):
                for l in v:
                    convert_types(l)
            else:
                dict_item[k] = convert_type(v)

    return dict_item


def normalize_telephone_number(telephone_number: str) -> str:
    """
    Create an international dialing string from a phone number.
    User may have entered a phone number in any number of formats.
    This method normalizes the telephone number formar for database
    storage. The format used is E164.

    Args:
        telephone_number (str): Number to be cleaned up.
    Returns:
        (str): Normalized telephone number string
    """
    if not telephone_number:
        return telephone_number

    tn = None
    try:
        tn = phonenumbers.parse(telephone_number)
    except Exception:
        pass

    # If parsing failed, try putting a country code in front of the number
    # Assuming a US country code.
    if tn is None:
        try:
            tn = phonenumbers.parse(f'+1{telephone_number}')
        except Exception:
            pass

    # If parsing still failed, then send back the same string we received.
    if tn is None:
        return telephone_number

    normalized_number = phonenumbers.format_number(tn, phonenumbers.PhoneNumberFormat.E164)
    return normalized_number


def do_upgrades():
    pass
