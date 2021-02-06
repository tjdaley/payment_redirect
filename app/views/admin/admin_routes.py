"""
admin_routes.py - Handle the administrative routes.

_See_: https://github.com/Azure-Samples/ms-identity-python-webapp/blob/master/app.py

Copyright (c) 2020 by Thomas J. Daley. All Rights Reserved.
"""
import uuid
import os
from flask import Blueprint, flash, redirect, render_template, request, Response, session, url_for, send_file
import urllib

import views.decorators as DECORATORS
from .forms.ClientForm import ClientForm
from .forms.GlobalSettingsForm import GlobalSettingsForm
from .forms.TemplateForm import TemplateForm
from .forms.UserForm import UserForm
from util.template_manager import TemplateManager
from util.template_name import template_name
from util.email_sender import send_evergreen
from util.file_cache_manager import FileCacheManager
from util.dialer import Dialer
import msftconfig

from util.db_admins import DbAdmins
from util.db_clients import DbClients
from util.database import multidict2dict
from util.db_users import DbUsers
from util.msftgraph import MicrosoftGraph
from util.userlist import Users
DBUSERS = DbUsers()
DBCLIENTS = DbClients()
MSFT = MicrosoftGraph()
USERS = None  # We need an authenticated user before we can populate the list

TEMPLATE_MANAGER = TemplateManager()

admin_routes = Blueprint("admin_routes", __name__, template_folder="templates")
REDIRECT_PATH = os.environ['AZURE_REDIRECT_PATH']
ALLOWED_EXTENSIONS = ['docx']


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
def edit_template(email_template_name):
    form = TemplateForm(request.form)
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    template = TEMPLATE_MANAGER.get_template(user_email, email_template_name)
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
def delete_template(email_template_name):
    user_email = session['user']['preferred_username']
    result = TEMPLATE_MANAGER.delete_template(user_email, email_template_name)  # NOQA
    return redirect(url_for('admin_routes.list_templates'))


@admin_routes.route('/admin/global_settings')
@DECORATORS.is_logged_in
@DECORATORS.auth_edit_global_settings
def global_settings():
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    form = GlobalSettingsForm(request.form)
    return render_template('global_settings.html', authorizations=authorizations, form=form)


