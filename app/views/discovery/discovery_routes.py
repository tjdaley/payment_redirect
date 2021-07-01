"""
discovery_routes.py - Handle dicovery-related views.

Copyright (c) 2021 by Thomas J. Daley. All Rights Reserved.
"""
import datetime as dt
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, json, jsonify, send_file, Response
from mailmerge import MailMerge
import os

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.db_admins import DbAdmins
from util.database import multidict2dict
from util.db_clients import DbClients, intake_to_client
from util.db_client_discovery import DbClientDiscovery
import views.decorators as DECORATORS
from util.template_name import template_name
from util.logger import get_logger
from util.flatten_dict import flatten_dict
# pylint: enable=no-name-in-module
# pylint: enable=import-error
DBADMINS = DbAdmins()
DBCLIENTS = DbClients()
DBDISCOVERY = DbClientDiscovery()
LOGGER = get_logger('discovery_routes')


discovery_routes = Blueprint('discovery_routes', __name__, template_folder='templates')

@discovery_routes.route('/discovery/list/<string:client_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def discovery_list(client_id: str):
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    client_name = DBCLIENTS.get_client_name(client_id, True)
    authorizations = DBADMINS.authorizations(user_email)
    discovery_list = DBDISCOVERY.get_list(user_email, client_id)
    return render_template(
        'discovery/list.html',
        client=client,
        client_name=client_name,
        discovery_list=discovery_list,
        authorizations=authorizations
    )

@discovery_routes.route('/discovery/requests/<string:client_id>/<string:discovery_requests_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def discovery_requests(client_id: str, discovery_requests_id: str):
    user_email = session['user']['preferred_username']
    discovery_requests = DBDISCOVERY.get_one(discovery_requests_id)
    if discovery_requests is None:
        flash(f"Discovery requests not found ({discovery_requests_id})")
        return redirect(url_for('discovery_routes.discovery_list', client_id=client_id))

    client = DBCLIENTS.get_one(client_id)
    client_name = DBCLIENTS.get_client_name(client_id, True)
    authorizations = DBADMINS.authorizations(user_email)
    discovery_requests = DBDISCOVERY.get_one(discovery_requests_id)
    return render_template(
        'discovery/requests.html',
        client=client,
        client_name=client_name,
        discovery_requests=discovery_requests,
        authorizations=authorizations
    )

@discovery_routes.route('/discovery/response/<string:client_id>/<string:discovery_requests_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def discovery_response(client_id: str, discovery_requests_id: str):
    user_email = session['user']['preferred_username']  # noqa
    client = DBCLIENTS.get_one(client_id)
    template_file_name = template_name('discovery_responses', user_email)
    merged_file_name = os.path.join(os.environ.get('DOCX_PATH'), f'tmp-{user_email}-discovery_responses.docx')
    doc = DBDISCOVERY.get_one(discovery_requests_id)
    requests = doc.get('requests', [])

    cl_last_name = client.get('name', {}).get('last_name', 'DEFAULT')
    today = _get_filename_date()
    discovery_type = doc.get('discovery_type', 'UNKNOWN')
    attachment_name = f"{cl_last_name} - {today} - {discovery_type} Responses.docx"

    try:
        with MailMerge(template_file_name) as document:
            document.merge_templates(requests, separator='continuous_section')
            document.write(merged_file_name)
        return send_file(merged_file_name, as_attachment=True, cache_timeout=30, attachment_filename=attachment_name)
    except Exception as e:
        LOGGER.error("Error merging discovery responses: %s", str(e))
        LOGGER.error("\tUser Email: %s", user_email)
        LOGGER.error("\tTemplate  : %s", template_file_name)
        LOGGER.error("\tMerged    : %s", merged_file_name)
    flash("Error merging discovery responses - Check logs.", 'danger')
    return redirect(url_for('discovery_routes.discovery_requests', client_id=client_id, discovery_requests_id=discovery_requests_id))

@discovery_routes.route('/discovery/del/request/<string:doc_id>/<string:discovery_requests_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def discovery_del_request(doc_id: str, discovery_requests_id: str):
    user_email = session['user']['preferred_username']
    result = DBDISCOVERY.del_one_request(user_email, doc_id, discovery_requests_id)
    return jsonify(result)

@discovery_routes.route('/discovery/update/request/', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def discovery_update_request():
    user_email = session['user']['preferred_username']
    result = DBDISCOVERY.update_one_request(user_email, multidict2dict(request.form))
    return jsonify(result)

def _get_filename_date():
    """
    Returns the date in YYYY.MM.DD format for use in file names.
    """
    return dt.datetime.today().strftime('%Y.%m.%d')
