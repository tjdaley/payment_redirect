"""
server.py - Entry point to CRM server

@author Thomas J. Daley, J.D.
@version: 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from datetime import datetime
import os
from flask import Flask, render_template, redirect, url_for
from flask_session import Session
import locale
import platform
from pymongo import MongoClient
import re
from waitress import serve

import settings  # NOQA
import msftconfig # NOQA

from util.database import Database, do_upgrades
from views.admin.admin_routes import admin_routes
from views.discovery.discovery_routes import discovery_routes
from views.crm.crm_routes import crm_routes
from views.payment.payment_routes import payment_routes
from views.tools.tools_routes import tools_routes
from views.admin.forms.ClientForm import CRM_STATES
from views.admin.forms.ClientForm import CASE_TYPES


DATABASE = Database()
do_upgrades()

DEBUG = int(os.environ.get('DEBUG', '0'))


app = Flask(__name__)
app.config.from_mapping(
    CLIENT_SECRET=os.environ['AZURE_CLIENT_SECRET'],
    SESSION_TYPE='mongodb',
    SESSION_MONGODB=MongoClient(os.environ['DB_URL']),
    SECRET_KEY=os.environ.get('FLASK_FORM_SECRET_KEY', 'aas;ldfkjiruetnviupi842nvutj4iv'),
    EXPLAIN_TEMPLATE_LOADING=False
)
Session(app)

# Blueprints for routes
app.register_blueprint(admin_routes)
app.register_blueprint(crm_routes)
app.register_blueprint(discovery_routes)
app.register_blueprint(payment_routes)
app.register_blueprint(tools_routes)


# jinja filters
def phone_filter(value):
    return f"{value[2:5]}-{value[5:8]}-{value[8:]}"


def crm_state_filter(value):
    for crm_state in CRM_STATES:
        if crm_state[0] == value:
            return crm_state[1]
    return value


def case_type_filter(value):
    return dict(CASE_TYPES).get(value, None)


def date_filter(value):
    if isinstance(value, datetime):
        return datetime.strftime(value, '%m/%d/%Y')
    date_parts = value.split('-')
    return f"{date_parts[1]}/{date_parts[2]}/{date_parts[0]}"


def fullname_filter(value):
    return " ".join([
        value.get('last_name', '').upper()+",",
        value.get('first_name', ''),
        value.get('middle_name', ''),
        value.get('suffix', '')]
    )


def newlines_filter(value: str) -> str:
    """
    Convert newlines to <br /> for displaying on browser.
    """
    if isinstance(value, str):
        return value.replace('\n', '<br />')
    return value


def currency_filter(value: str) -> str:
    """
    Create a number that looks like currency
    """
    try:
        c_value = float(value)
    except Exception:
        if isinstance(value, str):
            c_value = re.sub('[^0-9\.]', '', value)
        if value is None or c_value == '':
            c_value = '0'
        c_value = float(value)
    return locale.currency(c_value, grouping=True)


# {{"" | pyimplementation}} {"" | {pyversion}}
def platform_system_filter(value: str) -> str:
    return platform.system()


def platform_release_filter(value: str) -> str:
    return platform.release()


def platform_hostname_filter(value: str) -> str:
    return os.getenv('HOSTNAME', os.getenv('COMPUTERNAME', platform.node())).split('.')[0]


def platform_pyimplementation_filter(value: str) -> str:
    return platform.python_implementation()


def platform_pyversion_filter(value: str) -> str:
    return platform.python_version()


def email_name_filter(value: str) -> str:
    return value.split('@')[0]

app.jinja_env.filters['case_type'] = case_type_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['crm_state'] = crm_state_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['currency'] = currency_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['date'] = date_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['email_name'] = email_name_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['fullname'] = fullname_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['hostname'] = platform_hostname_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['newlines'] = newlines_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['os'] = platform_system_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['os_version'] = platform_release_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['phone_number'] = phone_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['pyimplementation'] = platform_pyimplementation_filter  # noqa pylint: disable=no-member
app.jinja_env.filters['pyversion'] = platform_pyversion_filter  # noqa pylint: disable=no-member


@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('crm_routes.list_clients'))


@app.route('/privacy')
def privacy():
    return render_template("privacy.html")


@app.route('/terms_and_conditions')
def terms_and_conditions():
    return render_template("terms_and_conditions.html")


if __name__ == "__main__":
    # The following line is from MSFT's example. It causes a lint error
    # and commenting it out does not seem to cause any problems.
    # tjd 06/28/2020
    # app.jinja_env.globals.update(_build_auth_url=_build_auth_url)
    port = int(os.environ.get('LISTEN_PORT', '8088'))
    if DEBUG == 1:
        app.run(debug=True, port=port)
    else:
        serve(app, host='0.0.0.0', port=port)
