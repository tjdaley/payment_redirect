
"""
decorators.py - Decorators for applied to routes/views
"""
import os
from flask import flash, redirect, session, url_for
from functools import wraps

from util.db_admins import DbAdmins
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
        database = DbAdmins()
        admin_record = database.admin_record(user_email)
        if admin_record and admin_record['attorneys']:
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


# Decorator to see if user may download contact lists
def auth_download_contacts(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user_email = session['user']['preferred_username']
        authorizations = _get_authorizations(user_email)
        if AUTH.AUTH_DOWNLOAD_CONTACTS in authorizations:
            return f(*args, **kwargs)
        else:
            flash("Your account has not been authorized to download contact lists", "danger")
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


# Decorator to see if user may download contact vcards
def auth_download_vcards(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user_email = session['user']['preferred_username']
        authorizations = _get_authorizations(user_email)
        if AUTH.AUTH_DOWNLOAD_VCARD in authorizations:
            return f(*args, **kwargs)
        else:
            flash("Your account has not been authorized to download v-cards", "danger")
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


# Decorator to see if user may manage users
def auth_manage_users(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user_email = session['user']['preferred_username']
        authorizations = _get_authorizations(user_email)
        if AUTH.AUTH_USER_ADMIN in authorizations:
            return f(*args, **kwargs)
        else:
            flash("Your account has not been authorized to administer users", "danger")
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


# Decorator to see if user is authorized to use crm functions
def auth_crm_user(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user_email = session['user']['preferred_username']
        authorizations = _get_authorizations(user_email)
        if AUTH.AUTH_CRM_USER in authorizations:
            return f(*args, **kwargs)
        else:
            flash("Your account has not been authorized to access CRM features", "danger")
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


# Decorator to see if user is authorized to edit global settings
def auth_edit_global_settings(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user_email = session['user']['preferred_username']
        authorizations = _get_authorizations(user_email)
        if AUTH.AUTH_EDIT_GLOBAL_SETTINGS in authorizations:
            return f(*args, **kwargs)
        else:
            flash("Your account has not been authorized to edit global settings", "danger")
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


# Decorator to see if user is a test user (crash test dummy)
def auth_pioneer(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user_email = session['user']['preferred_username']
        authorizations = _get_authorizations(user_email)
        if AUTH.AUTH_PIONEER in authorizations:
            return f(*args, **kwargs)
        else:
            flash("Your account has not been authorized as a test user", "danger")
            return redirect(url_for(LOGIN_FUNCTION))
    return wrap


def _get_authorizations(user_email: str) -> list:
    database = DbAdmins()
    return database.authorizations(user_email)
