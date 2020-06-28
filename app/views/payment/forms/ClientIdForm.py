"""
ClientIdForm.py - Client Identifies Itself

Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
from wtforms import Form, StringField, SelectField, validators


class ClientIdForm(Form):
    client_ssn = StringField(
        "Social Security number (last three digits)",
        [validators.DataRequired(), validators.Length(min=3, max=3, message="Just enter the LAST 3 digits of your Social Security number.")]
    )
    client_dl = StringField(
        "Driver's License number (last three digits)",
        [validators.DataRequired(), validators.Length(min=3, max=3, message="Only enter the LAST 3 digits of your driver's license number.")]
    )
