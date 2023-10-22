"""
tools_routes.py - Direct a client to the payment page

Copyright (c) 2021 by Thomas J. Daley. All Rights Reserved.
"""
from datetime import datetime
from decimal import Decimal
import os
from flask import Blueprint, render_template, request, session, jsonify
from views.tools.forms.violation_form import ViolationForm
from views.tools.forms.stepdown_form import StepdownForm
from views.tools.templates.tools.cs_utils.combined_payment_schedule import combined_payment_schedule
from views.tools.templates.tools.cs_utils.payments_made import payments_made
from views.tools.templates.tools.cs_utils.compliance_report \
    import enforcement_report, violations
from views.tools.templates.tools.cs_utils.stepdown import stepdown
import views.decorators as DECORATORS
from views.crm.plan_templates import PlanTemplates

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.db_admins import DbAdmins
from util.db_clients import DbClients
from util.logger import get_logger
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


@tools_routes.route('/client_tools/<string:client_id>/load_file', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def load_file(client_id: str):
    """
    Present a form for loading a PDF file for analysis.

    Args:
        client_id (str): Client ID

    Returns:
        HTML response
    """
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    authorizations = _get_authorizations(user_email)
    return render_template(
        'tools/load_file.html',
        client=client,
        authorizations=authorizations
    )


@tools_routes.route('/client_tools/<string:client_id>/save_file', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def save_file(client_id: str):
    """
    Save a PDF file for analysis.

    Args:
        client_id (str): Client ID

    Returns:
        JSON response
    """
    tmp_dir = os.getenv('TMP_DIR')

    if tmp_dir is None:
        LOGGER.error("TMP_DIR environment variable not set")
        return jsonify({'success': False, 'error': 'TMP_DIR environment variable not set'})

    user_email = session['user']['preferred_username']
    # client = DBCLIENTS.get_one(client_id)
    # authorizations = _get_authorizations(user_email)
    file = request.files['file']
    try:
        tmp_file_name = f'{user_email}_{client_id}__{file.filename}'
        tmp_file = os.path.join(tmp_dir, tmp_file_name)
        file.save(tmp_file)
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error("Unexpected error saving file: %s", err)
        LOGGER.debug("File: %s", tmp_file)
        return jsonify({'success': False, 'error': str(err)})
    LOGGER.debug("Saved file: %s", file.filename)
    return jsonify({'success': True, 'doc_id': tmp_file_name})


@tools_routes.route('/client_tools/<string:client_id>/classify', methods=['POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def classify_file(client_id: str):
    """
    Classify a file.

    Args:
        client_id (str): Client ID

    Returns:
        JSON response
    """
    doc_id = request.form['doc_id']
    synchonous = request.form['synchronous'].lower() == 'true'
    return jsonify(
        {
            'success': True,
            'doc_id': doc_id,
            'client_id': client_id,
            'synchronous': synchonous,
            'job_id': '12345'
        }
    )


@tools_routes.route('/client_tools/<string:client_id>/classification/<string:job_id>', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def get_classification(client_id: str, job_id: str):
    """
    Retrieve the classification of a file.

    Args:
        client_id (str): Client ID
        job_id (str): Job ID

    Returns:
        HTML response
    """
    return jsonify(
        {
            'success': True,
            'job_id': job_id,
            'client_id': client_id,
        }
    )

@tools_routes.route('/client_tools/<string:client_id>/', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def client_tools(client_id: str):
    """
    Render the client tools page.
    """
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    authorizations = _get_authorizations(user_email)
    return render_template(
        'tools/tools.html',
        client=client,
        authorizations=authorizations
    )


@tools_routes.route('/client_tools/<string:client_id>/images2pdf', methods=['GET', 'POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def images_to_pdf(client_id: str):
    """
    Save client files to a temp folder. After saving, queue a task to convert the files to PDF.

    """
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    authorizations = _get_authorizations(user_email)
    if request.method == 'GET':
        return render_template(
            'tools/bates_recordings.html',
            client=client,
            authorizations=authorizations
        )

    # POST files to be converted
    files = request.files.getlist('files')
    if not files:
        return render_template(
            'tools/bates_recordings.html',
            client=client,
            authorizations=authorizations,
            error='No files were selected.'
        )
    temp_folder = _save_files(files)
    form_data = request.form()
    conversion_params = {
        'client_id': client_id,
        'user_email': user_email,
        'bates_prefix': form_data.get('bates_prefix', ''),
        'bates_start': form_data.get('bates_start', '1'),
        'bates_increment': form_data.get('bates_increment', '1'),
        'bates_suffix': form_data.get('bates_suffix', ''),
        'bates_digits': form_data.get('bates_digits', '6'),
        'image_date_format': form_data.get('image_date_format', '%Y-%m-%d'),
    }
    _queue_conversion(temp_folder, client_id, user_email, conversion_params)
    return render_template(
        'tools/bates_recordings.html',
        client=client,
        authorizations=authorizations,
        success='Files were uploaded.'
    )


@tools_routes.route('/client_tools/<string:client_id>/cs_calc', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def cs_calc(client_id: str):
    """
    Render the child support calculator page.
    """
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
    """
    Render the child support stepdown page.
    """
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
            stepdown_schedule=stepdown_schedule
        )

    return render_template(
        'tools/cs_stepdown.html',
        form=form,
        form_data=form_data,
        client=client,
        authorizations=authorizations,
        stepdown_schedule=[]
    )


@tools_routes.route('/client_tools/<string:client_id>/cs_violations', methods=['GET', 'POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def cs_violations(client_id: str):
    """
    Render the child support violations page.
    """
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    children = _children(client)
    authorizations = _get_authorizations(user_email)
    form = ViolationForm(request.form)
    form_data = {
        'cs_payment_amount': form.cs_payment_amount.data or '0.00',
        'medical_payment_amount': form.medical_payment_amount.data or '0.00',
        'dental_payment_amount': form.dental_payment_amount.data or '0.00',
        'start_date': form.start_date.data or '',
        'payments': form.payments.data or '',
        'children_not_before_court': form.children_not_before_court.data or '0',
        'payment_interval': int(form.payment_interval.data or 12),
        'violations_only': form.violations_only.data or True
    }

    if request.method == 'POST' and form.validate():
        DBCLIENTS.save(
            {
                '_id': client_id,
                'active_flag': 'Y',
                'cs_tools_enforcement': form_data
            },
            user_email
        )
        payments_due = combined_payment_schedule(
            children=children,
            children=children,
            initial_child_support_payment=Decimal(form_data['cs_payment_amount']),
            health_insurance_payment=Decimal(form_data['medical_payment_amount']),
            dental_insurance_payment=Decimal(form_data['dental_payment_amount']),
            confirmed_arrearage=None,
            start_date=form_data['start_date'],
            num_children_not_before_court=_int(form_data['payment_interval'], 12),
            payment_interval=_int(form_data['payment_interval'])
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
        form_data=client.get('cs_tools_enforcement', form_data),
        client=client,
        authorizations=authorizations,
        indictments=[]
    )


@tools_routes.route('/client_tools/<string:client_id>/cs_arrearage', methods=['GET', 'POST'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def cs_arrearage(client_id: str):
    """
    Render the child support arrearage page.
    """
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    children = _children(client)
    authorizations = _get_authorizations(user_email)
    form = ViolationForm(request.form)
    form_data = {
        'cs_payment_amount': form.cs_payment_amount.data or '0.00',
        'medical_payment_amount': form.medical_payment_amount.data or '0.00',
        'dental_payment_amount': form.dental_payment_amount.data or '0.00',
        'start_date': form.start_date.data or '',
        'payments': form.payments.data or '',
        'children_not_before_court': form.children_not_before_court.data or '0',
        'payment_interval': int(form.payment_interval.data or 12),
        'violations_only': form.violations_only.data or False
    }

    if request.method == 'POST' and form.validate():
        DBCLIENTS.save(
            {
                '_id': client_id,
                'active_flag': 'Y',
                'cs_tools_enforcement': form_data
            },
            user_email
        )
        payments_due = combined_payment_schedule(
            children=children,
            children=children,
            initial_child_support_payment=Decimal(form_data['cs_payment_amount']),
            health_insurance_payment=Decimal(form_data['medical_payment_amount']),
            dental_insurance_payment=Decimal(form_data['dental_payment_amount']),
            confirmed_arrearage=None,
            start_date=form_data['start_date'],
            num_children_not_before_court=_int(form_data['payment_interval'], 12),
            payment_interval=_int(form_data['payment_interval'])
        )
        payments = payments_made(form_data['payments'])
        report = enforcement_report(payments_due, payments)

        # Add up total child support arrearage
        total_arrearages = {}
        for item in report:
            if item.get('remaining_amount', Decimal(0.00)) > 0:
                if item['description'] not in total_arrearages:
                    total_arrearages[item['description']] = Decimal(0.00)
                total_arrearages[item['description']] += item['remaining_amount']


        sum_of_totals = Decimal(0.00)
        for item in total_arrearages:
            sum_of_totals += total_arrearages[item]
        total_arrearages['TOTAL'] = sum_of_totals

        return render_template(
            'tools/cs_arrearage.html',
            form=form,
            form_data=form_data,
            client=client,
            authorizations=authorizations,
            report=report,
            arrearages=total_arrearages
        )

    return render_template(
        'tools/cs_arrearage.html',
        form=form,
        form_data=client.get('cs_tools_enforcement', form_data),
        client=client,
        authorizations=authorizations,
        report=[]
    )


def _int(string: str, default: int = 0) -> int:
    try:
        return int(string)
    except ValueError:
        return default
    except TypeError:
        return default
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error("Unexpected error at _int(): %s", err)
        return default


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
    lname = name_parts.get('last_name', '')
    lname = name_parts.get('last_name', '')
    suffix = name_parts.get('suffix', None)
    name = f"{title} {fname} {mname} {lname}".strip().replace('  ', ' ')
    if suffix:
        name += f", {suffix}"
    return name


def _save_files(files: list) -> str:
    """
    Save files to a temp folder.

    Args:
        files (list): List of files to be saved

    Returns:
        str: Path to the temp folder
    """
    tmp_dir = os.getenv('TMP_DIR')
    if tmp_dir is None:
        LOGGER.error("TMP_DIR environment variable not set")
        return None

    try:
        tmp_folder = os.path.join(tmp_dir, str(datetime.now().timestamp()))
        os.mkdir(tmp_folder)
        for file in files:
            file.save(os.path.join(tmp_folder, file.filename))
        return tmp_folder
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error("Unexpected error saving files: %s", err)
        return None


def _queue_conversion(temp_folder: str, client_id: str, user_email: str, conversion_params: dict):
    """
    Queue a task to convert the files in a temp folder to PDF.

    Args:
        temp_folder (str): Path to the temp folder
        client_id (str): Client ID
        user_email (str): Email address of user
        conversion_params (dict): Parameters for the conversion
    """
    pass