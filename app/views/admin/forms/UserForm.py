"""
UserForm.py - CRUD form for a client.

Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
from wtforms import Form, StringField, SelectMultipleField, validators, BooleanField, FileField
from wtforms.fields import EmailField

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
    ring_central_username = StringField(
        "Ring Central username"
    )
    ring_central_extension = StringField(
        "Ring Central extension"
    )
    ring_central_password = StringField(
        "Ring Central password"
    )
    prompt_on_dial_flag = BooleanField(
        "Prompt before dialing?",
        false_values=('N', '', None)
    )
    letterhead_template = FileField(
        "Client letterhead template"
    )
    contact_letterhead_template = FileField(
        "Contact letterhead template"
    )
    fee_agreement = FileField(
        "Fee agreement template"
    )
    default_cc_list = StringField(
        "Default CC list"
    )
    default_access_list = StringField(
        "Default access list"
    )
    click_up_workspace_name = StringField(
        'Click Up Workspace name',
        default="Clients"
    )
    click_up_team_name = StringField(
        'Click Up Team name',
        default="Client Workspace"
    )
