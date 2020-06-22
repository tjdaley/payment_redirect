"""
admin_routes.py - Handle the administrative routes.

Copyright (c) 2020 by Thomas J. Daley. All Rights Reserved.
"""
import uuid
import os
import msal
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
import requests

from views.decorators import is_logged_in, is_admin_user
from .forms.ClientForm import ClientForm
import config

from util.database import Database
DATABASE = Database()
DATABASE.connect()

admin_routes = Blueprint("admin_routes", __name__, template_folder="templates")
REDIRECT_PATH = os.environ['AZURE_REDIRECT_PATH']


@admin_routes.route("/clients", methods=['GET'])
@is_logged_in
@is_admin_user
def list_clients():
    user_email = session['user']['preferred_username']
    clients = DATABASE.get_clients(user_email)
    return render_template("clients.html", clients=clients)


@admin_routes.route("/client/<string:id>/", methods=['GET', 'POST'])
@is_logged_in
@is_admin_user
def show_client(id):
    form = ClientForm(request.form)

    if request.method == 'POST':
        if form.validate():
            user_email = session['user']['preferred_username']
            fields = request.form
            result = DATABASE.save_client(fields, user_email)
            if result['success']:
                flash(result['message'], 'success')
                return redirect(url_for('admin_routes.list_clients'))

    client = DATABASE.get_client(id)
    cleanup_client(client)
    return render_template("client.html", client=client, form=form)


@admin_routes.route('/login', methods=['GET'])
def login():
    session['state'] = str(uuid.uuid4())
    auth_url = _build_auth_url(scopes=config.AZURE_SCOPE, state=session['state'])
    return render_template('login.html', auth_url=auth_url, version=msal.__version__)


# REDIRECT_PATH must match your app's redirect_uri set in AAD
@admin_routes.route(REDIRECT_PATH)
def authorized():
    print("Processing authorization")
    if request.args.get('state') != session.get('state'):
        return redirect(url_for(os.environ['LOGIN_FUNCTION']))
    if 'error' in request.args:  # Authentization/Authorization failure
        flash("Login error - Try Again", 'danger')
        return render_template("auth_error.html", result=request.args)
    if request.args.get('code'):
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_authorization_code(
            request.args['code'],
            scopes=config.AZURE_SCOPE,  # Misspelled scope would cause HTTP 400 error here
            redirect_uri=url_for('admin_routes.authorized', _external=True)
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
    return _build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state or str(uuid.uuid4()),
        redirect_uri=url_for("admin_routes.authorized", _external=True))


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
