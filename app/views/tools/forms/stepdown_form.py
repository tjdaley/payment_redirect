"""
stepdown_form.py - Prompt for fields to calclate a step-down schedule

Copyright (c) 2021 by Thomas J. Daley, J.D.
"""
from wtforms import Form, DecimalField, IntegerField, validators


class StepdownForm(Form):
    payment_amount = DecimalField(
        label="Starting payment amount",
        validators=[validators.DataRequired()],
        places=2
    )
    children_not_before_court = IntegerField(
        label="Children NOT before the court",
        default='0'
    )
