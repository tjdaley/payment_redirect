"""
crm_routes.py - Direct a client to the payment page

Copyright (c) 2020 by Thomas J. Daley. All Rights Reserved.
"""
import datetime as dt
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, json, jsonify, send_file, Response
import io
import json  # noqa
from mailmerge import MailMerge
import msftconfig
import random
import os
from csutils import combined_payment_schedule, payments_made, compliance_report, violations, enforcement_report

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.db_admins import DbAdmins
from util.database import multidict2dict
from util.db_clients import DbClients, intake_to_client
from util.db_client_discovery import DbClientDiscovery
from util.db_clients_contacts import DbClientsContacts
from util.db_client_notes import DbClientNotes
from util.db_contacts import DbContacts
from util.flatten_dict import flatten_dict
from util.db_intake import DbIntakes
import views.decorators as DECORATORS
from util.court_directory import CourtDirectory
from util.dialer import Dialer
from util.template_name import template_name
from util.logger import get_logger
from views.crm.forms.client_tabs import client_tabs
from views.crm.plan_templates import PlanTemplates
from util.msftgraph import MicrosoftGraph
from util.userlist import Users
# pylint: enable=no-name-in-module
# pylint: enable=import-error
# from util.logger import get_logger
from views.admin.forms.ClientForm import ChildForm, ClientForm, ContactForm
DBADMINS = DbAdmins()
DBCONTACTS = DbContacts()
DBCLIENTS = DbClients()
DBCLIENT_CONTACTS = DbClientsContacts()
DBDISCOVERY = DbClientDiscovery()
DBNOTES = DbClientNotes()
DBINTAKES = DbIntakes()
MSFT = MicrosoftGraph()
PLAN_TEMPLATES = PlanTemplates()
USERS = None
LOGGER = get_logger('crm_routes')


# Refresh court directory information on restart
# CourtDirectory.process()
DIRECTORY = CourtDirectory()

crm_routes = Blueprint('crm_routes', __name__, template_folder='templates')

