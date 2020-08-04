"""
admin_routes.py - Handle the administrative routes.

Copyright (c) 2020 by Thomas J. Daley. All Rights Reserved.
"""
import uuid
import os
import msal
from flask import Blueprint, flash, redirect, render_template, request, Response, session, url_for
import requests
import urllib

import views.decorators as DECORATORS
from .forms.ClientForm import ClientForm
from .forms.TemplateForm import TemplateForm
from .forms.UserForm import UserForm
from util.logger import get_logger
from util.template_manager import TemplateManager
from util.email_sender import send_evergreen
from util.dialer import Dialer
import config

from util.db_admins import DbAdmins
from util.db_clients import DbClients
from util.database import multidict2dict
from util.db_users import DbUsers
DBUSERS = DbUsers()
DBCLIENTS = DbClients()

TEMPLATE_MANAGER = TemplateManager()

admin_routes = Blueprint("admin_routes", __name__, template_folder="templates")
REDIRECT_PATH = os.environ['AZURE_REDIRECT_PATH']


@admin_routes.route('/admin/templates')
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
@DECORATORS.auth_manage_templates
def list_templates():
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    templates = TEMPLATE_MANAGER.get_templates(user_email)
    return render_template('templates.html', templates=templates, authorizations=authorizations)


@admin_routes.route('/admin/add_template')
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
@DECORATORS.auth_manage_templates
def add_template():
    form = TemplateForm(request.form)
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    return render_template('template.html', template={}, form=form, authorizations=authorizations)


@admin_routes.route('/admin/template/<string:template_name>/')
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
@DECORATORS.auth_manage_templates
def edit_template(template_name):
    form = TemplateForm(request.form)
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    template = TEMPLATE_MANAGER.get_template(user_email, template_name)
    return render_template('template.html', template=template, form=form, authorizations=authorizations)


