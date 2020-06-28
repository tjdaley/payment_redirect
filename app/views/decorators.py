
"""
decorators.py - Decorators for applied to routes/views
"""
import os
from flask import flash, redirect, session, url_for
from functools import wraps

from util.database import Database

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
