"""
date_converter.py - Custom Validator for Dates

Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from wtforms import ValidationError
from datetime import date


class DateConverter(object):
    """
    This class is a custom validator for WTForms. Use it to convert datetime.date
    data to string before saving to Mongo DB.
    """
    def __call__(self, form, field):
        """
        Args:
            form (Form): Referencee to form that is hosting the field
            field (DateField): Reference to field that is being fixed
        Returns:
            None

        Returns:
            ValidationError if the input value doesn't clean up properly.

        Side-Effects:
            datetime.date is converted to YYYY-MM-DD string.
        """
        if not isinstance(field.data, (date)):
            return

        try:
            field.data = field.data.strftime('%Y-%m-%d')
        except ValueError as e:
            raise ValidationError(str(e))