@admin_routes.route("/admin/global/save_file/", methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_edit_global_settings
def save_global_file():
    form = GlobalSettingsForm(request.form)
    fields = dict(request.form)

    if form.validate():
        # save letterhead templates, if provided
        saved_files = []
        cache_manager = FileCacheManager()
        if 'letterhead_template' in request.files:
            letterhead_template = request.files['letterhead_template']
            if letterhead_template.filename != '' and _allowed_file(letterhead_template.filename):
                filename = 'default-letterhead.docx'
                file_path = os.path.join(os.environ.get('DOCX_PATH'), filename)
                letterhead_template.save(os.path.join(os.environ.get('DOCX_PATH'), file_path))
                cache_manager.synchronize_file(filename)
                saved_files.append(filename)
        if 'contact_letterhead_template' in request.files:
            letterhead_template = request.files['contact_letterhead_template']
            if letterhead_template.filename != '' and _allowed_file(letterhead_template.filename):
                filename = 'default-contact-letterhead.docx'
                file_path = os.path.join(os.environ.get('DOCX_PATH'), filename)
                letterhead_template.save(os.path.join(os.environ.get('DOCX_PATH'), file_path))
                cache_manager.synchronize_file(filename)
                saved_files.append(filename)
        if 'fee_agreement' in request.files:
            template = request.files['fee_agreement']
            if template.filename != '' and _allowed_file(template.filename):
                filename = 'default-fee-agreement.docx'
                file_path = os.path.join(os.environ.get('DOCX_PATH'), filename)
                template.save(os.path.join(os.environ.get('DOCX_PATH'), file_path))
                cache_manager.synchronize_file(filename)
                saved_files.append(filename)
        if saved_files:
            if len(saved_files) == 1:
                message = "Saved " + saved_files[0]
            else:
                message = "Saved " + ", ".join(saved_files[:-1]) + ", and " + saved_files[-1]
        flash(message, 'success')
        return redirect('/crm')

    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    form.groups.data = request.form['groups']
    form.attorneys.data = request.form['attorneys']
    form.authorizations.data = request.form['authorizations']
    return render_template('user.html', client=fields, form=form, operation="Correct", authorizations=authorizations)


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

        # save letterhead templates, if provided
        cache_manager = FileCacheManager()
        if 'letterhead_template' in request.files:
            letterhead_template = request.files['letterhead_template']
            if letterhead_template.filename != '' and _allowed_file(letterhead_template.filename):
                user_email = fields['email']
                filename = f'{user_email}-letterhead.docx'
                file_path = os.path.join(os.environ.get('DOCX_PATH'), filename)
                letterhead_template.save(os.path.join(os.environ.get('DOCX_PATH'), file_path))
                cache_manager.synchronize_file(filename)
        if 'contact_letterhead_template' in request.files:
            letterhead_template = request.files['contact_letterhead_template']
            if letterhead_template.filename != '' and _allowed_file(letterhead_template.filename):
                user_email = fields['email']
                filename = f'{user_email}-contact-letterhead.docx'
                file_path = os.path.join(os.environ.get('DOCX_PATH'), filename)
                letterhead_template.save(os.path.join(os.environ.get('DOCX_PATH'), filename))
                cache_manager.synchronize_file(filename)
        if 'fee_agreement' in request.files:
            template = request.files['fee_agreement']
            if template.filename != '' and _allowed_file(template.filename):
                user_email = fields['email']
                filename = f'{user_email}-fee-agreement.docx'
                file_path = os.path.join(os.environ.get('DOCX_PATH'), filename)
                template.save(os.path.join(os.environ.get('DOCX_PATH'), filename))
                cache_manager.synchronize_file(filename)
        flash(result['message'], css_name)
        return redirect(url_for('admin_routes.list_users'))

    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    form.groups.data = request.form['groups']
    form.attorneys.data = request.form['attorneys']
    form.authorizations.data = request.form['authorizations']
    return render_template('user.html', client=fields, form=form, operation="Correct", authorizations=authorizations)


@admin_routes.route('/admin/user/get/template/<string:docx_template_name>/<string:user_email>/', methods=['GET'])
@DECORATORS.is_logged_in
def get_user_template(docx_template_name: str, user_email: str):
    filename = template_name(docx_template_name, user_email)
    return send_file(filename, as_attachment=True, cache_timeout=30)


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
    tasklists = MSFT.graphcall(msftconfig.AZURE_TODO_LISTS_ENDPOINT).get('value', [])
    return render_template('user.html', user=user, authorizations=authorizations, tasklists=tasklists, form=form)


@admin_routes.route('/admin/global/get/template/<string:docx_template_name>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_edit_global_settings
def get_global_template(docx_template_name: str):
    filename = template_name(docx_template_name, 'default')
    return send_file(filename, as_attachment=True, cache_timeout=30)


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
    auth_url = MSFT.build_auth_url(scopes=msftconfig.AZURE_SCOPE, state=session['state'])
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
        cache = MSFT.load_cache()
        redirect_uri = os.environ.get('AZURE_REDIRECT_PATH')
        result = MSFT.build_msal_app(
            cache=cache
        ).acquire_token_by_authorization_code(
            request.args['code'],
            scopes=msftconfig.
            AZURE_SCOPE,  # Misspelled scope would cause HTTP 400 error here
            redirect_uri=redirect_uri)
        if 'error' in result:
            return render_template('auth_error.html', result=result)
        session['user'] = result.get('id_token_claims')
        MSFT.save_cache(cache)

    return redirect(url_for('admin_routes.list_clients'))


@admin_routes.route('/logout')
def logout():
    session.clear()
    authority = os.environ['AZURE_AUTHORITY']
    return redirect(
        authority + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True)
    )


@admin_routes.route('/docket')
@DECORATORS.is_logged_in
def docket_report():
    user_email = session['user']['preferred_username']
    authorizations = _get_authorizations(user_email)
    clients = DBCLIENTS.get_list(user_email)
    _load_user_list()
    _load_tasks(clients)
    return render_template("docket.html",
                           clients=clients,
                           authorizations=authorizations,
                           )


@admin_routes.route('/tasklists/')
@DECORATORS.is_logged_in
def get_tasklists():
    return MSFT.browser_graphcall(msftconfig.AZURE_TODO_LISTS_ENDPOINT)


@admin_routes.route('/task/<string:tasklistid>/<string:taskid>/')
@DECORATORS.is_logged_in
def get_task(tasklistid: str, taskid: str):
    endpoint = msftconfig.AZURE_TODO_TASK_ENDPOINT \
        .replace('[todoTaskListId]', tasklistid) \
        .replace('[taskId]', taskid)
    return MSFT.browser_graphcall(endpoint)


@admin_routes.route('/tasks/<string:tasklistid>/')
@DECORATORS.is_logged_in
def get_tasks(tasklistid: str):
    endpoint = msftconfig.AZURE_TODO_TASKS_ENDPOINT.replace('[todoTaskListId]', tasklistid)
    return MSFT.browser_graphcall(endpoint)


@admin_routes.route('/users')
@DECORATORS.is_logged_in
def get_users():
    return MSFT.browser_graphcall(msftconfig.AZURE_USERS_ENDPOINT)


@admin_routes.route('/user/<string:user_id>')
@DECORATORS.is_logged_in
def get_user(user_id: str):
    endpoint = msftconfig.AZURE_USER_ENDPOINT.replace('[id]', user_id)
    return MSFT.browser_graphcall(endpoint)


@admin_routes.route('/plans')
@DECORATORS.is_logged_in
def get_plans():
    group_id = os.environ.get('AZURE_GROUP_ID', '')
    endpoint = msftconfig.AZURE_PLANNER_PLANS_ENDPOINT.replace('[group-id]', group_id)
    return MSFT.browser_graphcall(endpoint)


@admin_routes.route('/plan/<string:planid>')
@DECORATORS.is_logged_in
def get_plan(planid: str):
    endpoint = msftconfig.AZURE_PLANNER_PLAN_ENDPOINT.replace('[plan-id]', planid)
    return MSFT.browser_graphcall(endpoint)


@admin_routes.route('/plan/buckets/<string:planid>/')
@DECORATORS.is_logged_in
def get_plan_buckets(planid: str):
    endpoint = msftconfig.AZURE_PLANNER_BUCKETS_ENDPOINT.replace(
        '[plan-id]', planid)
    return MSFT.browser_graphcall(endpoint)


@admin_routes.route('/plan/bucket/<string:bucketid>/')
@DECORATORS.is_logged_in
def get_plan_bucket(bucketid: str):
    endpoint = msftconfig.AZURE_PLANNER_BUCKET_ENDPOINT.replace('[id]', bucketid)
    return MSFT.browser_graphcall(endpoint)


@admin_routes.route('/plan/bucket/<string:bucketid>/tasks/')
@DECORATORS.is_logged_in
def get_bucket_tasks(bucketid: str):
    endpoint = msftconfig.AZURE_PLANNER_BUCKET_TASKS_ENDPOINT.replace('[id]', bucketid)
    return MSFT.browser_graphcall(endpoint)


def cleanup_client(client: dict):
    """
    Turn arrays into CSV lists for human editing.
    """
    client['attorney_initials'] = ",".join(client['attorney_initials'])
    client['admin_users'] = ",".join(client['admin_users'])


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


def _allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _load_user_list():
    # If this is our first authenticated user, populate the users list.
    try:
        global USERS
        if not USERS:
            print("* " * 40)
            print("Populating USERS")
            print("* " * 40)
            USERS = Users(MSFT.graphcall(msftconfig.AZURE_USERS_ENDPOINT))
    except Exception as e:
        print(str(e))


def _load_plans() -> dict:
    """
    Load a list of plans, indexed by client's billing ID
    There is one plan per client.
    """
    group_id = os.environ.get('AZURE_GROUP_ID', '')
    endpoint = msftconfig.AZURE_PLANNER_PLANS_ENDPOINT.replace('[group-id]', group_id)
    graph_data = MSFT.graphcall(endpoint)
    print('Graph Data for Plans'.center(80, '-'))
    print(graph_data)
    graph_plans = graph_data.get('value', [])
    print('Graph Plans'.center(80, '-'))
    print(graph_plans)
    plans = {}
    for plan in graph_plans:
        title = plan.get('title', '')
        open_paren = title.find('(')
        close_paren = title.find(')', open_paren + 1)
        if close_paren > open_paren and open != -1:
            client_id = title[open_paren+1:close_paren]
            plans[client_id] = {
                'title': title,
                'id': plan.get('id'),
            }
    return plans


def _load_tasks(clients: dict):
    """
    Load all client to-do lists in place.

    Args:
        clients (dict): list of clients for this user.
    """
    plans = _load_plans()
    print('PLANS'.center(80, '-'))
    print(plans)
    for client in clients:
        billing_id = client.get('billing_id')
        _load_client_tasks(client, plans.get(billing_id, []))
    print('Clients'.center(80, '|'))
    print(clients[0])


def _load_client_tasks(client: dict, plan: dict):
    """
    Load all tasks for one client.

    **NOTE**: This method will update the _client_ dict.
    """
    print('Loading Client Tasks for Plan'.center(80, '-'))
    print(plan)
    print(' -' * 40)
    print(client)
    if not plan:
        client['tasks'] = []
        return

    endpoint = msftconfig.AZURE_PLANNER_BUCKETS_ENDPOINT.replace(
        '[plan-id]', plan['id'])
    buckets = MSFT.graphcall(endpoint).get('value', [])
    tasks = []
    for bucket in buckets:
        bucket_tasks = _load_bucket_tasks(bucket.get('id'))
        tasks.append({'bucket_name': bucket.get('name', ''), 'tasks': bucket_tasks})
    client['tasks'] = tasks


def _load_bucket_tasks(bucket_id) -> list:
    """
    Load a list of tasks for this bucket.
    """
    endpoint = msftconfig.AZURE_PLANNER_BUCKET_TASKS_ENDPOINT.replace('[id]', bucket_id)
    graph_tasks = MSFT.graphcall(endpoint).get('value', [])
    tasks = []
    for task in graph_tasks:
        print(' TASK '.center(80, "*"))
        print(task)
        due_date = task.get('dueDateTime', '')
        title = task.get('title', '')
        assigned_str = _decode_task_assignments(task.get('assignments', {}))
        percent_complete = task.get('percentComplete', 0)
        css_classes = __select_css_classes(task.get('appliedCategories', {}))
        tasks.append(
            {
                'title': title,
                'assigned_to': assigned_str,
                'due_date': due_date,
                'percent_complete': percent_complete,
                'css_classes': css_classes
            }
        )
    return tasks


def __select_css_classes(categories: dict):
    """
    Pick a superior css class for this item.
    This assumes the most important category is #1. This is set up in Microsoft Planner at the plan level.
    """
    for task_label in range(1, 7, 1):
        if f'category{task_label}' in categories:
            return f'task_category task_category_{task_label}'
    return 'task_category'

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
