"""
payment_routes.py - Direct a client to the payment page

Copyright (c) 2020 by Thomas J. Daley. All Rights Reserved.
"""
import datetime as dt
import os
from flask import Blueprint, flash, redirect, render_template, request, url_for
import random
import settings  # NOQA
import urllib.parse

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.logger import get_logger
from views.payment.forms.ClientIdForm import ClientIdForm
from util.db_clients import DbClients, correct_check_digit
# pylint: enable=no-name-in-module
# pylint: enable=import-error
DBCLIENTS = DbClients()

payment_routes = Blueprint("payment_routes", __name__, template_folder="templates")


@payment_routes.route('/pay/<string:id>', methods=['GET'])
def route_client(id: str):
    """
    First three digits of ID are last three digits of client's SSN
    Next three digits of ID are last three digits of client's driver's license number
    Last digit is a check digit
    """
    if len(id) != 7:
        flash("Invalid client id.", "warning")
        return redirect(url_for('payment_routes.identify_client'))

    ssn = id[:3]
    dl = id[3:6]
    check_digit = id[-1].upper()
    if check_digit != correct_check_digit(ssn, dl):
        flash("Invalid client id.", "danger")
        return redirect(url_for('payment_routes.identify_client'))

    client = DBCLIENTS.get_by_ssn(ssn, dl)
    if not client:
        flash(f"Could not find client record. SSN {ssn} DL {dl}", "info")
        return redirect(url_for('payment_routes.identify_client'))

    url = os.environ.get('BASE_URL')
    url = enrich_url(url, client)
    return redirect(url, code=302)


@payment_routes.route("/pay", methods=['GET', 'POST'])
def identify_client():
    form = ClientIdForm(request.form)

    # TODO: form.validate() does NOT display error messages on validation errors.
    if request.method == 'POST' and form.validate():
        fields = request.form
        ssn = fields['client_ssn']
        dl = fields['client_dl']
        client = DBCLIENTS.get_by_ssn(ssn, dl)
        if not client:
            flash("Could not find your information. Please try again.", 'warning')
            return redirect(url_for('payment_routes.identify_client'))

        url = os.environ.get('BASE_URL')
        url = enrich_url(url, client)
        return redirect(url, code=302)

    return render_template("client_id.html", form=form, greeting=get_greeting())


def enrich_url(base_url, client_doc) -> str:
    """
    Add payment form API parameters for this client.
    """
    url = base_url
    params = ''
    try:
        params = f'{params}?reference={client_doc["reference"]}'
        params = f'{params}&name={client_doc["client_name"]}'
        params = f'{params}&address1={client_doc["address"]["street"]}'
        params = f'{params}&city={client_doc["address"]["city"]}'
        params = f'{params}&state={client_doc["address"]["state"]}'
        params = f'{params}&postal_code={client_doc["address"]["postal_code"]}'
        params = f'{params}&amount={client_doc["payment_due"]}'
        params = f'{params}&email={client_doc["email"]}'
    except KeyError as e:
        logger = get_logger('payment_routes')
        logger.warn("Error creating redirect url:", e)

    encoded_params = urllib.parse.quote(params, safe='?&=')
    url = f'{base_url}{encoded_params}'

    return url


def get_greeting():
    """
    Generate a random greeting.
    """
    greetings = [
        "Welcome!!",
        "Good to see you!!",
        f"Good {get_day_time()}!!",
        "Hello!!"
    ]

    return random.choice(greetings)


def get_day_time():
    hour = dt.datetime.today().hour
    if hour < 12:
        return "Morning"
    if hour < 17:
        return "Afternoon"
    return "Evening"
