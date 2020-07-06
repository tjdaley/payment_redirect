
"""
decorators.py - Decorators for applied to routes/views
"""
import os
from flask import flash, redirect, session, url_for
from functools import wraps

from util.database import Database
import util.authorizations as AUTH

LOGIN_FUNCTION = os.environ.get('LOGIN_FUNCTION', 'admin_routes.login')


# Decorator to check if user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session.get('user'):
            return f(*args, **kwargs)
        else:
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


# Decorator to check if user is an administrator
def is_admin_user(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user_email = session['user']['preferred_username']
        database = Database()
        database.connect()
        admin_record = database.get_admin_record(user_email)
        if admin_record and admin_record['for']:
            session['is_admin'] = 'Y'
            return f(*args, **kwargs)
        else:
            session['is_admin'] = 'N'
            flash("Unauthorized - Please Log In As An Administrator", "danger")
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


# Decorator to see is user is a template manager
def auth_manage_templates(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user_email = session['user']['preferred_username']
        authorizations = _get_authorizations(user_email)
        if AUTH.AUTH_TEMPLATE_ADMIN in authorizations:
            return f(*args, **kwargs)
        else:
            flash("Your account has not been authorized to administer templates", "danger")
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


# Decorator to see is user is an evergreen sender
def auth_send_evergreens(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user_email = session['user']['preferred_username']
        authorizations = _get_authorizations(user_email)
        if AUTH.AUTH_SEND_EVERGREEN in authorizations:
            return f(*args, **kwargs)
        else:
            flash("Your account has not been authorized to send evergreen letters", "danger")
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


# Decorator to see if user may download client lists
def auth_download_clients(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user_email = session['user']['preferred_username']
        authorizations = _get_authorizations(user_email)
        if AUTH.AUTH_DOWNLOAD_CLIENTS in authorizations:
            return f(*args, **kwargs)
        else:
            flash("Your account has not been authorized to download client lists", "danger")
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


def _get_authorizations(user_email: str) -> list:
    database = Database()
    database.connect()
    admin_record = database.get_admin_record(user_email)
    if admin_record:
        authorizations = admin_record.get('authorizations', [])
        return authorizations
    return []
