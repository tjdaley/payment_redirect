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
    salutation = StringField(
        "Salutation",
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
    address1 = StringField(
        "Street",
        [validators.DataRequired(), validators.Length(min=3, max=50)]
    )
    city = StringField(
        "City",
        [validators.DataRequired(), validators.Length(min=3, max=50)]
    )
    state = StringField(
        "State",
        [validators.DataRequired(), validators.Length(min=2, max=2)]
    )
    postal_code = StringField(
        "ZIP code",
        [validators.DataRequired(), validators.Length(min=5, max=10)]
    )
    client_email = StringField(
        "Client email",
        [validators.DataRequired(), validators.Email()]
    )
    check_digit = StringField(
        "Check digit"
    )
    attorney_initials = StringField(
        "Attorney initials",
        [validators.DataRequired(), validators.Length(min=2, max=4)]
    )
    admin_users = StringField(
        "Admin emails",
        [validators.DataRequired()]
    )
    payment_due = StringField(
        "Payment due"
    )
    notes = StringField(
        "Note to client",
        [validators.Length(max=256)]
    )