@crm_routes.route('/client_tools/<string:client_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def client_tools(client_id: str):
    user_email = session['user']['preferred_username']
    user = DBADMINS.admin_record(user_email)
    client = DBCLIENTS.get_one(client_id)
    authorizations = _get_authorizations(user_email)
    return render_template(
        'crm/tools.html',
        client=client,
        authorizations=authorizations
    )


@crm_routes.route('/crm/client_contacts/<string:client_id>/<int:page_num>/', methods=['GET'])
@crm_routes.route('/crm/client_contacts/<string:client_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def list_client_contacts(client_id, page_num: int = 1):
    user_email = session['user']['preferred_username']
    contacts = _client_contacts(user_email, client_id)
    cl_name = DBCLIENTS.get_client_name(client_id)
    email_subject = DBCLIENTS.get_email_subject(client_id)
    authorizations = _get_authorizations(user_email)
    return render_template(
        'crm/contacts.html',
        contacts=contacts,
        authorizations=authorizations,
        prev_page_num=page_num - 1,
        next_page_num=page_num + 1,
        client_name=cl_name,
        email_subject=email_subject,
        client_id=client_id
    )


@crm_routes.route('/crm/contacts', methods=['GET'])
@crm_routes.route('/crm/contacts/<int:page_num>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def list_contacts(page_num: int = 1):
    user_email = session['user']['preferred_username']
    user = DBADMINS.admin_record(user_email)
    user_ccs = user.get('default_cc_list', '').split(',')
    contacts = DBCONTACTS.get_list(user_email, page_num=page_num)
    for contact in contacts:
        contact_ccs = contact.get('cc_list', '').split(',')
        contact['cc_list'] = ';'.join(user_ccs + contact_ccs)

    authorizations = _get_authorizations(user_email)
    return render_template(
        'crm/contacts.html',
        contacts=contacts,
        authorizations=authorizations,
        prev_page_num=page_num - 1,
        next_page_num=page_num + 1,
        client_name=None,
        email_subject=''
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
    form = ContactForm()
    form.process(formdata=request.form)

    if form.validate():
        fields = form.data
        fields['_id'] = request.form.get('_id', '0')
        user_email = session['user']['preferred_username']
        result = DBCONTACTS.save(user_email, fields)
        if result['success']:
            css_name = 'success'
        else:
            css_name = 'danger'
        flash(result['message'], css_name)
        return redirect(url_for('crm_routes.list_contacts'))

    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    return render_template('crm/client.html', client=fields, form=form, operation="Correct", tabs=client_tabs, authorizations=authorizations)


@crm_routes.route('/crm/contact/search/<int:page_num>/', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def search_contacts(page_num: int = 1):
    user_email = session['user']['preferred_username']
    query = request.form.get('query', None)
    client_id = request.form.get('client_id')
    if client_id == '0':
        client_id = None
    if query:
        contacts = DBCONTACTS.search(user_email, query=query, page_num=page_num, client_id=client_id)
    else:
        contacts = DBCONTACTS.get_list(user_email, page_num=page_num, client_id=client_id)
    authorizations = _get_authorizations(user_email)

    if client_id:
        cl_name = DBCLIENTS.get_client_name(client_id)
        email_subject = DBCLIENTS.get_email_subject(client_id)
    else:
        cl_name = None
        email_subject = None
    return render_template(
        'crm/contacts.html',
        contacts=contacts,
        authorizations=authorizations,
        prev_page_num=page_num - 1,
        next_page_num=page_num + 1,
        client_name=cl_name,
        email_subject=email_subject,
        client_id=client_id
    )


@crm_routes.route('/crm/contact/<string:contact_id>/', methods=['GET'])
@crm_routes.route('/crm/contact/<string:contact_id>/<string:client_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def show_contact(contact_id: str, client_id: str = '0'):
    form = ContactForm(request.form)
    user_email = session['user']['preferred_username']
    contact = DBCONTACTS.get_one(contact_id)
    form.name.title.data = contact.get('name', {}).get('title', None)
    form.address.state.data = contact.get('address', {}).get('state', None)
    authorizations = _get_authorizations(user_email)
    return render_template('crm/contact.html', contact=contact, client_id=client_id, authorizations=authorizations, form=form)


@crm_routes.route('/crm', methods=['GET'])
@crm_routes.route('/clients', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def list_clients():
    user_email = session['user']['preferred_username']
    user = DBADMINS.admin_record(user_email)
    clients = DBCLIENTS.get_list(user_email)
    authorizations = _get_authorizations(user_email)
    for client in clients:
        client['_class'] = _client_row_class(client)
        client['_email_subject'] = DBCLIENTS.get_email_subject(client['_id'])
        client['_notes_flag'] = DBNOTES.has_any(client['_id'])
        client['_discovery_flag'] = DBDISCOVERY.has_any(client['_id'])
    return render_template(
        'crm/clients.html',
        clients=clients,
        default_cc_list=user.get('default_cc_list'),
        authorizations=authorizations,
        show_crm_state=False)


@crm_routes.route('/crm/clients/search/<int:page_num>/', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def search_clients(page_num: int = 1):
    user_email = session['user']['preferred_username']
    query = request.form.get('query', None)
    if query:
        clients = DBCLIENTS.search(user_email, query=query, page_num=page_num, crm_state='*')
    else:
        clients = DBCLIENTS.get_list(user_email)
    authorizations = _get_authorizations(user_email)

    return render_template(
        'crm/clients.html',
        clients=clients,
        authorizations=authorizations,
        show_crm_state=True
    )


@crm_routes.route("/crm/client/add/", methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def add_client():
    form = ClientForm(request.form)
    child_form = ChildForm()  # Blank form for adding new children
    user_email = session['user']['preferred_username']
    user = DBADMINS.admin_record(user_email)
    authorizations = _get_authorizations(user_email)

    client = {'_id': '0'}
    client['address'] = {}
    client['name'] = {}
    default_access_list = user.get('default_access_list', user_email).lower()
    if user_email.lower() not in default_access_list:
        default_access_list = ",".join([user_email.lower(), default_access_list])
    return render_template(
        "crm/client.html",
        client=client,
        form=form,
        new_child=child_form,
        operation="Add New",
        default_admins=default_access_list,
        default_cc_list=user.get('default_cc_list', ''),
        tabs=client_tabs,
        authorizations=authorizations
    )


@crm_routes.route("/crm/client/save/", methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def save_client():
    form = ClientForm()
    form.process(formdata=request.form)

    if form.validate():
        fields = form.data
        fields['_id'] = request.form.get('_id', '0')
        user_email = session['user']['preferred_username']
        result = DBCLIENTS.save(fields, user_email)
        if result['success']:
            css_name = 'success'
        else:
            css_name = 'danger'
        flash(result['message'], css_name)
        return redirect(url_for('crm_routes.list_clients'))

    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    our_pay_url = os.environ.get('OUR_PAY_URL', None)
    child_form = ChildForm()
    return render_template(
        'crm/client.html',
        client=form.data,
        form=form,
        new_child=child_form,
        our_pay_url=our_pay_url,
        operation="Correct",
        tabs=client_tabs,
        authorizations=authorizations
    )


@crm_routes.route('/crm/client/<string:id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def show_client(id):
    form = ClientForm(request.form)
    child_form = ChildForm()
    user_email = session['user']['preferred_username']
    user = DBADMINS.admin_record(user_email)
    client = DBCLIENTS.get_one(id)
    _cleanup_client(client)
    form.process(data=client)

    form.court_type.choices = DIRECTORY.get_court_type_tuples(client.get('case_county'))
    form.court_name.choices = DIRECTORY.get_court_tuples(client.get('case_county'), client.get('court_type'))

    authorizations = _get_authorizations(user_email)
    our_pay_url = os.environ.get('OUR_PAY_URL', None)
    contacts = _client_contacts(user_email, id)
    email_subject = DBCLIENTS.get_email_subject(id)
    return render_template(
        'crm/client.html',
        client=client,
        form=form,
        new_child=child_form,
        our_pay_url=our_pay_url,
        default_cc_list=user.get('default_cc_list', ''),
        tabs=client_tabs,
        contacts=contacts,
        email_subject=email_subject,
        authorizations=authorizations
    )


@crm_routes.route('/crm/notes/add/', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def add_note():
    
    client_id = fields.get('clients_id', None)
    client = DBCLIENTS.get_one(client_id)
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
        (user.get('prompt_on_dial_flag', 'N') == 'Y'),
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


@crm_routes.route('/crm/util/update_contact_role', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def update_contact_role():
    user_email = session['user']['preferred_username']
    fields = multidict2dict(request.form)
    result = DBCLIENT_CONTACTS.update_role(user_email, fields['id'], fields['role'])
    return jsonify(result)


@crm_routes.route('/crm/util/assign_contact/<string:contact_id>/<string:client_id>/', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def assign_contact_to_client(contact_id: str, client_id: str):
    user_email = session['user']['preferred_username']
    fields = multidict2dict(request.form)
    fields['contacts_id'] = contact_id
    fields['clients_id'] = client_id
    result = DBCLIENT_CONTACTS.save(user_email, fields)
    return jsonify(result)


@crm_routes.route('/crm/util/unassign_contact/<string:contact_id>/<string:client_id>/')
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def unassign_contact_from_client(contact_id: str, client_id: str):
    user_email = session['user']['preferred_username']
    result = DBCLIENT_CONTACTS.unlink(user_email, client_id, contact_id)
    return jsonify(result)


@crm_routes.route('/crm/util/save_intake', methods=['POST'])
def save_intake():
    data = request.get_json(silent=True)
    result = DBINTAKES.save(data)

    # upsert_id is not none if this was a brand new record
    if result.get('upsert_id', None):
        client_doc = intake_to_client(data)
        client_doc['_id'] = '0'
        client_doc['crm_state'] = '040:consult_scheduled'
        DBCLIENTS.save(client_doc)
    return jsonify(result)


@crm_routes.route('/crm/util/update_intake', methods=['POST'])
def update_intake():
    data = request.get_json(silent=True)
    result = DBINTAKES.save(data)

    # upsert_id is not none if this was a brand new record
    if result.get('modified', 0) == 0:
        client_doc = intake_to_client(data)
        client_doc['_id'] = '0'
        result = DBCLIENTS.save(client_doc, 'tdaley@koonsfuller.com')

    return jsonify(result)


@crm_routes.route('/crm/util/contacts/csv/', methods=['GET'])
@crm_routes.route('/crm/util/contacts/csv/<string:client_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_download_contacts
def download_contacts(client_id: str = ''):
    user_email = session['user']['preferred_username']  # noqa
    contacts = DBCONTACTS.get_list_as_csv(user_email, client_id=client_id)
    return Response(
        contacts,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=contacts.csv'
        }
    )


@crm_routes.route('/crm/util/client_letter/<string:client_id>/', methods=['GET'])
@DECORATORS.is_logged_in
def client_letter(client_id: str):
    user_email = session['user']['preferred_username']  # noqa
    client = DBCLIENTS.get_one(client_id)
    flat_client = flatten_dict(client)
    template_file_name = template_name('letterhead', user_email)
    merged_file_name = os.path.join(os.environ.get('DOCX_PATH'), f'tmp-{user_email}-letterhead.docx')
    today = _get_filename_date()
    attachment_name = f"{flat_client['name_last_name']} - {today} - Letter to {flat_client['name_full_name']}.docx"

    try:
        with MailMerge(template_file_name) as document:
            document.merge(**flat_client)
            document.write(merged_file_name)
        return send_file(merged_file_name, as_attachment=True, cache_timeout=30, attachment_filename=attachment_name)
    except Exception as e:
        LOGGER.error("Error merging client letter: %s", str(e))
        LOGGER.error("\tUser Email: %s", user_email)
        LOGGER.error("\tTemplate  : %s", template_file_name)
        LOGGER.error("\tMerged    : %s", merged_file_name)
    flash("Error merging client letter - Check logs.", 'danger')
    return redirect(url_for('crm_routes.list_clients'))


@crm_routes.route('/crm/util/contact_letter/<string:contact_id>/<string:client_id>/', methods=['GET'])
@DECORATORS.is_logged_in
def contact_letter(contact_id: str, client_id: str):
    user_email = session['user']['preferred_username']  # noqa
    client = DBCLIENTS.get_one(client_id)
    contact = DBCONTACTS.get_one(contact_id)

    # Copy some client fields into the contact document so they are
    # available for the merge operation.
    client_fields = ['case_style', 'case_county', 'cause_number', 'court_name']
    if client:
        for cf in client_fields:
            contact[cf] = client[cf]
        client_name = f"{client['name']['last_name']} - "
    else:
        client_name = ''

    # Flatten dictionary andn do the merge.
    flat_contact = flatten_dict(contact)
    today = _get_filename_date()
    attachment_name = f"{client_name}{today} - Letter to {flat_contact['name_full_name']}.docx"
    template_file_name = template_name('contact-letterhead', user_email)
    merged_file_name = os.path.join(os.environ.get('DOCX_PATH'), f'tmp-{user_email}-letterhead.docx')

    try:
        with MailMerge(template_file_name) as document:
            document.merge(**flat_contact)
            document.write(merged_file_name)
        return send_file(merged_file_name, as_attachment=True, cache_timeout=30, attachment_filename=attachment_name)
    except Exception as e:
        LOGGER.error("Error merging client letter: %s", str(e))
        LOGGER.error("\tUser Email: %s", user_email)
        LOGGER.error("\tTemplate  : %s", template_file_name)
        LOGGER.error("\tMerged    : %s", merged_file_name)
    flash("Error merging contact letter - Check logs.", 'danger')
    return redirect(url_for('crm_routes.list_clients'))


@crm_routes.route('/crm/data/client_ids/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def get_client_ids():
    user_email = session['user']['preferred_username']
    client_ids = DBCLIENTS.get_id_name_list(user_email, crm_state='070:retained_active')

    # jsonify() will sort client_ids by the key value, which we don't want.
    # To maintain the order of the data without messing with global app settings,
    # we create our own json string and build a response object.
    json_string = json.dumps(client_ids, sort_keys=False)
    response = Response(json_string, status=200, mimetype='application/json')
    return response


@crm_routes.route('/crm/data/contact/vcard/<string:contact_id>/<string:type_name>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_download_vcards
def get_vcard(contact_id, type_name):
    contact = DBCONTACTS.get_one(contact_id)
    vcard = _vcard(contact, (type_name == 'pro'))
    vcard_name = _vcard_name(contact)
    fp = io.BytesIO(vcard.encode())
    fp.seek(0)
    return send_file(fp, as_attachment=True, attachment_filename=vcard_name)


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


@crm_routes.route('/crm/data/plan/get/<string:client_id>/')
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def get_client_plan(client_id):
    user_email = session['user']['preferred_username']
    plan_id = _client_plan_id(client_id, user_email)
    if not plan_id:
        return {'success': True, 'plan_found': False, 'message': f"Plan not found for client {client_id}"}
    endpoint = msftconfig.AZURE_PLANNER_PLAN_ENDPOINT.replace('[plan-id]', plan_id)
    # planner_plan = MSFT.graphcall(endpoint)

    plan = []
    endpoint = msftconfig.AZURE_PLANNER_BUCKETS_ENDPOINT.replace(
        '[plan-id]', plan_id)
    buckets = MSFT.graphcall(endpoint).get('value', [])

    for bucket in buckets:
        tasks = _load_bucket_tasks(bucket.get('id'))
        plan.append({'title': bucket.get('name'), 'tasks': tasks})

    return jsonify(plan)


@crm_routes.route('/crm/data/plan/create/<string:client_id>/<int:plan_type>/')
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def create_plan(client_id: str, plan_type: int):
    """
    Create a plan based on a template.

    Args:
        client_id (str): Client's billing ID
        plan_type (int): One of the plan_templates enumeration values
    """
    user_email = session['user']['preferred_username']
    template = PLAN_TEMPLATES.get(plan_type)
    if not template:
        return jsonify({'success': False, 'message': f"Unable to load template of type {plan_type}"})

    # Our reference names are a little different.
    # Our Lingo            Microsoft Planner
    # --------------       -----------------
    # Client               Plan
    # Plan                 Bucket
    # Task                 Task
    result = MSFT.create_bucket_from_template(_client_plan_id(client_id, user_email), template)
    return jsonify(result)


def _load_bucket_tasks(bucket_id: str) -> list:
    """
    Load a list of tasks for this bucket.
    """
    endpoint = msftconfig.AZURE_PLANNER_BUCKET_TASKS_ENDPOINT.replace('[id]', bucket_id)
    graph_tasks = MSFT.graphcall(endpoint).get('value', [])
    tasks = []
    for task in graph_tasks:
        print('* ' * 40)
        print(task)
        due_date = task.get('dueDateTime', '')
        title = task.get('title', '')
        assigned_str = _decode_task_assignments(task.get('assignments', {}))
        tasks.append({
            'title': title,
            'assigned_to': assigned_str,
            'due_date': due_date,
            'start_date': task.get('startDateTime') or '____________________',
            'percent_complete': task.get('percentComplete'),
            'complete_date': task.get('completedDateTime') or '____________________'
        })
    return tasks


def _decode_task_assignments(assignments: dict):
    """
    The assignments are a dict where the keys are user ids.
    You might have expected a list of assignments. But that's not MSFT implemented this.
    """
    _load_user_list()
    users = []
    for user_id, assignment in assignments.items():
        users_name = USERS.get_field(user_id, USERS.UserFields.FIRST_NAME)
        users.append(users_name)
    return '(' + ', '.join(users) + ')'


def _load_user_list():
    # If this is our first authenticated user, populate the users list.
    try:
        global USERS
        if not USERS:
            USERS = Users(MSFT.graphcall(msftconfig.AZURE_USERS_ENDPOINT))
    except Exception as e:
        print(str(e))


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


def _get_filename_date():
    """
    Returns the date in YYYY.MM.DD format for use in file names.
    """
    return dt.datetime.today().strftime('%Y.%m.%d')


def _get_authorizations(user_email: str) -> list:
    database = DbAdmins()
    return database.authorizations(user_email)


def _vcard_name(contact: dict) -> str:
    """
    Create the file name for a vcard from this contact.
    """
    name = contact.get('name', {})
    title = name.get('title', '')
    fname = name.get('first_name', '')
    mname = name.get('middle_name', '')
    lname = name.get('last_name', '')
    suffix = name.get('suffix', '')
    fullname = f'{title}_{fname}_{mname}_{lname}'
    if suffix:
        fullname += '_' + suffix
    fullname = fullname.strip().replace(',', '_').replace('.', '_').replace('__', '_')
    return fullname + '.vcf'


def _vcard40(contact: dict, is_pro: bool) -> str:
    """
    Create a vcard from a contact dict.

    Args:
        contact (dict): Contact properties
        is_pro (bool): Whether to format for sharing with a fellow professional.
            If True, then vcard will include cell phone and email. Otherwise those
            properties are not shared with non-professionals.
    Returns:
        (str): VCard string

    Ref:
        https://en.wikipedia.org/wiki/VCard#vCard_4.0
    """
    name = contact.get('name', {})
    title = name.get('title', '')
    fname = name.get('first_name', '')
    mname = name.get('middle_name', '')
    lname = name.get('last_name', '')
    suffix = name.get('suffix', '')
    fullname = f'{title} {fname} {mname} {lname}'
    if suffix:
        fullname += ', ' + suffix
    fullname = fullname.strip().replace('  ', ' ')
    org = contact.get('organization')
    jtitle = contact.get('job_title')
    telephone = contact.get('office_phone')
    fax = contact.get('fax')
    cell = contact.get('cell_phone')
    email = contact.get('email')
    address = contact.get('address', {})
    street = address.get('street', '')
    city = address.get('city', '')
    state = address.get('state', '')
    country = address.get('country', 'United States of America')
    postal_code = address.get('postal_code')
    note = contact.get('email_cc', None)

    vcard = []
    vcard.append('BEGIN:VCARD')
    vcard.append('VERSION:4.0')
    vcard.append('KIND:individual')
    vcard.append(f'N:{lname};{fname};{mname};{title}')
    vcard.append(f'FN:{fullname}')
    if org:
        vcard.append(f'ORG:{org}')
    if jtitle:
        vcard.append(f'TITLE:{jtitle}')
    if telephone:
        vcard.append(f'TEL;TYPE=work,voice:{telephone}')
    if fax:
        vcard.append(f'TEL;TYPE=work,fax:{fax}')
    if cell and is_pro:
        vcard.append(f'TEL;TYPE=cell,text,voice:{cell}')
    if email and is_pro:
        vcard.append(f'EMAIL:{email}')

    addr_label = f'{street}\\n{city}, {state} {postal_code}\\n{country}'
    addr_parts = f'{street};{city};{state};{postal_code};{country}'
    vcard.append(f'ADR;WORK:;;{addr_parts}\nLABEL;WORK;PREF;ENCODING=QUOTED-PRINTABLE:{addr_label}')
    # vcard.append(f'ADR;TYPE=WORK;PREF=1;LABEL={addr_label};;{addr_parts}')

    if note and is_pro:
        vcard.append(f'NOTE:Requests that emails be copied to: {note}')
    vcard.append('END:VCARD')
    return '\r\n'.join(vcard)


def _vcard21(contact: dict, is_pro: bool) -> str:
    """
    Create a vcard from a contact dict.

    Args:
        contact (dict): Contact properties
        is_pro (bool): Whether to format for sharing with a fellow professional.
            If True, then vcard will include cell phone and email. Otherwise those
            properties are not shared with non-professionals.
    Returns:
        (str): VCard string

    Ref:
        https://en.wikipedia.org/wiki/VCard#vCard_4.0
    """
    name = contact.get('name', {})
    title = name.get('title', '')
    fname = name.get('first_name', '')
    mname = name.get('middle_name', '')
    lname = name.get('last_name', '')
    suffix = name.get('suffix', '')
    fullname = f'{title} {fname} {mname} {lname}'
    if suffix:
        fullname += ', ' + suffix
    fullname = fullname.strip().replace('  ', ' ')
    org = contact.get('organization')
    jtitle = contact.get('job_title')
    telephone = contact.get('office_phone')
    fax = contact.get('fax')
    cell = contact.get('cell_phone')
    email = contact.get('email')
    address = contact.get('address', {})
    street = address.get('street', '')
    city = address.get('city', '')
    state = address.get('state', '')
    country = address.get('country', 'United States of America')
    postal_code = address.get('postal_code')
    note = contact.get('email_cc', None)

    vcard = []
    vcard.append('BEGIN:VCARD')
    vcard.append('VERSION:2.1')
    vcard.append(f'N:{lname};{fname};{mname};{title}')
    vcard.append(f'FN:{fullname}')
    if org:
        vcard.append(f'ORG:{org}')
    if jtitle:
        vcard.append(f'TITLE:{jtitle}')
    if telephone:
        vcard.append(f'TEL;WORK;VOICE:{telephone}')
    if fax:
        vcard.append(f'TEL;WORK;FAX:{fax}')
    if cell and is_pro:
        vcard.append(f'TEL;CELL;TEXT:{cell}')
    if email and is_pro:
        vcard.append(f'EMAIL;PREF;WORK:{email}')

    addr_label = f'{street}=0D=0A=\n{city}, {state} {postal_code}=0D=0A{country}'
    addr_parts = f'{street};{city};{state};{postal_code};{country}'
    vcard.append(f'ADR;WORK:;;{addr_parts}\nLABEL;WORK;PREF;ENCODING=QUOTED-PRINTABLE;CHARSET-UTF-8:{addr_label}')
    # vcard.append(f'ADR;TYPE=WORK;PREF=1;LABEL={addr_label};;{addr_parts}')

    if note and is_pro:
        vcard.append(f'NOTE:Requests that emails be copied to: {note}')
    vcard.append('END:VCARD')
    return '\r\n'.join(vcard)


def _vcard(contact: dict, is_pro: bool) -> str:
    return _vcard21(contact, is_pro)


def _client_contacts(user_email: str, client_id: str) -> list:
    """
    Get a list of contacts linked to the given client account.

    Args:
        user_email (str): Email of the logged-in user.
        client_id (str): String version of the ObjectId identifying the record in the clients collection.

    Returns:
        (list): List of contact objects.
    """
    # See if we have a client-specific set of emails to CC
    client = DBCLIENTS.get_one(client_id)
    our_cc_str = client.get('email_cc_list')

    # If not, then use the default email CC list for this user
    if not our_cc_str:
        user = DBADMINS.admin_record(user_email)
        our_cc_str = user.get('default_cc_list')

    # Combine our CC list into the CC list for this contact
    our_ccs = our_cc_str.split(',')
    contacts = DBCLIENT_CONTACTS.get_list(user_email, clients_id=client_id)
    if contacts is None:
        return []

    for contact in contacts:
        contact_ccs = (contact.get('email_cc', '')).split(',')
        contact['cc_list'] = ';'.join(our_ccs + contact_ccs)

    return contacts


def _client_plan_id(client_id: str, user_email: str) -> str:
    """
    Retrieve id of Microsoft planner plan associated with this client.

    Have we saved the plan id to the client record?
        YES: Verify that plan id is still valid.
            YES: Return plan id
            NO : Clear plan id from client record, search as per below
        NO : Is client id found in any of the plans?
            YES: Save that plan ID to the client's record and return the plan id
            NO : Return None
    """
    plan_key = 'm365_plan_id'
    client = DBCLIENTS.get_by_billing_id(client_id)
    if not client:
        return None

    plan_id = client.get(plan_key, None)
    if plan_id:
        if _validate_plan_id(plan_id):
            return plan_id
        client[plan_key] = None
        DBCLIENTS.save(client, user_email)

    plan_id = _search_client_plan_id(client_id)
    if plan_id:
        client[plan_key] = plan_id
        DBCLIENTS.save(client, user_email)

    return plan_id


def _validate_plan_id(plan_id: str) -> bool:
    """
    Verify that the given plan id exists and is accessible.
    """
    endpoint = msftconfig.AZURE_PLANNER_PLAN_ENDPOINT.replace('[plan-id]', plan_id)
    graph_response = MSFT.graphcall(endpoint)
    print(graph_response)
    return ('error' not in graph_response)


def _search_client_plan_id(search_client_id):
    """
    Search plans for one relating to this client.

    This searches the title of the plan, looking for the client's
    billing id in parentheses, e.g. "DALEY, Thomas J. (99999)", where "99999"
    is the billing id.

    All of the client plans belong to the same Azure Group.
    """
    group_id = os.environ.get('AZURE_GROUP_ID', '')
    endpoint = msftconfig.AZURE_PLANNER_PLANS_ENDPOINT.replace('[group-id]', group_id)
    graph_data = MSFT.graphcall(endpoint)
    graph_plans = graph_data.get('value', [])

    for plan in graph_plans:
        title = plan.get('title', '')
        open_paren = title.find('(')
        close_paren = title.find(')', open_paren + 1)
        if close_paren > open_paren and open != -1:
            client_id = title[open_paren+1:close_paren]
            if client_id == search_client_id:
                return plan.get('id')
    return None
