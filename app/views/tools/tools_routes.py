"""
tools_routes.py - Direct a client to the payment page

Copyright (c) 2021 by Thomas J. Daley. All Rights Reserved.
"""
from datetime import datetime
from decimal import Decimal
import locale
from csutils.stepdown import stepdown
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, json, jsonify, send_file, Response
from mailmerge import MailMerge
from csutils import combined_payment_schedule, payments_made, compliance_report, violations, enforcement_report
from views.tools.forms.violation_form import ViolationForm
from views.tools.forms.stepdown_form import StepdownForm
from views.tools.templates.tools.cs_utils.combined_payment_schedule import combined_payment_schedule
from views.tools.templates.tools.cs_utils.payments_made import payments_made
from views.tools.templates.tools.cs_utils.compliance_report import compliance_report, enforcement_report, violations

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.db_admins import DbAdmins
from util.db_clients import DbClients
import views.decorators as DECORATORS
from util.logger import get_logger
from views.crm.plan_templates import PlanTemplates
from util.msftgraph import MicrosoftGraph
# pylint: enable=no-name-in-module
# pylint: enable=import-error
# from util.logger import get_logger
DBADMINS = DbAdmins()
DBCLIENTS = DbClients()
MSFT = MicrosoftGraph()
PLAN_TEMPLATES = PlanTemplates()
USERS = None
LOGGER = get_logger('crm_routes')


tools_routes = Blueprint('tools_routes', __name__, template_folder='templates')

@tools_routes.route('/client_tools/<string:client_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def client_tools(client_id: str):
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    authorizations = _get_authorizations(user_email)
    return render_template(
        'tools/tools.html',
        client=client,
        authorizations=authorizations
    )


@tools_routes.route('/client_tools/<string:client_id>/cs_calc', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def cs_calc(client_id: str):
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    authorizations = _get_authorizations(user_email)
    return render_template(
        'tools/cs_calculator.html',
        client=client,
        authorizations=authorizations
    )


@tools_routes.route('/client_tools/<string:client_id>/cs_stepdown', methods=['GET', 'POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def cs_stepdown(client_id: str):
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    authorizations = _get_authorizations(user_email)
    form = StepdownForm(request.form)
    form_data = {
        'payment_amount': form.payment_amount.data or '',
        'children_not_before_court': form.children_not_before_court.data
    }

    if request.method == 'POST' and form.validate():
        stepdown_schedule = stepdown(
            children=_children(client),
            initial_payment_amount=Decimal(form.payment_amount.data),
            num_children_not_before_court=int(form.children_not_before_court.data)
        )
        return render_template(
            'tools/cs_stepdown.html',
            form=form,
            form_data=form_data,
            client=client,
            authorizations=authorizations,
            stepdown_schedule = stepdown_schedule
        )

    return render_template(
        'tools/cs_stepdown.html',
        form=form,
        form_data=form_data,
        client=client,
        authorizations=authorizations,
        stepdown_schedule = []
    )


@tools_routes.route('/client_tools/<string:client_id>/cs_violations', methods=['GET', 'POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def cs_violations(client_id: str):
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    authorizations = _get_authorizations(user_email)
    form = ViolationForm(request.form)
    form_data = {
        'cs_payment_amount': form.cs_payment_amount.data or '0.00',
        'medical_payment_amount': form.medical_payment_amount.data or '0.00',
        'dental_payment_amount': form.dental_payment_amount.data or '0.00',
        'start_date': form.start_date.data or '',
        'payments': form.payments.data or ''
    }

    if request.method == 'POST' and form.validate():
        payments_due = combined_payment_schedule(
            children = [{'name': "Olivia Grace Thomas", 'dob': datetime(2005, 9, 21)}],
            initial_child_support_payment=Decimal(form_data['cs_payment_amount']),
            health_insurance_payment=Decimal(form_data['medical_payment_amount']),
            dental_insurance_payment=Decimal(form_data['dental_payment_amount']),
            confirmed_arrearage=None,
            start_date=form_data['start_date'],
            num_children_not_before_court=0
        )
        payments = payments_made(form_data['payments'])
        report = enforcement_report(payments_due, payments)
        indictments = violations(report)

        return render_template(
            'tools/cs_violations.html',
            form=form,
            form_data=form_data,
            client=client,
            authorizations=authorizations,
            indictments=indictments
        )

    return render_template(
        'tools/cs_violations.html',
        form=form,
        form_data=form_data,
        client=client,
        authorizations=authorizations,
        indictments = []
    )


def _children(client: dict) -> list:
    child_list = client.get('children', [])
    children = [{'name': _name(c['name']), 'dob': _date(c['dob'])} for c in child_list]
    return children


def _date(in_date: str) -> datetime:
    return datetime.strptime(in_date, '%Y-%m-%d')


def _get_authorizations(user_email: str) -> list:
    database = DbAdmins()
    return database.authorizations(user_email)


def _name(name_parts: dict) -> str:
    title = name_parts.get('title', '')
    fname = name_parts.get('first_name', '')
    mname = name_parts.get('middle_name', '')
    lname  = name_parts.get('last_name', '')
    suffix = name_parts.get('suffix', None)
    name = f"{title} {fname} {mname} {lname}".strip().replace('  ', ' ')
    if suffix:
        name += f", {suffix}"
    return name

