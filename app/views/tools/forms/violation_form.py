"""
violation_form.py - Prompt for fields to determine child support violations

Copyright (c) 2022 by Thomas J. Daley, J.D.
"""
from wtforms import Form, DecimalField, IntegerField, SelectField, TextAreaField, validators, BooleanField
from wtforms.fields.html5 import DateField
# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.date_converter import DateConverter
# pylint: enable=no-name-in-module
# pylint: enable=import-error

PAYMENT_INTERVALS = [
    (12, "Monthly"),
    (24, "Semimonthly"),
    (26, "Bi-Weekly"),
    (52, "Weekly")
]

class ViolationForm(Form):
    cs_payment_amount = DecimalField(
        label="Child support payment amount",
        # validators=[validators.DataRequired()],
        places=2
    )
    medical_payment_amount = DecimalField(
        label="Medical insurance reimbursement amount",
        # validators=[validators.DataRequired()],
        places=2
    )
    dental_payment_amount = DecimalField(
        label="Dental insurance reimbursement amount",
        # validators=[validators.DataRequired()],
        places=2
    )
    start_date = DateField(
        "First payment due date",
        validators=[validators.Optional(), DateConverter()]
    )
    payment_interval = SelectField(
        "Payment interval",
        choices=PAYMENT_INTERVALS
    )
    children_not_before_court = IntegerField(
        label="Children NOT before the court",
        default='0'
    )
    violations_only = BooleanField(
        "Show violations only?"
    )
    payments = TextAreaField(
        "Payments"
    )
