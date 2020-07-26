"""
app.py - Flask-based server.

@author Thomas J. Daley, J.D.
@version: 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
import os
from flask import Flask, render_template, redirect, url_for
from flask_session import Session
from waitress import serve

import settings  # NOQA
import config # NOQA

from util.database import Database, do_upgrades
from views.admin.admin_routes import admin_routes
from views.crm.crm_routes import crm_routes
from views.payment.payment_routes import payment_routes


DATABASE = Database()
do_upgrades()

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
    if DEBUG == 1:
        app.run(debug=DEBUG, port=port)
    else:
        serve(app, host='0.0.0.0', port=port)
