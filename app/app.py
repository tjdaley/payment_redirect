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
app.register_blueprint(payment_routes)


@app.route('/', methods=['GET'])
def index():
    url = os.environ.get('BASE_URL')
    return redirect(url, code=302)


if __name__ == "__main__":
    app.jinja_env.globals.update(_build_auth_url=_build_auth_url)
    port = int(os.environ.get('LISTEN_PORT', '8088'))
    app.run(debug=DEBUG, port=port)
