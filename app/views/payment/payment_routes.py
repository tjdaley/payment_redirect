"""
payment_routes.py - Direct a client to the payment page

Copyright (c) 2020 by Thomas J. Daley. All Rights Reserved.
"""
import os
from flask import Blueprint, flash, redirect, render_template, request, url_for
import settings

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.logger import get_logger
from views.payment.forms.ClientIdForm import ClientIdForm
from util.database import Database
# pylint: enable=no-name-in-module
# pylint: enable=import-error
DATABASE = Database()
DATABASE.connect()

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

    client = DATABASE.get_client_by_ssn(ssn, dl)
    if not client:
        flash("Could not find client record.", "info")
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
        client = DATABASE.get_client_by_ssn(ssn, dl)
        if not client:
            flash("Could not find your information. Please try again.", 'warning')
            return redirect(url_for('payment_routes.identify_client'))

        url = os.environ.get('BASE_URL')
        url = enrich_url(url, client)
        return redirect(url, code=302)

    form = ClientIdForm(request.form)
    return render_template("client_id.html", form=form)


def enrich_url(base_url, client_doc) -> str:
    """
    Add payment form API parameters for this client.
    """
    url = base_url
    try:
        url = f'{url}?reference={client_doc["reference"]}'
        url = f'{url}&name={client_doc["client_name"]}'
        url = f'{url}&address1={client_doc["address1"]}'
        url = f'{url}&city={client_doc["city"]}'
        url = f'{url}&state={client_doc["state"]}'
        url = f'{url}&postal_code={client_doc["postal_code"]}'
        url = f'{url}&amount={client_doc["payment_due"]}'
        url = f'{url}&email={client_doc["email"]}'
    except KeyError as e:
        logger = get_logger('payment_routes')
        logger.warn("Error creating redirect url:", e)

    return url


def correct_check_digit(ssn: str, dl: str) -> str:
    s = f'{ssn}{dl}'
    total = 0
    try:
        for letter in s:
            total += int(letter)
    except ValueError:
        return ''

    check_index = total % 26
    return 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[check_index]
