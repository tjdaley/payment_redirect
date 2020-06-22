"""
app.py - Flask-based server.

@author Thomas J. Daley, J.D.
@version: 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
import os
import random
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
from wtforms import Form, StringField, TextAreaField, PasswordField, validators

from functools import wraps

import settings  # Loads .env into os.environ

from views.decorators import is_admin_user, is_logged_in
from util.database import Database
from views.admin.admin_routes import admin_routes
from views.payment.payment_routes import payment_routes

DATABASE = Database()
DATABASE.connect()

DEBUG = int(os.environ.get('DEBUG', '0'))

app = Flask(__name__)

app.register_blueprint(admin_routes)
app.register_blueprint(payment_routes)


@app.route('/', methods=['GET'])
def index():
    url = os.environ.get('BASE_URL')
    return redirect(url, code=302)


if __name__ == "__main__":
    app.secret_key = os.environ['APP_SECRET_KEY']
    port = int(os.environ.get('LISTEN_PORT', '8088'))
    app.run(debug=DEBUG, port=port)
