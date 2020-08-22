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
from util.us_states import US_STATE_NAMES
from util.logger import get_logger

COLLECTION_NAME = 'clients'

# Flag values for get_clients()
MEDIATION_RETAINER_DUE = 'M'
TRIAL_RETAINER_DUE = 'T'
EVERGREEN_PAYMENT_DUE = 'E'


class DbClients(Database):
    """
    Encapsulates a database accessor for clients
    """
    def get_list(self, email: str, flag: str = None, projection: dict = None, crm_state: str = '070:retained_active', where: dict = {}) -> list:
        """
        Return a list of client records where the email provided
        is one of the admin_users of the client record.

        Args:
            email (str): Email address of user who requested the query
            flag (str): 'M' for clients who owe a mediation retainer
                        'T' for clients who owe a trial retainer
                        'E' for clients who just have an evergreen payment due
                        None for all clients
            projection (dict): MongoDb projection (defaults to all doc cols)
            crm_state (str): CRM State to select. Default is '070:retained_acive',
                             None or '*' for all CRM States.
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

        if crm_state and crm_state != '*':
            filter_['$and'].append({'crm_state': {'$eq': crm_state}})

        if where:
            filter_['$and'].append(where)

        order_by = [
            ('crm_state', ASCENDING),
            ('name.last_name', ASCENDING),
            ('name.first_name', ASCENDING),
            ('email', ASCENDING)
        ]

        documents = list(self.dbconn[COLLECTION_NAME].find(filter_, projection).sort(order_by))
        return documents

    def search(self, email: str, query: str, page_num: int = 1, page_size: int = 25, crm_state: str = None) -> list:
        """
        Search for clients matching the words in *query*.

        Args:
            email (str): Email of user performing the search.
            query (str): Query string from user.
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
            'email',
            'telephone',
            'address.street',
            'address.city',
            'case_county',
            'court_name',
            'cause_number',
            'oag_number'
        ]
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
            crm_state=crm_state
        )

    def get_list_as_csv(self, email: str, crm_state=None) -> str:
        """
        Return the client list as a CSV string.
        """
        documents = self.get_list(email, crm_state=crm_state)

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

    def get_id_name_list(self, email: str, crm_state=None) -> str:
        """
        Return a list of clients as a list of tuples suitable
        for populating a select box.
        """
        docs = self.get_list(email, projection={'_id': 1, 'name': 1, 'billing_id': 1}, crm_state=crm_state)
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

    def get_client_name(self, client_id, include_title: bool = True) -> str:
        """
        Return a client name string.
        """
        client = self.get_one(client_id)
        if client:
            return make_client_name(client, include_title)
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
        """
        try:
            doc = multidict2dict(fields)
            cleanup(doc)

            # Determine client name for status message
            # client_name = doc.get('name', {}).get('salutation', 'Client')
            client_name = make_client_name(doc)

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
            doc['reference'] = f"Client ID {doc['billing_id']}"
            result = self.dbconn[COLLECTION_NAME].update_one(filter_, {'$set': doc})
            if result.modified_count == 1:
                message = f"{client_name}'s record updated"
                return {'success': True, 'message': message}

            message = f"No updates applied to {client_name}'s record({result.modified_count})"
            return {'success': True, 'message': message}
        except Exception as e:
            get_logger('db_clients').exception(e)
            return {'success': False, 'message': str(e)}


CHECK_DIGITS = os.environ.get('CHECK_DIGITS', 'QPWOEIRUTYALSKDJFHGZMXNCBV')
CHECK_DIGITS_LENGTH = len(CHECK_DIGITS)


def make_client_name(client: dict, include_title: bool = True) -> str:
    """
    Create a client_name string from parts.

    Args:
        client (dict): Document from clients collection.
        include_title (bool): Whether to include the title field as a prefix.
    Returns:
        (str): Client name string.
    """
    if include_title:
        first_index = 0
    else:
        first_index = 1
    return " ".join(list(client['name'].values())[first_index:-1])


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


def intake_to_client(intake: dict) -> dict:
    """
    Convert a dict from the Cognito Forms intake form to
    a dict compatible with our clients collection.

    Args:
        intake (dict): Intake after being saved to the intakes table.
    Returns:
        (dict): Transformed to clients collection form.
    """
    try:
        client_doc = {}

        # Internal-only fields
        admin = intake.get('AdminFields', {})
        client_doc['active_flag'] = 'Y'
        client_doc['admin_users'] = admin.get('AssignedTo', os.environ.get('ADMIN_USERS'))
        client_doc['crm_state'] = admin.get('CRMState', '040"consult_scheduled')
        client_doc['billing_id'] = admin.get('BillingID', '9999')
        client_doc['attorney_initials'] = admin.get('AttorneyInitials', 'tjd')

        # About the Cliente
        about_you = intake.get('AboutYou', {})

        # Transform names to a name dict
        name = about_you.get('Name', {})
        name = __transform_name(name)
        client_doc['name'] = name

        # Transform addresses
        address = about_you.get('Address', {})
        address = __transform_address(address)
        client_doc['address'] = address

        if about_you.get('Usehomeaddressforbilling', True):
            client_doc['billing_address'] = address
        else:
            address = about_you.get('BillingAddress', {})
            address = __transform_address(address)
            client_doc['billing_address'] = address

        # Transform client flags
        client_doc['in_county_90_days_flag'] = __flag_value(about_you.get('Incounty90days', False))
        client_doc['in_state_6_months_flag'] = __flag_value(about_you.get('Instate6months', False))
        client_doc['email_statements_flag'] = __flag_value(about_you.get('Billingemailok', False))

        # Transform telephone numbers
        telephone = about_you.get('HomeTelephone', '')
        client_doc['home_phone'] = normalize_telephone_number(telephone)
        telephone = about_you.get('CellPhone', '')
        client_doc['cell_phone'] = normalize_telephone_number(telephone)
        if about_you.get('PreferredPhone', 'Cell Phone') == 'Cell Phone':
            client_doc['telephone'] = client_doc['cell_phone']
        else:
            client_doc['telephone'] = client_doc['home_phone']

        # Client Email
        client_doc['email'] = about_you.get('Email')

        # More About You Section
        more_you = intake.get('Moreyou', {})
        vehicle = more_you.get('Vehicle', {})
        vehicle = __transform_vehicle(vehicle)
        client_doc['client_vehicle'] = vehicle

        # Employment
        employment = more_you.get('Employment', {})
        employment = __transform_employment(employment)
        client_doc['employment'] = employment

        # Client Confidential Section
        client_conf = intake.get('Clientconfidential', {})
        client_doc['client_ssn'] = client_conf.get('Ssn', '000')
        client_doc['client_dl'] = client_conf.get('Dl', '000')
        dl_state = client_conf.get('Dlstate', {}).get('State')
        client_doc['client_dl_state'] = US_STATE_NAMES.get(dl_state, dl_state)
        client_doc['client_dob'] = client_conf.get('DateOfBirth')
        client_doc['place_of_birth'] = client_conf.get('PlaceOfBirth')

        # About OP
        about_op = intake.get('Op', {})
        client_doc['op'] = {}
        name = about_op.get('Name', {})
        name = __transform_name(name)
        client_doc['op']['name'] = name
        address = about_op.get('Address', {})
        address = __transform_address(address)
        client_doc['op']['address'] = address

        # Transform OP flags
        client_doc['op']['in_county_90_days_flag'] = __flag_value(about_op.get('LivedInThiscountyMoreThan90Days', False))
        client_doc['op']['in_state_6_months_flag'] = __flag_value(about_op.get('LivedInThisstateMoreThan6Months', False))

        # OP Confidential
        op_conf = intake.get('ConfidentialInformationAboutOpNameRequiredByTheState', {})
        client_doc['op']['ssn'] = op_conf.get('LastThreeDigitsOfFormOpNameFirstsSocialSecurityNumber', '000')
        client_doc['op']['dl'] = op_conf.get('LastThreeDigitsOfFormOpNameFirstsDriversLicenseNumber', '000')
        dl_state = op_conf.get('Dlstate', {}).get('State')
        client_doc['op']['dl_state'] = US_STATE_NAMES.get(dl_state, dl_state)
        client_doc['op']['dob'] = op_conf.get('DateOfBirth')
        client_doc['op']['place_of_birth'] = op_conf.get('PlaceOfBirth')

        # More About OP Section
        more_op = intake.get('Moreop', {})
        vehicle = more_op.get('FormOpNameFirstsPrimaryAutomobile', {})
        vehicle = __transform_vehicle(vehicle)
        client_doc['op']['client_vehicle'] = vehicle

        # Employment
        employment = more_op.get('FormOpNameFirstsPrimaryEmployment', {})
        employment = __transform_employment(employment)
        client_doc['op']['employment'] = employment

        # Physical Description
        phys = more_op.get('FormOpNameFirstsPhysicalDescription', {})
        client_doc['op']['physical_description'] = {
            'height': phys.get('Height', ''),
            'weight': phys.get('Weight', ''),
            'hair_color': phys.get('HairColor', '')
        }

        # Marriage Information
        marriage = intake.get('Marriage', {})
        client_doc['marriage_date'] = marriage.get('Dom')
        client_doc['separation_date'] = marriage.get('Dos')
        client_doc['marriage_place'] = marriage.get('Place')
        client_doc['restore_maiden_name_flag'] = __flag_value(marriage.get('Maindenrestoreflag'))
        client_doc['maiden_name'] = marriage.get('Midenname')

        # Children
        children = intake.get('Children', [])
        if children:
            client_doc['children'] = []
            for child in children:
                c_name = __transform_name(child.get('Name', {}))
                c_dob = child.get('Dob', '')
                c_state = child.get('HomeState', {}).get('State')
                c_home_state = US_STATE_NAMES.get(c_state, c_state)
                c = {'name': c_name, 'dob': c_dob, 'home_state': c_home_state}
                client_doc['children'].append(c)

        # Health Insurance
        h_ins = intake.get('Med', {})
        if h_ins:
            client_doc['health_ins'] = {
                'carrier': h_ins.get('HealthInsuranceCompany'),
                'policy_holder': h_ins.get('PolicyHolderName'),
                'policy_number': h_ins.get('PolicyNumber'),
                'group_number': h_ins.get('GroupNumber'),
                'monthly_premium': h_ins.get('MonthlyCost', 0.00),
                'provided_through': h_ins.get('ProvidedThrough')
            }

        # Dental Insurance
        h_ins = intake.get('Dental', {})
        if h_ins:
            client_doc['dental_ins'] = {
                'carrier': h_ins.get('HealthInsuranceCompany'),
                'policy_holder': h_ins.get('PolicyHolderName'),
                'policy_number': h_ins.get('PolicyNumber'),
                'group_number': h_ins.get('GroupNumber'),
                'monthly_premium': h_ins.get('MonthlyCost', 0.00),
                'provided_through': h_ins.get('ProvidedThrough')
            }

        # Marketing information
        referral = intake.get('Referral', {})
        referral = __transform_referral(referral)
        client_doc['referrer'] = referral
    except Exception as e:
        get_logger('db_clients').exception(e)

    # Done!!
    return client_doc


def __flag_value(v) -> str:
    """
    Transform a flag value from Cognito into a Y or N string.
    """
    if v:
        return 'Y'
    return 'N'


def __name_string(n: dict) -> str:
    n = __transform_name(n)
    ti = n.get('title', '')
    fn = n.get('first_name', '')
    mn = n.get('middle_name', '')
    ln = n.get('last_name', '')
    sx = n.get('suffix', '')
    if ti:
        ti += ' '
    if fn:
        fn += ' '
    if mn:
        mn += ' '
    if ln:
        ln += ' '
    result = f"{ti}{fn}{mn}{ln}{sx}".strip()
    return result


def __transform_address(address: dict) -> dict:
    """
    Transform an address from Cognito format to our format.
    """
    return {
        'street': address.get('Line1', ''),
        'city': address.get('City', ''),
        'state': US_STATE_NAMES.get(address.get('State'), address.get('State')),
        'postal_code': address.get('PostalCode', ''),
        'country': address.get('Country', 'United States')
    }


def __transform_employment(employment: dict) -> dict:
    """
    Transform employment information from Cognito format to our format.
    """
    e_name = employment.get('EmployersName')
    e_job = employment.get('JobTitle')
    address = employment.get('Address', {})
    address = __transform_address(address)
    e_tel = normalize_telephone_number(employment.get('Phone', ''))
    e_inc = employment.get('ApproximateAnnualIncome', 0.0)
    contact = employment.get('EmergencyContact', {})
    contact = __transform_name(contact)
    return {
        'employer': e_name,
        'position': e_job,
        'address': address,
        'telephone': e_tel,
        'annual_income': e_inc,
        'contact': contact
    }


def __transform_name(name: dict) -> dict:
    """
    Transform a name from Cognito format to our format.
    """
    result = {}
    f_name = name.get('First')
    m_name = name.get('Middle')
    l_name = name.get('Last')
    title = name.get('Prefix')
    suffix = name.get('Suffix')

    if title:
        result['title'] = title
    if f_name:
        result['first_name'] = f_name
    if m_name:
        result['middle_name'] = m_name
    if l_name:
        result['last_name'] = l_name
    if suffix:
        result['suffix'] = suffix
    if title and l_name:
        result['salutation'] = f"{title} {l_name}"
    return result


def __transform_referral(referral: dict) -> dict:
    result = {}
    ref_to = referral.get('NameOfAttorneyYouWereReferredTo', 'FIRM')
    if ref_to:
        result['referred_to'] = ref_to
    else:
        result['referred_to'] = 'FIRM'
    result['source'] = referral.get('Source')
    if referral.get('Name', {}).get('FirstAndLast', ' ') != ' ':
        ref_name = __name_string(referral.get('Name', {}))
    elif referral.get('Website'):
        ref_name = f"SITE: {referral.get('Website')}"
    elif referral.get('Magazine'):
        ref_name = f"TITLE: {referral.get('Magazine')}"
    elif referral.get('Program'):
        ref_name = f"PROGRAM: {referral.get('Program')}"
    elif referral.get('Description'):
        ref_name = referral.get('Description')
    elif referral.get('Searchstring'):
        ref_name = f"SEARCH: {referral.get('Searchstring')}"
    else:
        ref_name = "n/a"
    result['more_info'] = ref_name
    return result


def __transform_vehicle(vehicle: dict) -> str:
    v_year = vehicle.get('Year', '')
    v_make = vehicle.get('Make', '')
    v_model = vehicle.get('Model', '')
    v_color = vehicle.get('Color', '')
    v = [v_year, v_make, v_model, v_color]
    v = [val for val in v if val]
    return ' '.join(v).strip().title()
