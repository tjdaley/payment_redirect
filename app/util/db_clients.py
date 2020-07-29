"""
database.py - Class for access our persistent data store for clients.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from datetime import datetime
import json  # noqa
import os

from pymongo import ASCENDING
from bson.objectid import ObjectId

import pandas as pd

from util.database import Database, multidict2dict, csv_to_list, str_to_dollars, set_missing_flags, normalize_telephone_number

COLLECTION_NAME = 'clients'

# Flag values for get_clients()
MEDIATION_RETAINER_DUE = 'M'
TRIAL_RETAINER_DUE = 'T'
EVERGREEN_PAYMENT_DUE = 'E'


class DbClients(Database):
    """
    Encapsulates a database accessor for clients
    """
    def get_list(self, email: str, flag: str = None, projection: dict = None) -> list:
        """
        Return a list of client records where the email provided
        is one of the admin_users of the client record.

        Args:
            email (str): Email address of user who requested the query
            flag (str): 'M' for clients who owe a mediation retainer
                        'T' for clients to who a trial retainer
                        'E' for clients who just have an evergreen payment due
                        None for all clients
            projection (dict): MongoDb projection (defaults to all doc cols)
        Returns:
            (list): Of client docs.
        """
        filter_ = {
            '$and': [
                {'admin_users': {'$elemMatch': {'$eq': email.lower()}}},
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

        order_by = [
            ('name.last_name', ASCENDING),
            ('name.first_name', ASCENDING),
            ('email', ASCENDING)
        ]

        documents = list(self.dbconn[COLLECTION_NAME].find(filter_, projection).sort(order_by))
        return documents

    def get_list_as_csv(self, email: str) -> str:
        """
        Return the client list as a CSV string.
        """
        documents = self.get_list(email)

        # Break out compound fields into individual columns
        for document in documents:
            name = document.get('name', {})
            for key, value in name.items():
                document[key] = value
            address = document.get('address', {})
            for key, value in address.items():
                document[key] = value

        clients = clients_to_dataframe(documents)

        # Drop columns that don't need to be downloaded
        clients = clients.drop(
            columns=[
                '_id', 'admin_users', 'check_digit', 'client_dl', 'client_ssn',
                'active_flag', 'name', 'address', 'address1', 'client_name'
            ])

        # Create and return CSV file.
        csv_export = clients.to_csv(sep=",")
        return csv_export

    def get_id_name_list(self, email: str) -> str:
        """
        Return a list of clients as a list of tuples suitable
        for populating a select box.
        """
        docs = self.get_list(email, projection={'_id': 1, 'name': 1, 'billing_id': 1})
        clients = {}
        for doc in docs:
            cn_name = " ".join(list(doc['name'].values())[0:-1])
            clients[str(doc['_id'])] = cn_name
        return clients

    def get_one(self, client_id) -> dict:
        """
        Return a client record given a client ID.
        """
        # Create lookup filter
        filter_ = {}
        filter_['_id'] = ObjectId(client_id)

        # Locate matching client document
        document = self.dbconn[COLLECTION_NAME].find_one(filter_)
        return document

    def get_by_ssn(self, ssn, dl) -> dict:
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
        document = self.dbconn[COLLECTION_NAME].find_one(filter_)
        return document

    def get_client_name(self, client_id) -> str:
        """
        Return a client name string.
        """
        client = self.get_one(client_id)
        if client:
            return " ".join(list(client['name'].values())[0:-1])
        return None

    def get_email_subject(self, client_id) -> str:
        """
        Return a standard string to use as an email subject.
        """
        client = self.get_one(client_id)
        if client:
            subj_name = client.get('name', {}).get('last_name', "")
            subj_cause = client.get('cause_number', None)
            if not subj_cause:
                subj_cause = client.get('case_style', None)
            if subj_cause:
                subj_cause = f"({subj_cause})"
            return f"{subj_name} {subj_cause}:"

        return None

    def save(self, fields, user_email) -> dict:
        """
        Save a client record, if the user is permitted to do so.
        NOTE: if *fields* is missing 'active_flag', it will be set to 'N' (inactive).
        """
        doc = multidict2dict(fields)
        cleanup(doc)

        # Determine client name for status message
        client_name = doc.get('name', {}).get('salutation', 'Client')

        # Insert new client record
        if doc['_id'] == '0':
            del doc['_id']

            doc['active_flag'] = 'Y'
            if user_email.lower() not in doc['admin_users']:
                doc['admin_users'].append(user_email.lower())

            # Create a reference field
            doc['reference'] = f"Client ID {doc['billing_id']}"
            result = self.dbconn[COLLECTION_NAME].insert_one(doc)
            if result.inserted_id:
                message = f"Client record added for {client_name}"
                return {'success': True, 'message': message}
            message = "Failed to add new client record"
            return {'success': False, 'message': message}

        # Update existing client record
        filter_ = {'_id': ObjectId(doc['_id'])}
        del doc['_id']
        result = self.dbconn[COLLECTION_NAME].update_one(filter_, {'$set': doc})
        if result.modified_count == 1:
            message = f"{client_name}'s record updated"
            return {'success': True, 'message': message}

        message = f"No updates applied to {client_name}'s record({result.modified_count})"
        return {'success': True, 'message': message}


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


def cleanup(doc: dict):
    """
    Clean up some fields before saving.
    """
    # Convert the fields that are CSV to the user but lists in the database
    csv_to_list(doc, ['attorney_initials', 'admin_users'])

    # Make sure we have the correct check digit
    if 'client_ssn' in doc and 'client_dl' in doc:
        doc['check_digit'] = correct_check_digit(doc['client_ssn'], doc['client_dl'])

    # Clean up dollar amount strings and convert them to numbers
    dollar_fields = ['payment_due', 'target_retainer', 'trial_retainer', 'mediation_retainer', 'refresh_trigger', 'trust_balance', 'orig_trust_balance']
    str_to_dollars(doc, dollar_fields)

    # Normalize the email address
    if 'email' in doc:
        doc['email'] = doc['email'].strip().lower()

    # Normalize telephone numbers
    phone_number_fields = ['telephone']
    for field in phone_number_fields:
        if field in doc:
            doc[field] = normalize_telephone_number(doc[field])

    # Set the trust balance update date/time
    if 'trust_balance' in doc and 'orig_trust_balance' in doc and doc['trust_balance'] != doc['orig_trust_balance']:
        doc['trust_balance_update'] = datetime.now()
    if 'orig_trust_balance' in doc:
        del doc['orig_trust_balance']

    # Fix the flags
    flag_fields = ['trial_retainer_flag', 'mediation_retainer_flag']
    set_missing_flags(doc, flag_fields)
