"""
crm_routes.py - Direct a client to the payment page

Copyright (c) 2020 by Thomas J. Daley. All Rights Reserved.
"""
import datetime as dt
import os
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, jsonify
import random
import settings
import urllib.parse

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.logger import get_logger
from util.database import Database, correct_check_digit
import views.decorators as DECORATORS
from util.court_directory import CourtDirectory
# pylint: enable=no-name-in-module
# pylint: enable=import-error
from views.admin.forms.ClientForm import ClientForm
DATABASE = Database()
DATABASE.connect()

# Refresh court directory information on restart
CourtDirectory.process()
DIRECTORY = CourtDirectory()

crm_routes = Blueprint('crm_routes', __name__, template_folder='templates')
print("Blueprint root path:", crm_routes.root_path)
print("Template path:", crm_routes.template_folder)


@crm_routes.route('/crm', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def list_clients():
    user_email = session['user']['preferred_username']
    clients = DATABASE.get_clients(user_email)
    authorizations = DATABASE.get_authorizations(user_email)
    for client in clients:
        client['_class'] = _client_row_class(client)
    return render_template('crm/clients.html', clients=clients, authorizations=authorizations)


@crm_routes.route("/crm/client/add/", methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def add_client(id: str = '0'):
    form = ClientForm(request.form)
    user_email = session['user']['preferred_username']
    authorizations = DATABASE.get_authorizations(user_email)

    client = {'_id': id}
    return render_template("crm/client.html", client=client, form=form, operation="Add New", authorizations=authorizations)


@crm_routes.route("/crm/client/save/", methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def save_client():
    form = ClientForm(request.form)
    fields = request.form

    if form.validate():
        user_email = session['user']['preferred_username']
        result = DATABASE.save_client(fields, user_email)
        if result['success']:
            css_name = 'success'
        else:
            css_name = 'danger'
        flash(result['message'], css_name)
        return redirect(url_for('crm_routes.list_clients'))

    user_email = session['user']['preferred_username']
    authorizations = DATABASE.get_authorizations(user_email)
    if form.errors:
        for key, value in form.errors.items():
            print(key, value)
    return render_template('/crm/client.html', client=fields, form=form, operation="Correct", authorizations=authorizations)


@crm_routes.route('/crm/client/<string:id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def show_client(id):
    form = ClientForm(request.form)
    user_email = session['user']['preferred_username']
    client = DATABASE.get_client(id)
    _cleanup_client(client)
    form.state.data = client['state']
    form.case_county.data = client['case_county']
    form.court_type.choices = DIRECTORY.get_court_type_tuples(client['case_county'])
    form.court_type.data = client['court_type']
    form.court_name.choices = DIRECTORY.get_court_tuples(client['case_county'], client['court_type'])
    form.court_name.data = client['court_name']
    authorizations = DATABASE.get_authorizations(user_email)
    return render_template('crm/client.html', client=client, authorizations=authorizations, form=form)


@crm_routes.route('/crm/data/court_types/<string:county>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def get_court_types(county):
    return jsonify(DIRECTORY.get_court_types(county))


@crm_routes.route('/crm/data/court_names/<string:county>/<string:court_type>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def get_court_names(county, court_type):
    return jsonify(DIRECTORY.get_courts(county, court_type))


def _client_row_class(client: dict) -> str:
    """
    Set the row class depending on what's in the client record.

    """
    required_cols = ['trust_balance', 'refresh_trigger']
    for col in required_cols:
        if col not in client:
            return 'light'

    if client['trust_balance'] > client['refresh_trigger']:
        return 'success'
    return 'danger'


def _cleanup_client(client: dict):
    """
    Turn arrays into CSV lists for human editing.
    """
    client['attorney_initials'] = ",".join(client['attorney_initials'])
    client['admin_users'] = ",".join(client['admin_users'])


def _get_greeting():
    """
    Generate a random greeting.
    """
    greetings = [
        "Welcome!!",
        "Good to see you!!",
        f"Good {_get_day_time()}!!",
        "Hello!!"
    ]

    return random.choice(greetings)


def _get_day_time():
    hour = dt.datetime.today().hour
    if hour < 12:
        return "Morning"
    if hour < 17:
        return "Afternoon"
    return "Evening"
