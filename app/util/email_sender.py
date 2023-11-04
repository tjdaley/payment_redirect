"""
email_sender.py - Send bulk email to clients.

Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import json
import os
from datetime import datetime, timedelta
import boto3

from util.template_manager import TemplateManager
import msftconfig  # NOQA
from util.logger import get_logger

from util.db_clients import DbClients, TRIAL_RETAINER_DUE, MEDIATION_RETAINER_DUE, EVERGREEN_PAYMENT_DUE
from dotenv import load_dotenv
load_dotenv()

DATABASE = DbClients()

TEMPLATE_MANAGER = TemplateManager()


def send_evergreen(email: str):
    """
    Send evergreen letters to clients.

    Args:
        email (str): Email address of user who wants to send letters.
    """
    clients = DATABASE.get_list(email, MEDIATION_RETAINER_DUE)
    _send_email(email, clients, 'MediationRetainer')

    clients = DATABASE.get_list(email, TRIAL_RETAINER_DUE)
    _send_email(email, clients, 'TrialRetainer')

    clients = DATABASE.get_list(email, EVERGREEN_PAYMENT_DUE)
    _send_email(email, clients, 'EverGreen')


def _send_email(from_email: str, clients: list, template: dict):
    boto_client = boto3.client(
        'ses',
        region_name=os.environ.get('AWS_REGION'),
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )
    log = get_logger('email_sender')

    for client in clients:
        # Don't send if trust balance has never been updated
        if 'trust_balance_update' not in client:
            continue

        # Don't send if trust balance has not been updated since
        # the last time we sent an evergreen letter.
        if 'evergreen_sent_date' in client:
            if client['evergreen_sent_date'] > client['trust_balance_update']:
                continue

        destination = {
            'ToAddresses': [client['email']],
            'BccAddresses': [from_email]
        }

        # Convert client dict to json-string for use by SES
        template_data = _template_data(client)

        try:
            # Queue the email message for transmission.
            boto_client.send_templated_email(
                Source=from_email,
                Template=template,
                Destination=destination,
                TemplateData=template_data
            )
        except Exception as e:
            # Log an error to the client's record and go to the next client.
            message = f"Email failed {str(e)}"
            log.error(message)
            update = {
                '_id': client['_id'],
                'email_date': datetime.now(),
                'email_status': message,
                'active_flag': client['active_flag']
            }
            DATABASE.save(update, from_email)
            continue

        # On success, notate a succesful queueing to the client record
        update = {
            '_id': client['_id'],
            'evergreen_sent_date': datetime.now(),
            'active_flag': client['active_flag'],
            'email_date': datetime.now(),
            'email_status': 'OK'
        }
        DATABASE.save(update, from_email)


def _env_int(key: str, default: int = 0) -> int:
    """
    Retrieve an int from the named environment variable.

    Args:
        key (str): Environment variable to look for.
        default (int): Default value if variable not found or on type errors.

    Returns:
        (int): Int value of environment variable or default on failure.
    """
    v = os.environ.get(key, default)
    try:
        v = int(v)
    except ValueError:
        v = default
    return v


def _due_date(client: dict):
    """
    Determine when payment is due.
    """
    now = datetime.now()
    days_to_refresh_retainer = _env_int('REFRESH_DAYS', 7)
    days_to_refresh_trial_retainer = _env_int('REFRESH_TRIAL_DAYS', 45)
    days_to_refresh_mediation_retainer = _env_int('REFRESH_MEDIATION_DAYS', 30)

    if client.get('mediation_retainer_flag', 'N') == 'Y' and client['mediation_date']:
        d_day = datetime.strptime(client['mediation_date'], '%Y-%m-%d')
        payment_due = d_day + timedelta(days=-days_to_refresh_mediation_retainer)
        if payment_due < now:
            payment_due = now + timedelta(days=days_to_refresh_retainer)
        return payment_due

    if client.get('trial_retainer_flag', 'N') == 'Y' and client['trial_date']:
        d_day = datetime.strptime(client['trial_date'], '%Y-%m-%d')
        payment_due = d_day + timedelta(days=-days_to_refresh_trial_retainer)
        if payment_due < now:
            payment_due = now + timedelta(days=days_to_refresh_retainer)
        return payment_due

    return now + timedelta(days=10)


def _template_data(client) -> str:
    base_address = os.environ.get('OUR_PAY_URL')
    pay_url = f"{base_address}{client['client_ssn']}{client['client_dl']}{client['check_digit']}"
    payment_due_date = _due_date(client)
    template_data = {
            'due_date': _long_date(payment_due_date),
            'mediation_retainer':  _dollar(client['mediation_retainer']),
            'notes':  client['notes'],
            'payment_due':  _dollar(client['payment_due']),
            'payment_link':  pay_url,
            'refresh_trigger':  _dollar(client['refresh_trigger']),
            'salutation':  client['name']['salutation'],
            'trust_balance':  _dollar(client['trust_balance']),
            'target_retainer':  _dollar(client['target_retainer']),
            'trial_retainer':  _dollar(client['trial_retainer'])
    }

    if client['trial_date']:
        template_data['trial_date'] = _long_date(datetime.strptime(client['trial_date'], '%Y-%m-%d'))
    if client['mediation_date']:
        template_data['mediation_date'] = _long_date(datetime.strptime(client['mediation_date'], '%Y-%m-%d'))

    return json.dumps(template_data)


def _long_date(d):
    return d.strftime('%A, %B %d, %Y')


def _dollar(n):
    try:
        float_amount = float(n)
    except ValueError:
        float_amount = 0.0

    return '${:,.2f}'.format(float_amount)
