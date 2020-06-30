"""
TemplateForm.py - Form to create/edit an AWS SES Template

Copyright (c) 2020 by Thomas J. Daley, J.D. ALl Rights Reserved.
"""
from wtforms import Form, StringField, TextAreaField, validators


class TemplateForm(Form):
    TemplateName = StringField(
        "Name",
        [validators.DataRequired()]
    )
    SubjectPart = StringField(
        "Subject",
        [validators.DataRequired()]
    )
    TextPart = TextAreaField(
        "Text",
        [validators.DataRequired()]
    )
    HtmlPart = TextAreaField(
        "HTML"
    )
