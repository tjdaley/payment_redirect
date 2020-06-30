"""
dollarcleaner.py - Custom Validator for Dollar Values for WTForms

Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from wtforms import ValidationError


class DollarCleaner(object):
    """
    This class is a custom validator for WTForms. Use it to make sure an input
    string is a valid dollar amount within and optional given range.
    """
    def __init__(self, min: float = None, max: float = None, message: str = None):
        """
        Args:
            min (float): The minimum value. Default is no minimum value.
            max (float): The maximum value. Default is no maximum value.
            message (str): Error message to display on validation errors. You're better
                           off not including a value here for most purposes because the
                           validator will create a more precise error message.
        Returns:
            None

        Returns:
            ValidationError if the input value doesn't clean up properly.

        Side-Effects:
            "$" and "," are removed from the input string so that the value
            returned to the web server looks like a valid Decimal number.
        """
        self.min = min
        self.max = max
        self.message = message

    def __call__(self, form, field):
        field.data = field.data.replace('$', '').replace(',', '')
        try:
            x = float(field.data)
        except ValueError:
            raise ValidationError("Please enter a dollar value.")

        if self.min is not None and x < self.min:
            if self.message:
                raise ValidationError(self.message)
            if self.min == 0:
                raise ValidationError(f"Value cannot be a negative number.")
            raise ValidationError(f"Value must be at least ${self.min:,.2f}.")

        if self.max is not None and x > self.max:
            if self.message:
                raise ValidationError(self.message)
            raise ValidationError(f"Value must be no more than ${self.max:,.2f}.")
