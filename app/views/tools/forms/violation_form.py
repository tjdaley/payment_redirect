"""
violation_form.py - Prompt for fields to determine child support violations

Copyright (c) 2022 by Thomas J. Daley, J.D.
"""
from wtforms import Form, DecimalField, IntegerField, TextAreaField, validators
from wtforms.fields.html5 import DateField
# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.date_converter import DateConverter
# pylint: enable=no-name-in-module
# pylint: enable=import-error


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
    payments = TextAreaField("Payments")
