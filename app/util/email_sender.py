"""
email_sender.py - Send bulk email to clients.

Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import json
import os
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

import settings

from util.template_manager import TemplateManager
import config

from util.database import Database, TRIAL_RETAINER_DUE, MEDIATION_RETAINER_DUE, EVERGREEN_PAYMENT_DUE
DATABASE = Database()
DATABASE.connect()

TEMPLATE_MANAGER = TemplateManager()
AWS_REGION = os.environ.get('AWS_REGION')


def send_evergreen(email: str):
    """
    Send evergreen letters to clients.

    Args:
        email (str): Email address of user who wants to send letters.
    """
    clients = DATABASE.get_clients(email, MEDIATION_RETAINER_DUE)
    _send_email(email, clients, 'MediationRetainer')

    clients = DATABASE.get_clients(email, TRIAL_RETAINER_DUE)
    _send_email(email, clients, 'TrialRetainer')

    clients = DATABASE.get_clients(email, EVERGREEN_PAYMENT_DUE)
    _send_email(email, clients, 'EverGreen')


def _send_email(from_email: str, clients: list, template: dict):
    boto_client = boto3.client('ses', region_name=AWS_REGION, )
    for client in clients:
        # Don't send if trust balance has never been updated
        if 'trust_balance_update' not in client:
            continue

        # Don't send if trust balance has not been updated since
        # the last time we send an evergreen letter.
        if 'evergreen_sent_date' in client:
            if client['evergreen_sent_date'] > client['trust_balance_update']:
                continue

        destination = {
            'ToAddresses': [client['email']],
            'BccAddresses': [from_email]
        }
        template_data = _template_data(client)
        boto_client.send_templated_email(
            Source=from_email,
            Template=template,
            Destination=destination,
            TemplateData=template_data
        )
        update = {
            '_id': client['_id'],
            'evergreen_sent_date': datetime.now(),
            'active_flag': client['active_flag']
        }
        DATABASE.save_client(update, from_email)


def _due_date(client: dict):
    now = datetime.now()
    if client.get('mediation_retainer_flag', 'N') == 'Y':
        d_day = datetime.strptime(client['mediation_date'], '%Y-%m-%d')
        payment_due = d_day + timedelta(days=-14)
        if payment_due < now:
            payment_due = now + timedelta(days=5)
        return payment_due

    if client.get('trial_retainer_flag', 'N') == 'Y':
        d_day = datetime.strptime(client['trial_date'], '%Y-%m-%d')
        payment_due = d_day + timedelta(days=-45)
        if payment_due < now:
            payment_due = now + timedelta(days=5)
        return payment_due

    return now + timedelta(days=10)


def _template_data(client) -> list:
    base_address = os.environ.get('OUR_PAY_URL')
    pay_url = f"{base_address}{client['client_ssn']}{client['client_dl']}{client['check_digit']}"
    payment_due_date = _due_date(client)
    template_data = {
            'due_date': _long_date(payment_due_date),
            'mediation_date':  _long_date(datetime.strptime(client['mediation_date'], '%Y-%m-%d')),
            'mediation_retainer':  _dollar(client['mediation_retainer']),
            'notes':  client['notes'],
            'payment_due':  _dollar(client['payment_due']),
            'payment_link':  pay_url,
            'refresh_trigger':  _dollar(client['refresh_trigger']),
            'salutation':  client['salutation'],
            'trust_balance':  _dollar(client['trust_balance']),
            'target_retainer':  _dollar(client['target_retainer']),
            'trial_date':  _long_date(datetime.strptime(client['trial_date'], '%Y-%m-%d')),
            'trial_retainer':  _dollar(client['trial_retainer'])
    }
    return json.dumps(template_data)


def _long_date(d):
    return d.strftime('%A, %B %d, %Y')


def _dollar(n):
    return '${:,.2f}'.format(n)
