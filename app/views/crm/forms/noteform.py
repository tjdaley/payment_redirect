"""
NoteForm.py - CRUD form for a note.

Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
from wtforms import Form, StringField, validators, TextAreaField, HiddenField


class NoteForm(Form):
    text = TextAreaField(
        "Note",
        [validators.DataRequired]
    )
    tags = StringField(
        "Tags"
    )
    clients_id = HiddenField(
        "Client ID"
    )
    create_date = HiddenField(
        "Date"
    )
    created_by = HiddenField(
        "Created by"
    )
    _id = HiddenField(
        "Note ID"
    )
