"""
GlobalSettingsForm.py - Form to create/edit Global settings

Copyright (c) 2020 by Thomas J. Daley, J.D. ALl Rights Reserved.
"""
from wtforms import Form, FileField


class GlobalSettingsForm(Form):

    letterhead_template = FileField(
        "Client letterhead template"
    )
    contact_letterhead_template = FileField(
        "Contact letterhead template"
    )
    fee_agreement = FileField(
        "Fee agreement template"
    )
