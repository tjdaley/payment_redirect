"""
authorizations.py - Provide authorizations information.

Coyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
AUTH_CRM_USER = "CRM_USER"
AUTH_DOWNLOAD_CLIENTS = 'DOWNLOAD_CLIENTS'
AUTH_DOWNLOAD_CONTACTS = 'DOWNLOAD_CONTACTS'
AUTH_DOWNLOAD_VCARD = 'DOWNLOAD_VCARD'
AUTH_SEND_EVERGREEN = 'SEND_EVERGREEN'
AUTH_TEMPLATE_ADMIN = 'TEMPLATE_ADMIN'
AUTH_USER_ADMIN = "USER_ADMIN"
AUTH_EDIT_REFERRER = 'EDIT_REFERRER'
AUTH_EDIT_GLOBAL_SETTINGS = 'EDIT_GLOBAL_SETTINGS'

AUTHORIZATIONS = [
    {'key': AUTH_CRM_USER, 'description': "Access CRM features"},
    {'key': AUTH_DOWNLOAD_CONTACTS, 'description': "Download contact lists"},
    {'key': AUTH_DOWNLOAD_CLIENTS, 'description': "Download client lists"},
    {'key': AUTH_DOWNLOAD_VCARD, 'description': "Download v-card"},
    {'key': AUTH_SEND_EVERGREEN, 'description': "Send evergreen letters"},
    {'key': AUTH_TEMPLATE_ADMIN, 'description': "Administer email templates"},
    {'key': AUTH_USER_ADMIN, 'description': "Administer Users"},
    {'key': AUTH_EDIT_REFERRER, 'description': "Edit referrer"},
    {'key': AUTH_EDIT_GLOBAL_SETTINGS, 'description': "Edit global settings"}
]

AUTHORIZATION_OPTIONS = [(a['key'], a['description']) for a in AUTHORIZATIONS]
