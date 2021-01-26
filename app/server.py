"""
app.py - Flask-based server.

@author Thomas J. Daley, J.D.
@version: 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
import os
from flask import Flask, render_template, redirect, url_for
from flask_session import Session
from pymongo import MongoClient
from waitress import serve

import settings  # NOQA
import msftconfig # NOQA

from util.database import Database, do_upgrades
from views.admin.admin_routes import admin_routes
from views.crm.crm_routes import crm_routes
from views.payment.payment_routes import payment_routes
from views.admin.forms.ClientForm import CRM_STATES
from views.admin.forms.ClientForm import CASE_TYPES


DATABASE = Database()
do_upgrades()

DEBUG = int(os.environ.get('DEBUG', '0'))


def phone_filter(value):
    return f"{value[2:5]}-{value[5:8]}-{value[8:]}"


def crm_state_filter(value):
    for crm_state in CRM_STATES:
        if crm_state[0] == value:
            return crm_state[1]
    return value


def case_type_filter(value):
    return dict(CASE_TYPES).get(value, None)


def newlines_filter(value: str) -> str:
    """
    Convert newlines to <br /> for displaying on browser.
    """
    if isinstance(value, str):
        return value.replace('\n', '<br />')
    return value


app = Flask(__name__)
app.config.from_mapping(
    CLIENT_SECRET=os.environ['AZURE_CLIENT_SECRET'],
    SESSION_TYPE='mongodb',
    SESSION_MONGODB=MongoClient(os.environ['DB_URL']),
    SECRET_KEY=os.environ.get('FLASK_FORM_SECRET_KEY', 'aas;ldfkjiruetnviupi842nvutj4iv')
)
Session(app)

app.register_blueprint(admin_routes)
app.register_blueprint(crm_routes)
app.register_blueprint(payment_routes)
app.jinja_env.filters['phone_number'] = phone_filter
app.jinja_env.filters['crm_state'] = crm_state_filter
app.jinja_env.filters['newlines'] = newlines_filter
app.jinja_env.filters['case_type'] = case_type_filter


@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('payment_routes.identify_client'))


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
        app.run(debug=DEBUG, port=port)
    else:
        serve(app, host='0.0.0.0', port=port)
