"""
ClientForm.py - CRUD form for a client.

Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
from wtforms import Form, StringField, SelectField, validators


class ClientForm(Form):
    billing_id = StringField(
        "Billing ID",
        [validators.DataRequired(), validators.Length(min=4, max=5, message="Enter the client's billing ID without the matter suffix.")]
    )
    client_name = StringField(
        "Client name",
        [validators.DataRequired(), validators.Length(min=3, max=50)]
    )
    client_ssn = StringField(
        "Client SSN",
        [validators.DataRequired(), validators.Length(min=3, max=3)]
    )
    client_dl = StringField(
        "Client Driver's License",
        [validators.DataRequired(), validators.Length(min=3, max=3)]
    )
    attorney_initials = StringField(
        "Attorney initials",
        [validators.DataRequired(), validators.Length(min=2, max=4)]
    )
    payment_due = StringField(
        "Payment due",
        [validators.NumberRange(min=.01, max=500000.00, message="Payment due must be between $0.01 and $500,000.00")]
    )
    notes = StringField(
        "Note to client",
        [validators.Length(max=256)]
    )
