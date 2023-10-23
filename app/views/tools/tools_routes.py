"""
tools_routes.py - Direct a client to the payment page

Copyright (c) 2021 by Thomas J. Daley. All Rights Reserved.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import os
import re
from uuid import uuid4
from flask import Blueprint, render_template, request, session, jsonify
import boto3
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
from falconlib.falconlib import FalconLib
# from util.logger import get_logger


DBADMINS = DbAdmins()
DBCLIENTS = DbClients()
MSFT = MicrosoftGraph()
PLAN_TEMPLATES = PlanTemplates()
USERS = None
LOGGER = get_logger('crm_routes')

tools_routes = Blueprint('tools_routes', __name__, template_folder='templates')

class FalconManager():
    """
    Manage the interface between our app and Falcon.
    """
    Tracker_Name = '$CLIENT_TOOLS$'
    def __init__(self):
        """
        Instantiate a connection to the Falcon API.
        """
        base_url = os.getenv('FALCON_URL', 'https://api.jdbot.us')
        api_version = os.getenv('FALCON_API_VERSION', '1_0')
        self.falcon = FalconLib(base_url, api_version)
        username = os.getenv('FALCON_USERNAME')
        password = os.getenv('FALCON_PASSWORD')
        result = self.falcon.authorize(username, password)
        if not result.success:
            LOGGER.error("Falcon login failed: %s", result.error)
        self.bucket = os.environ.get('DISCOVERY_CLASSIFIER_BUCKET', 'discoveryclassifier')
        self.folder = os.environ.get('ASYNC_PROCESSING_FOLDER', 'queued_documents')
        self.boto3_credentials = {
            'region_name': os.environ.get('AWS_REGION_TXT', 'us-east-1'),
            'aws_access_key_id': os.environ.get('AWS_ACCESS_KEY_ID_TXT', ''),
            'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY_TXT', '')
        }

    def extract_text(self, filename: str, file_path: str, user_email: str, client_id: str) -> str:
        """
        Chain together methods in this class to start the text extraction process.

        Args:
            filename (str): Name of file to be analyzed (as user knows it)
            file_path (str): Path to file to be analyzed (our tmp name)
            user_email (str): Email address of user
            client_id (str): Client ID

        Returns:
            str: ID of the document
        """
        doc_id = self.add_doc(client_id, user_email, file_path, filename)
        LOGGER.debug("Added document %s", doc_id)
        key_path = self.move_to_cloud(file_path)
        LOGGER.debug("Moved %s to %s", file_path, key_path)
        job_id = self.queue_text_extraction(key_path, file_path)
        LOGGER.debug("Queued %s for text extraction", key_path)
        self.update_job_id(doc_id, job_id)
        LOGGER.debug("Updated job ID for %s to %s", doc_id, job_id)
        return doc_id

    def create_tracker(self, client_id: str, user_email: str) -> str:
        """
        Create a tracker for a client.

        Args:
            client_id (str): Client ID
            user_email (str): Email address of user

        Returns:
            str: ID of the created tracker
        """
        # Create a tracker for this client.
        tracker_doc = {
            'client_reference': client_id,
            'id': user_email,
            'name': FalconManager.Tracker_Name,
        }
        r = self.falcon.create_tracker(tracker_doc)
        if not r.success:
            LOGGER.error("Error creating tracker: %s", r.message)
            return user_email

        tracker_id = r.payload.get('id')
        if not tracker_id:
            LOGGER.error("No tracker ID returned.")
            return None

        # Allow our user to access the tracker
        r = self.falcon.get_tracker(tracker_id)
        tracker_doc = r.payload
        if not tracker_doc:
            LOGGER.error("No tracker document returned.")
            return None
        tracker_doc['auth_usernames'].append(user_email)
        r = self.falcon.update_tracker(tracker_doc)
        return tracker_id

    def add_doc(self, client_id: str, user_email: str, file_path: str, filename: str)-> str:
        """
        Add a document to Falcon.

        Args:
            client_id (str): Client ID
            user_email (str): Email address of user
            file_path (str): Path to file to be added (our tmp name)
            filename (str): Name of file to be added (as user knows it)

        Returns:
            str: ID of the added document
        """
        tracker_id = self.create_tracker(client_id, user_email)

        # Add the document to Falcon Tracker
        doc_id = uuid4().hex
        doc = {
            'id': doc_id,
            'path': file_path,
            'filename': os.path.basename(file_path),
            'title': filename,
            'type': 'application/pdf',
            'create_date': datetime.now().isoformat().replace('T', ' '),  # Falcon doesn't like T in the date
            'client_reference': client_id,
        }
        r = self.falcon.add_document(doc)
        if not r.success:
            LOGGER.error("Error adding document: %s", r.message)
            return None
        LOGGER.debug("Added document %s", r.payload)
        r = self.falcon.link_document(tracker_id, doc_id)
        LOGGER.debug("Linked document %s to tracker %s", doc_id, tracker_id)

        props = {
            'id': doc_id,
            'extraction_type': 'ANALYSIS'
        }
        _ = self.falcon.add_extended_document_properties(props)
        return doc_id

    def update_job_id(self, doc_id: str, job_id: str) -> bool:
        """
        Update the job ID for a document.

        Args:
            doc_id (str): ID of document
            job_id (str): ID of job

        Returns:
            bool: True if successful, otherwise False
        """
        r = self.falcon.get_extended_document_properties(doc_id)
        props = r.payload
        props['job_id'] = job_id
        r = self.falcon.update_extended_document_properties(props)
        return r.success

    def move_to_cloud(self, file_path: str) -> str:
        """
        Copy a file to the cloud for processing.

        Args:
            file_path (str): path of document to store

        Returns:
            str: key_path if successful, otherwise None
        """
        key = os.path.basename(file_path)
        key_path = f'{self.folder}/{key}'
        LOGGER.debug("key_path: %s", key_path)

        try:
            # Copy the file to the async processing bucket on S3
            s3 = boto3.resource('s3', **self.boto3_credentials)  # pylint: disable=invalid-name
            assert s3.meta is not None, "S3 resource is not available"
            ttl = int(os.environ.get('QUEUED_DOC_TTL_SECONDS', '86400'))
            try:
                now = datetime.utcnow()
                expires = now + timedelta(seconds=ttl)
                s3.meta.client.upload_file(file_path, self.bucket, key_path, ExtraArgs={'Expires': expires})
            except Exception as e:  # pylint: disable=broad-except,invalid-name
                LOGGER.error("%s", str(e))
                return None
        except Exception as e:  # pylint: disable=broad-except,invalid-name
            LOGGER.error("Error staging %s to S3: %s", file_path, str(e))
            return None
        return key_path

    def queue_text_extraction(self, key_path: str, file_path: str) -> str:
        """
        Queue a text extraction job.

        Args:
            key_path (str): S3 key path to the file
            file_path (str): Path to the file

        Returns:
            str: ID of the job
        """
        job_id = None
        s3object = {'Bucket': self.bucket, 'Name': key_path}
        notification_channel = {
            'RoleArn': os.environ.get('TEXTRACT_ROLE_ARN', ''),
            'SNSTopicArn': os.environ.get('SNS_TOPIC_ARN', '')
        }
        client_request_token = re.sub('[^a-zA-Z0-9-_]', '', key_path)[:64]
        job_tag = re.sub('[^a-zA-Z0-9_.-]', '', key_path)[:32]

        textract_client = boto3.client('textract', **self.boto3_credentials)  # pylint: disable=invalid-name
        try:
            response = textract_client.start_document_analysis(
                DocumentLocation={'S3Object': s3object},
                ClientRequestToken=client_request_token,
                JobTag=job_tag,
                NotificationChannel=notification_channel,
                FeatureTypes=['TABLES'],
            )

            job_id = response.get('JobId', None)
            return job_id
        except textract_client.exceptions.InvalidParameterException as e:  # pylint: disable=invalid-name
            LOGGER.error("Error queuing %s for async processing: %s", file_path, str(e))
            LOGGER.error("S3Object: %s", s3object)
            LOGGER.error("ClientRequestToken: %s", client_request_token)
            LOGGER.error("JobTag: %s", job_tag)
            LOGGER.error("NotificationChannel: %s", notification_channel)
            return None
        except textract_client.exceptions.IdempotentParameterMismatchException as e:  # pylint: disable=invalid-name
            LOGGER.error("Error queuing %s for async processing: %s", file_path, str(e))
            LOGGER.error("A ClientRequestToken input parameter was reused with an operation, but at least one of the other input parameters is different from the previous call to the operation.")
            LOGGER.error("ClientRequestToken: %s", client_request_token)
            LOGGER.error("JobTag: %s", job_tag)
            return None
        except Exception as e:  # pylint: disable=broad-except,invalid-name
            LOGGER.error("Error queuing %s for async processing: %s", file_path, str(e))
            return None

    def text_extraction_status(self, doc_id: str) -> str:
        """
        Get the status of a text extraction job.

        Args:
            doc_id (str): ID of document to be queued

        Returns:
            str: Status of the job ('SUCCEEDED' = done)
        """
        r = self.falcon.get_extended_document_properties(doc_id)
        props = r.payload
        job_id = props.get('job_id')
        if not job_id:
            return 'NOT_QUEUED'
        status = props.get('job_status')
        if not status:
            return 'QUEUED*'
        return status

    def get_documents(self, client_id: str, user_email: str) -> list:
        """
        Retrieve a list of documents relating to this user.

        Args:
            client_id (str): Client ID
            user_email (str): Email address of user

        Returns:
            list: List of documents
        """
        result = self.falcon.get_trackers(user_email)
        trackers = result.payload.get('trackers', [])
        if not trackers:
            return []

        tracker_id = None
        for tracker in trackers:
            if tracker['name'] == FalconManager.Tracker_Name:
                tracker_id = tracker['id']
                break

        if not tracker_id:
            return []

        result = self.falcon.get_documents(tracker_id)
        documents = result.payload.get('documents', []) or []
        if not documents:
            return []
        client_documents = []
        for doc in documents:
            if doc['client_reference'] == client_id:
                client_documents.append(doc)

        if not client_documents:
            return []

        for doc in client_documents:
            result = self.falcon.get_extended_document_properties(doc['id'])
            xprops = result.payload
            status = 'FAILED'
            has_tables = False
            if xprops:
                status = xprops.get('job_status', 'NOT_QUEUED') or 'NOT_QUEUED'
                dict_tables = xprops.get('dict_tables', {}) or {}
                tables = dict_tables.get('tables', []) or []
                has_tables = len(tables) > 0
            doc['status'] = status
            doc['has_tables'] = has_tables

        return client_documents


FALCONLIB = FalconManager()

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
        doc_id = FALCONLIB.extract_text(file.filename, tmp_file, user_email, client_id)
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error("Unexpected error saving file: %s", err)
        LOGGER.debug("File: %s", tmp_file)
        return jsonify({'success': False, 'error': str(err)})
    LOGGER.debug("Saved file: %s", file.filename)
    return jsonify({'success': True, 'doc_id': doc_id, 'message': 'Text extraction in progress'})


@tools_routes.route('/client_tools/<string:client_id>/documents', methods=['GET'])
@DECORATORS.is_logged_in
@DECORATORS.auth_crm_user
def get_documents(client_id: str):
    """
    Get a list of documents for a client.

    Args:
        client_id (str): Client ID

    Returns:
        JSON response
    """
    user_email = session['user']['preferred_username']
    client = DBCLIENTS.get_one(client_id)
    authorizations = _get_authorizations(user_email)
    documents = FALCONLIB.get_documents(client_id, user_email)
    return render_template(
        'tools/documents.html',
        client=client,
        authorizations=authorizations,
        documents=documents
    )


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
