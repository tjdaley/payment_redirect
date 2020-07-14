"""
ClientForm.py - CRUD form for a client.

Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
from wtforms import Form, StringField, validators, BooleanField, DecimalField, SelectField, ValidationError
from wtforms.fields.html5 import DateField, EmailField, TelField

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.dollarcleaner import DollarCleaner
from util.us_states import US_STATES
from util.court_directory import CourtDirectory
# pylint: enable=no-name-in-module
# pylint: enable=import-error


class ClientForm(Form):
    directory = CourtDirectory()

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
    state = SelectField(
        "State",
        choices=US_STATES
    )
    postal_code = StringField(
        "ZIP code",
        [validators.DataRequired(), validators.Length(min=5, max=10)]
    )
    email = EmailField(
        "Client email",
        [validators.DataRequired()]
    )
    telephone = TelField(
        "Telephone",
        [validators.DataRequired()]
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
        "Payment due",
        [
            DollarCleaner(min=0, max=500000)
        ]
    )
    notes = StringField(
        "Note to client",
        [validators.Length(max=256)]
    )
    active_flag = BooleanField(
        "Active?",
        false_values=('N', '')
    )
    target_retainer = StringField(
        "Target retainer", [DollarCleaner(min=0)]
    )
    refresh_trigger = StringField(
        "Refresh trigger", [DollarCleaner(min=0)]
    )
    trial_retainer = StringField(
        "Trial retainer", [validators.Optional(), DollarCleaner(min=0)]
    )
    trial_date = DateField(
        "Trial date",
        validators=[validators.Optional()]
    )
    mediation_retainer = StringField(
        "Mediation retainer", [validators.Optional(), DollarCleaner(min=0)]
    )
    mediation_date = DateField(
        "Mediation date",
        validators=[validators.Optional()]
    )
    trust_balance = StringField(
        "Trust balance", [validators.Optional(), DollarCleaner()]
    )
    trial_retainer_flag = BooleanField(
        'Trial retainer due?',
        false_values=('N', '')
    )
    mediation_retainer_flag = BooleanField(
        "Mediation retainer due?",
        false_values=('N', '')
    )
    case_county = SelectField(
        "County",
        choices=directory.get_county_tuples()
    )
    court_type = SelectField(
        "Court type",
        validate_choice=False
    )
    court_name = SelectField(
        "Court name",
        validate_choice=False
    )
    cause_number = StringField("Cause number")
