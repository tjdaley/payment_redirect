"""
authorizatins.py - Provide authorizations information.

Coyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
AUTH_DOWNLOAD_CLIENTS = 'DOWNLOAD_CLIENTS'
AUTH_SEND_EVERGREEN = 'SEND_EVERGREEN'
AUTH_TEMPLATE_ADMIN = 'TEMPLATE_ADMIN'
AUTH_USER_ADMIN = "USER_ADMIN"

AUTHORIZATIONS = [
    {'key': AUTH_DOWNLOAD_CLIENTS, 'description': "Download client lists"},
    {'key': AUTH_SEND_EVERGREEN, 'description': "Send evergreen letters"},
    {'key': AUTH_TEMPLATE_ADMIN, 'description': "Administer email templates"},
    {'key': AUTH_USER_ADMIN, 'description': "Administer Users"}
]

AUTHORIZATION_OPTIONS = [(a['key'], a['description']) for a in AUTHORIZATIONS]