@admin_routes.route('/admin/save_template/', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
@DECORATORS.auth_manage_templates
def save_template():
    form = TemplateForm(request.form)
    fields = request.form

    if form.validate():
        user_email = session['user']['preferred_username']
        result = TEMPLATE_MANAGER.save_template(user_email, fields)
        if result['success']:
            css_name = 'success'
        else:
            css_name = 'danger'
        flash(result['message'], css_name)
        return redirect(url_for('admin_routes.list_templates'))
    return render_template('template.html', template=fields, form=form, operation="Correct")


@admin_routes.route('/admin/delete_template/<string:template_name>/')
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
@DECORATORS.auth_manage_templates
def delete_template(template_name):
    user_email = session['user']['preferred_username']
    result = TEMPLATE_MANAGER.delete_template(user_email, template_name)  # NOQA
    return redirect(url_for('admin_routes.list_templates'))


@admin_routes.route('/admin/users')
@DECORATORS.is_logged_in
@DECORATORS.auth_manage_users
def list_users():
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    users = DBUSERS.get_list(user_email)
    return render_template('users.html', users=users, authorizations=authorizations)


@admin_routes.route('/admin/user/add/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_manage_users
def add_user():
    form = UserForm(request.form)
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    user = {'_id': '0'}
    return render_template("user.html", user=user, form=form, operation="Add New", authorizations=authorizations)


@admin_routes.route("/admin/user/save/", methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_manage_users
def save_user():
    form = UserForm(request.form)
    fields = dict(request.form)
    fields['attorneys'] = request.form.getlist('attorneys')
    fields['groups'] = request.form.getlist('groups')
    fields['authorizations'] = request.form.getlist('authorizations')

    if form.validate():
        result = DBUSERS.save(fields)
        if result['success']:
            css_name = 'success'
        else:
            css_name = 'danger'
        flash(result['message'], css_name)
        return redirect(url_for('admin_routes.list_users'))

    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    form.groups.data = request.form['groups']
    form.attorneys.data = request.form['attorneys']
    form.authorizations.data = request.form['authorizations']
    return render_template('user.html', client=fields, form=form, operation="Correct", authorizations=authorizations)


@admin_routes.route('/admin/user/<string:user_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_manage_users
def show_user(user_id):
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    user = DBUSERS.get_one(user_email, user_id=user_id)
    form = UserForm(request.form)
    form.groups.data = user['groups']
    form.attorneys.data = user['attorneys']
    form.authorizations.data = user['authorizations']
    return render_template('user.html', user=user, authorizations=authorizations, form=form)


@admin_routes.route('/admin')  # noqa
@admin_routes.route("/clients", methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
def list_clients():
    user_email = session['user']['preferred_username']
    clients = DBCLIENTS.get_list(user_email)
    authorizations = _get_authorizations(user_email)
    counter = 0
    for client in clients:
        counter += 1
        client['_class'] = 'light'
        message = ''
        if 'trust_balance_update' in client:
            if 'evergreen_sent_date' in client:
                if client['evergreen_sent_date'] < client['trust_balance_update']:
                    client['_class'] = 'success'
                else:
                    message += "Trust balance not updated since last evergreen email sent. Update it. "
                    client['_class'] = 'warning'
        else:
            client['_class'] = 'warning'
            message += "Trust balance needs to be updated. "
        try:
            if float(client.get('payment_due', '0.0')) < 0.0:
                client['_class'] = 'danger'
                message += "Payment due is either missing or negative. Must be a positive number. "
        except ValueError:
            client['_class'] = 'danger'
            message += "Payment due must be a number. "
        client['_message'] = message
        if client.get('mediation_retainer_flag', 'N') == 'Y':
            type = "Mediation retainer due"
        elif client.get('trial_retainer_flag', 'N') == 'Y':
            type = "Trial retainer due"
        elif float(client.get('payment_due', '0.0')) > 0.0:
            type = "Trust refresh due"
        else:
            type = "No payment due (please verify)"
        client['_type'] = type
    return render_template("clients.html", clients=clients, authorizations=authorizations)


@admin_routes.route('/admin/send_evergreen', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
@DECORATORS.auth_send_evergreens
def send_evergreens():
    user_email = session['user']['preferred_username']
    send_evergreen(user_email)
    return redirect(url_for('admin_routes.list_clients'))


@admin_routes.route("/clients/csv/", methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
@DECORATORS.auth_download_clients
def download_clients_csv():
    user_email = session['user']['preferred_username']
    clients = DBCLIENTS.get_list_as_csv(user_email)
    return Response(
        clients,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=clients.csv'
        }
    )


@admin_routes.route("/client/add/", methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
def add_client():
    form = ClientForm(request.form)
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)

    client = {'_id': '0'}
    client['address'] = {}
    client['name'] = {}
    return render_template("client.html", client=client, form=form, operation="Add New", authorizations=authorizations)


@admin_routes.route("/client/save/", methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
def save_client():
    form = ClientForm(request.form)
    fields = multidict2dict(request.form)

    if form.validate():
        user_email = session['user']['preferred_username']
        _update_compound_fields(fields, ['name', 'address'])
        result = DBCLIENTS.save(fields, user_email)
        if result['success']:
            css_name = 'success'
        else:
            css_name = 'danger'
        flash(result['message'], css_name)
        return redirect(url_for('admin_routes.list_clients'))

    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    return render_template('client.html', client=fields, form=form, operation="Correct", authorizations=authorizations)


@admin_routes.route("/client/<string:id>/", methods=['GET', 'POST'])
@DECORATORS.is_logged_in
@DECORATORS.is_admin_user
def show_client(id):
    form = ClientForm(request.form)
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)

    client = DBCLIENTS.get_one(id)
    form.address.state.data = client['address']['state']
    cleanup_client(client)
    our_pay_url = os.environ.get('OUR_PAY_URL')
    return render_template("client.html", client=client, form=form, operation="Update", our_pay_url=our_pay_url, authorizations=authorizations)


# Login Route for RingCentral's Identity Service
# This is only used for RingCentral Integration, such as for initiating calls and sending text reminders
@admin_routes.route('/rclogin', methods=['GET'])
def ring_central_login():
    base_url = os.environ.get('RING_CENTRAL_SERVER', None)
    if base_url is None:
        flash('RING_CENTRAL_SERVER is not defined', 'danger')
        return redirect(url_for('admin_routes.list_clients'))
    base_url += '/restapi/oauth/authorize'
    params = (
        ('response_type', 'code'),
        ('redirect_uri', os.environ.get('RING_CENTRAL_REDIRECT_PATH')),
        ('client_id', os.environ.get('RING_CENTRAL_CLIENTID')),
        ('state', 'initialState')
    )
    auth_url = base_url + '?' + urllib.parse.urlencode(params)
    firm_name = os.environ.get('FIRM_NAME', "The Firm")
    firm_admin_email = os.environ.get('FIRM_ADMIN_EMAIL')
    return render_template('rc_login.html', firm_name=firm_name, auth_url=auth_url, firm_admin_email=firm_admin_email)


# OAuth Redirect for RingCentral's Identity Service
@admin_routes.route('/rcoauth2callback', methods=['GET'])
def ring_central_authorized():
    auth_code = request.values.get('code')
    redirect_url = os.environ.get('RING_CENTRAL_REDIRECT_PATH')
    print('*' * 80)
    print("auth_code   :", auth_code)
    print("redirect_url:", redirect_url)
    print('*' * 80)
    tokens = Dialer.get_oauth_tokens(auth_code, redirect_url)
    session[Dialer.RING_CENTRAL_SESSION_KEY] = tokens
    return redirect(url_for('crm_routes.list_clients'))


# OAuth Logout for RingCentral's Identity Service
@admin_routes.route('/rclogout')
def ring_central_logout():
    token = session[Dialer.RING_CENTRAL_SESSION_KEY]
    Dialer.logout(token)
    return redirect(url_for('crm_routes.list_clients'))


# Login Route for Microsoft's Identity service
# This is our applications login.
@admin_routes.route('/login', methods=['GET'])
def login():
    session['state'] = str(uuid.uuid4())
    auth_url = _build_auth_url(scopes=config.AZURE_SCOPE, state=session['state'])
    firm_name = os.environ.get('FIRM_NAME', "The Firm")
    firm_admin_email = os.environ.get('FIRM_ADMIN_EMAIL')
    return render_template('login.html', firm_name=firm_name, auth_url=auth_url, firm_admin_email=firm_admin_email)


# REDIRECT_PATH must match your app's redirect_uri set in AAD
# OAuth Redirect for Microsoft's Identity Service
@admin_routes.route('/getAToken')
def authorized():
    if request.args.get('state') != session.get('state'):
        return redirect(url_for(os.environ['LOGIN_FUNCTION']))
    if 'error' in request.args:  # Authentization/Authorization failure
        message = request.args.get('error_description', 'Try Again')
        flash(f"Login error - {message}", 'danger')
        return render_template("auth_error.html", result=request.args)
    if request.args.get('code'):
        cache = _load_cache()
        redirect_uri = os.environ.get('AZURE_REDIRECT_PATH')
        result = _build_msal_app(cache=cache).acquire_token_by_authorization_code(
            request.args['code'],
            scopes=config.AZURE_SCOPE,  # Misspelled scope would cause HTTP 400 error here
            redirect_uri=redirect_uri
        )
        if 'error' in result:
            return render_template('auth_error.html', result=result)
        session['user'] = result.get('id_token_claims')
        _save_cache(cache)
    return redirect(url_for('admin_routes.list_clients'))


@admin_routes.route('/logout')
def logout():
    session.clear()
    authority = os.environ['AZURE_AUTHORITY']
    return redirect(
        authority + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True)
    )


def cleanup_client(client: dict):
    """
    Turn arrays into CSV lists for human editing.
    """
    client['attorney_initials'] = ",".join(client['attorney_initials'])
    client['admin_users'] = ",".join(client['admin_users'])


def _build_msal_app(cache=None, authority=None):
    client_id = os.environ['AZURE_CLIENT_ID']
    client_secret = os.environ['AZURE_CLIENT_SECRET']
    config_authority = os.environ['AZURE_AUTHORITY']
    return msal.ConfidentialClientApplication(
        client_id, authority=authority or config_authority,
        client_credential=client_secret, token_cache=cache)


def _build_auth_url(authority=None, scopes: list = None, state=None):
    redirect_uri = os.environ.get('AZURE_REDIRECT_PATH')
    get_logger("pmtredir.admin").info("B %s", redirect_uri)
    return _build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state or str(uuid.uuid4()),
        redirect_uri=redirect_uri)


def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()


def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result


def _get_users():
    token = _get_token_from_cache(config.AZURE_SCOPE)
    if not token:
        return redirect(url_for(os.environ['LOGIN_FUNCTION']))
    graph_data = requests.get(
        config.AZURE_USERS_ENDPOINT,
        headers={'Authorization': 'Bearer ' + token['access_token']},
    ).json()
    return graph_data


def _update_compound_fields(fields, field_list):
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
