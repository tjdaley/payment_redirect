"""
app.py - Flask-based server.

@author Thomas J. Daley, J.D.
@version: 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
import os
import random
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
from flask_session import Session
import msal
from wtforms import Form, StringField, TextAreaField, PasswordField, validators

from functools import wraps

import settings  # Loads .env into os.environ
import config

from views.decorators import is_admin_user, is_logged_in
from util.database import Database
from views.admin.admin_routes import admin_routes, _build_auth_url
from views.crm.crm_routes import crm_routes
from views.payment.payment_routes import payment_routes


DATABASE = Database()
DATABASE.connect()

DEBUG = int(os.environ.get('DEBUG', '0'))

app = Flask(__name__)
app.config.from_mapping(
    CLIENT_SECRET=os.environ['AZURE_CLIENT_SECRET'],
    SESSION_TYPE='filesystem'
)
Session(app)

app.register_blueprint(admin_routes)
app.register_blueprint(crm_routes)
app.register_blueprint(payment_routes)


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
    app.run(debug=DEBUG, port=port)
