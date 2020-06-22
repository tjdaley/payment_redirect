"""
admin_routes.py - Handle the administrative routes.

Copyright (c) 2020 by Thomas J. Daley. All Rights Reserved.
"""
from flask import Blueprint, render_template, request

from views.decorators import is_logged_in, is_admin_user
from .forms.ClientForm import ClientForm

from util.database import Database
DATABASE = Database()
DATABASE.connect()

admin_routes = Blueprint("admin_routes", __name__, template_folder="templates")


@admin_routes.route("/clients", methods=['GET'])
# @is_logged_in
# @is_admin_user
def list_query_cache():
    clients = DATABASE.get_clients()
    return render_template("clients.html", clients=clients)


@admin_routes.route("/client/<string:id>/", methods=['GET'])
# @is_logged_in
# @is_admin_user
def show_query(id):
    client = DATABASE.get_client(id)
    form = ClientForm(request.form)
    return render_template("client.html", client=client, form=form)
