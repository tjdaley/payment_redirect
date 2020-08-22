"""
ClientForm.py - CRUD form for a client.

Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
from wtforms import Form, FormField, validators, BooleanField, SelectField, FieldList, StringField
from wtforms.fields.html5 import DateField, EmailField, TelField

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from util.dollarcleaner import DollarCleaner
from util.us_states import US_STATES
from util.court_directory import CourtDirectory
# pylint: enable=no-name-in-module
# pylint: enable=import-error


COURTESY_TITLES = [
    ('Mr.', "Mr."),
    ('Ms.', "Ms."),
    ('Dr.', "Dr."),
    ('Hon.', "Hon.")
]

CRM_STATES = [
    ('000:none', "Select"),
    ('001:contact', "Initial contact"),
    ('010:conflict_pending', "Pending conflict check"),
    ('905:clo_conflicted', "Conflicted out"),
    ('020:conflict_clear', "Conflicts cleared"),
    ('030:consult_pending', "Ready to schedule"),
    ('040:consult_scheduled', "Consult scheduled"),
    ('910:clo_noconsult', "Declined consultation"),
    ('050:consult_done', "Consult done"),
    ('915:clo_consult_only', "Closed, Consult-only"),
    ('920:clo_referred_out', "Closed, Referred-out"),
    ('060:retain_pending', "Pending retainer"),
    ('070:retained_active', "Retained"),
    ('998:trash', "Trash"),
    ('999:clo_closed', "Matter closed")
]


def field_list(class_) -> list:
    x = class_()
    attrs = dir(x)
    members = [
        attr for attr in attrs
        if isinstance(getattr(x, attr), (BooleanField, SelectField, StringField, DateField, EmailField, TelField))
    ]
    return members


def instance_dict(class_, depth: int = 0) -> dict:
    x = class_()
    attribute_names = dir(x)
    result = {}
    for attr_name in attribute_names:
        if attr_name.startswith('_'):
            continue
        attr = getattr(x, attr_name)
        if isinstance(attr, (BooleanField, SelectField, StringField, DateField, EmailField, TelField)):
            result[attr_name] = None
        elif isinstance(attr, (FormField)):
            result[attr_name] = instance_dict(attr.form_class, depth+1)
    return result


class ContactName(Form):
    title = SelectField("Title", choices=COURTESY_TITLES)
    first_name = StringField("First name")
    middle_name = StringField("Middle name")
    last_name = StringField("Last name")
    suffix = StringField("Suffix")
    salutation = StringField("Salutation")

    @classmethod
    def get(cls) -> dict:
        return instance_dict(cls)


class ContactAddress(Form):
    street = StringField("Street")
    city = StringField("City")
    state = SelectField("State", choices=US_STATES)
    postal_code = StringField("ZIP")

    @classmethod
    def get(cls) -> dict:
        return instance_dict(cls)


class ContactForm(Form):
    name = FormField(ContactName)
    address = FormField(ContactAddress)
    office_phone = TelField("Office phone")
    cell_phone = TelField("Cell phone")
    fax = TelField("Fax")
    email = EmailField("Email")
    organization = StringField("Organization name")
    job_title = StringField("Job title")

    @classmethod
    def get(cls) -> dict:
        return instance_dict(cls)


class ContactsForm(Form):
    contacts = FieldList(ContactForm)


class Referral(Form):
    referred_to = StringField("Referred to")
    source = StringField("Source")
    more_info = StringField("More information")

    @classmethod
    def get(cls) -> dict:
        return instance_dict(cls)


class Insurance(Form):
    carrier = StringField("Carrier")
    policy_holder = StringField("Policy holder")
    policy_number = StringField("Policy #")
    group_number = StringField("Group #")
    monthly_premium = StringField("Monthly premium", [validators.Optional(), DollarCleaner(min=0)])
    provided_through = StringField("Provided through")

    @classmethod
    def get(cls) -> dict:
        return instance_dict(cls)


class ClientForm(Form):
    directory = CourtDirectory()

    billing_id = StringField(
        "Billing ID",
        [validators.DataRequired(), validators.Length(min=4, max=5, message="Enter the client's billing ID without the matter suffix.")]
    )

    name = FormField(ContactName)
    referrer = FormField(Referral)
    health_ins = FormField(Insurance, "Health Insurance")
    dental_ins = FormField(Insurance, "Dental Insurance")

    client_ssn = StringField(
        "Client SSN",
        [validators.DataRequired(), validators.Length(min=3, max=3)]
    )
    client_dl = StringField(
        "Client Driver's License",
        [validators.DataRequired(), validators.Length(min=3, max=3)]
    )
    address = FormField(ContactAddress)
    email = EmailField(
        "Client email",
        [validators.DataRequired()]
    )
    telephone = TelField(
        "Telephone",
        [validators.Optional()]
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
    crm_state = SelectField(
        "CRM State",
        choices=CRM_STATES
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
    unbilled_fees = StringField(
        "Unbilled fees", [validators.Optional(), DollarCleaner(min=0)]
    )
    unbilled_costs = StringField(
        "Unbilled costs", [validators.Optional(), DollarCleaner(min=0)]
    )
    final_bill_flag = BooleanField(
        "Final bill?",
        false_values=('N', '')
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
        choices=directory.get_county_tuples(),
        validators=[validators.Optional()]
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
    oag_number = StringField("OAG number")
    case_style = StringField("Style")
    client_dob = DateField(
        "Client's DOB",
        validators=[validators.Optional()]
    )
    marriage_date = DateField(
        "Date of Marriage",
        validators=[validators.Optional()]
    )
    separation_date = DateField(
        "Date of Separation",
        validators=[validators.Optional()]
    )
    retained_date = DateField(
        "Retained on",
        validators=[validators.Optional()]
    )
    filed_date = DateField(
        "Filed on",
        validators=[validators.Optional()]
    )
    completion_date = DateField(
        "Completed on",
        validators=[validators.Optional()]
    )

    @classmethod
    def get(cls) -> dict:
        return instance_dict(cls)
