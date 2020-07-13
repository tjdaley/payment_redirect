"""
UserForm.py - CRUD form for a client.

Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
from wtforms import Form, StringField, SelectMultipleField, validators, BooleanField, ValidationError
from wtforms.fields.html5 import EmailField

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.authorizations import AUTHORIZATION_OPTIONS
# pylint: enable=no-name-in-module
# pylint: enable=import-error


class UserForm(Form):
    first_name = StringField(
        "First name",
        [validators.DataRequired(), validators.Length(min=3, max=50)]
    )
    last_name = StringField(
        "Last name",
        [validators.DataRequired(), validators.Length(min=3, max=50)]
    )
    email = EmailField(
        "Email",
        [validators.DataRequired()]
    )
    attorneys = SelectMultipleField(
        "Attorneys",
        choices=[
            ('BSL', "Brian"),
            ('RLR', "Rick"),
            ('TJD', "Tom")
        ]
    )
    groups = SelectMultipleField(
        "Groups",
        choices=[
            ('collin', "Collin"),
            ('dallas', "Dallas"),
            ('denton', "Denton"),
            ('southlake', "South Lake")
        ]
    )
    authorizations = SelectMultipleField(
        "Authorizations",
        choices=AUTHORIZATION_OPTIONS
    )
    active_flag = BooleanField(
        "Active?",
        false_values=('N', '')
    )
