"""
ClientIdForm.py - Client Identifies Itself

Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
from wtforms import Form, StringField, SelectField, validators


class ClientIdForm(Form):
    client_ssn = StringField(
        "Last three digits of your Social Security number",
        [validators.DataRequired(), validators.Length(min=3, max=3, message="Just enter the LAST 3 digits of your Social Security number.")]
    )
    client_dl = StringField(
        "Last three digits of your Driver's License number",
        [validators.DataRequired(), validators.Length(min=3, max=3, message="Only enter the LAST 3 digits of your driver's license number.")]
    )
