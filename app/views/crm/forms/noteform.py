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
    _id = HiddenField(
        "Note ID"
    )
