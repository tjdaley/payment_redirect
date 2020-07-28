"""
crm_routes.py - Direct a client to the payment page

Copyright (c) 2020 by Thomas J. Daley. All Rights Reserved.
"""
import datetime as dt
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, jsonify
import json  # noqa
import random
import os

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.db_admins import DbAdmins
from util.database import multidict2dict
from util.db_clients import DbClients
from util.db_client_notes import DbClientNotes
from util.db_contacts import DbContacts
import views.decorators as DECORATORS
from util.court_directory import CourtDirectory
from util.dialer import Dialer
# pylint: enable=no-name-in-module
# pylint: enable=import-error
from views.admin.forms.ClientForm import ClientForm, ContactForm
DBADMINS = DbAdmins()
DBCONTACTS = DbContacts()
DBCLIENTS = DbClients()
DBNOTES = DbClientNotes()


# Refresh court directory information on restart
CourtDirectory.process()
DIRECTORY = CourtDirectory()

crm_routes = Blueprint('crm_routes', __name__, template_folder='templates')


@crm_routes.route('/crm/contacts', methods=['GET'])
@crm_routes.route('/crm/contacts/<int:page_num>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def list_contacts(page_num: int = 1):
    user_email = session['user']['preferred_username']
    contacts = DBCONTACTS.get_list(user_email, page_num=page_num)
    authorizations = _get_authorizations(user_email)
    return render_template(
        'crm/contacts.html',
        contacts=contacts,
        authorizations=authorizations,
        prev_page_num=page_num - 1,
        next_page_num=page_num + 1
    )


@crm_routes.route('/crm/contact/add/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def add_contact():
    form = ContactForm(request.form)
    user_email = session['user']['preferred_username']
    contact = {'_id': '0'}
    contact['address'] = {}
    contact['name'] = {}
    form.address.state.data = "TX"
    authorizations = _get_authorizations(user_email)
    return render_template("crm/contact.html", contact=contact, form=form, operation="Add New", authorizations=authorizations)


@crm_routes.route('/crm/contact/save/', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def save_contact():
    form = ContactForm(request.form)
    fields = multidict2dict(request.form)

    if form.validate():
        user_email = session['user']['preferred_username']
        _update_compound_fields(fields, ['name', 'address'])
        result = DBCONTACTS.save(user_email, fields)
        if result['success']:
            css_name = 'success'
        else:
            css_name = 'danger'
        flash(result['message'], css_name)
        return redirect(url_for('crm_routes.list_contacts'))

    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    return render_template('/crm/client.html', client=fields, form=form, operation="Correct", authorizations=authorizations)


@crm_routes.route('/crm/contact/search/<int:page_num>/', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def search_contacts(page_num: int = 1):
    user_email = session['user']['preferred_username']
    query = request.form.get('query', None)
    if query:
        contacts = DBCONTACTS.search(user_email, query=query, page_num=page_num)
    else:
        contacts = DBCONTACTS.get_list(user_email, page_num=page_num)
    authorizations = _get_authorizations(user_email)
    return render_template(
        'crm/contacts.html',
        contacts=contacts,
        authorizations=authorizations,
        prev_page_num=page_num - 1,
        next_page_num=page_num + 1
    )


@crm_routes.route('/crm/contact/<string:id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def show_contact(id: str):
    form = ContactForm(request.form)
    user_email = session['user']['preferred_username']
    contact = DBCONTACTS.get_one(id)
    form.name.title.data = contact.get('name', {}).get('title', None)
    form.address.state.data = contact.get('address', {}).get('state', None)
    authorizations = _get_authorizations(user_email)
    return render_template('crm/contact.html', contact=contact, authorizations=authorizations, form=form)


@crm_routes.route('/crm', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def list_clients():
    user_email = session['user']['preferred_username']
    clients = DBCLIENTS.get_list(user_email)
    authorizations = _get_authorizations(user_email)
    for client in clients:
        client['_class'] = _client_row_class(client)
    return render_template('crm/clients.html', clients=clients, authorizations=authorizations)


@crm_routes.route("/crm/client/add/", methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def add_client():
    form = ClientForm(request.form)
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)

    client = {'_id': '0'}
    client['address'] = {}
    client['name'] = {}
    return render_template("crm/client.html", client=client, form=form, operation="Add New", authorizations=authorizations)


@crm_routes.route("/crm/client/save/", methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def save_client():
    form = ClientForm(request.form)
    fields = multidict2dict(request.form, ClientForm.get())

    if form.validate():
        user_email = session['user']['preferred_username']
        _update_compound_fields(fields, ['name', 'address'])
        result = DBCLIENTS.save(fields, user_email)
        if result['success']:
            css_name = 'success'
        else:
            css_name = 'danger'
        flash(result['message'], css_name)
        return redirect(url_for('crm_routes.list_clients'))

    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    return render_template('/crm/client.html', client=fields, form=form, operation="Correct", authorizations=authorizations)


@crm_routes.route('/crm/client/<string:id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def show_client(id):
    form = ClientForm(request.form)
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(id)
    _cleanup_client(client)
    notes = DBNOTES.get_list(user_email, id)

    form.address.state.data = client.get('address', {}).get('state', None)
    form.case_county.data = client.get('case_county', None)
    form.court_type.choices = DIRECTORY.get_court_type_tuples(client.get('case_county'))
    form.court_type.data = client.get('court_type', None)
    form.court_name.choices = DIRECTORY.get_court_tuples(client.get('case_county'), client.get('court_type'))
    form.court_name.data = client.get('court_name', None)
    authorizations = _get_authorizations(user_email)
    our_pay_url = os.environ.get('OUR_PAY_URL', None)
    return render_template('crm/client.html', client=client, notes=notes, authorizations=authorizations, form=form, our_pay_url=our_pay_url)


@crm_routes.route('/crm/notes/add/', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def add_note():
    fields = multidict2dict(request.form)
    client_id = fields.get('clients_id', None)
    client = DBCLIENTS.get_one(client_id)
    print(client)
    if not client:
        return jsonify({'success': False, 'message': 'Invalid Client ID'})

    user_email = session['user']['preferred_username']
    fields['created_by'] = user_email
    result = DBNOTES.save(user_email, fields)
    return jsonify(result)


@crm_routes.route('/crm/notes/search/<int:page_num>/', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def search_notes(page_num: int = 1):
    user_email = session['user']['preferred_username']
    query = request.form.get('query', None)
    clients_id = request.form.get('client-id', None)
    client_name = DBCLIENTS.get_client_name(clients_id)
    if query:
        notes = DBNOTES.search(user_email, clients_id, query, page_num)
    else:
        notes = DBNOTES.get_list(user_email, clients_id, page_num=page_num)
    authorizations = _get_authorizations(user_email)
    return render_template(
        'crm/notes.html',
        notes=notes,
        client_id=clients_id,
        client_name=client_name,
        prev_page_num=page_num - 1,
        next_page_num=page_num + 1,
        authorizations=authorizations
    )


@crm_routes.route('/crm/notes/<string:clients_id>/', methods=['GET'])
@crm_routes.route('/crm/notes/<string:clients_id>/<int:page_num>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def show_notes(clients_id, page_num: int = 1):
    user_email = session['user']['preferred_username']
    notes = DBNOTES.get_list(user_email, clients_id, page_num=page_num)
    client_name = DBCLIENTS.get_client_name(clients_id)
    authorizations = _get_authorizations(user_email)
    return render_template(
        'crm/notes.html',
        notes=notes,
        client_id=clients_id,
        client_name=client_name,
        prev_page_num=page_num - 1,
        next_page_num=page_num + 1,
        authorizations=authorizations
    )


@crm_routes.route('/crm/util/dial/<string:to_number>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def dial_number(to_number):
    user_email = session['user']['preferred_username']
    user = DBADMINS.admin_record(user_email)
    token = session.get(Dialer.RING_CENTRAL_SESSION_KEY, None)
    response = Dialer.dial(
        user['ring_central_username'],
        to_number,
        user['ring_central_username'],
        user['ring_central_extension'],
        user['ring_central_password'],
        session_access_token=token
    )
    if response.get('rc_login_needed', False):
        response['redirect'] = url_for('admin_routes.ring_central_login')
    return jsonify(response)


@crm_routes.route('/crm/util/send_message/<string:to_number>/<string:message>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def send_sms_message(to_number, message):
    user_email = session['user']['preferred_username']
    user = DBADMINS.admin_record(user_email)
    token = session.get(Dialer.RING_CENTRAL_SESSION_KEY, None)
    response = Dialer.message(
        user['ring_central_username'],
        to_number,
        user['ring_central_username'],
        user['ring_central_extension'],
        user['ring_central_password'],
        message,
        session_access_token=token
    )
    if response.get('rc_login_needed', False):
        response['redirect'] = url_for('admin_routes.ring_central_login')
    return jsonify(response)


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


@crm_routes.route('/crm/data/save_note/<string:text>/<string:tags>/<string:client_id>/<string:note_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def save_note(text, tags, client_id, note_id):
    user_email = session['user']['preferred_username']
    note = {
        'text': text,
        'tags': tags,
        'clients_id': client_id,
        '_id': note_id
    }

    return jsonify(DBNOTES.save(user_email, note))


def _client_row_class(client: dict) -> str:
    """
    Set the row class depending on what's in the client record.

    """
    required_cols = ['trust_balance', 'refresh_trigger']
    for col in required_cols:
        if col not in client:
            return 'dark'

    try:
        if client['trust_balance'] > client['refresh_trigger']:
            return 'success'
    except TypeError:
        return 'dark'

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


def _update_compound_fields(fields, field_list):
    """
    Compound fields are represented in the request as field names with dashes in the middle.
    For example, name-first_name and name-last_name suggest a structure like this:

        {'name': {'first_name': None, 'last_name': None}}

    This method reorganizes these compound names into compound fields. Thus:

        {'name-first_name': 'Tom', 'name-last_name': 'Daley'}

    becomes:

        {'name': {'first_name': 'Tom', 'last_name': 'Daley'}}

    Args:
        fields (dict): The document object we're working with.
        field_list (list): The prefixes we're looking for, e.g. ['name']
    """
    new_fields = {f: {} for f in field_list}
    del_fields = []

    for field in fields:
        name_parts = str(field).split('-', 2)
        if len(name_parts) == 2:
            if name_parts[0] in field_list:
                new_fields[name_parts[0]][name_parts[1]] = fields[field]
                del_fields.append(field)

    for key, value in new_fields.items():
        fields[key] = value

    for field in del_fields:
        del fields[field]


def _get_authorizations(user_email: str) -> list:
    database = DbAdmins()
    return database.authorizations(user_email)
