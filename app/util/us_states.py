"""
us_states.py - Various forms of US States

From:
https://github.com/django/django-localflavor/blob/master/localflavor/us/us_states.py

Created 2020 by Thomas J. Daley, J.D.
"""

CONTIGUOUS_STATES = [
    ('AL', 'Alabama'),
    ('AZ', 'Arizona'),
    ('AR', 'Arkansas'),
    ('CA', 'California'),
    ('CO', 'Colorado'),
    ('CT', 'Connecticut'),
    ('DE', 'Delaware'),
    ('DC', 'District of Columbia'),
    ('FL', 'Florida'),
    ('GA', 'Georgia'),
    ('ID', 'Idaho'),
    ('IL', 'Illinois'),
    ('IN', 'Indiana'),
    ('IA', 'Iowa'),
    ('KS', 'Kansas'),
    ('KY', 'Kentucky'),
    ('LA', 'Louisiana'),
    ('ME', 'Maine'),
    ('MD', 'Maryland'),
    ('MA', 'Massachusetts'),
    ('MI', 'Michigan'),
    ('MN', 'Minnesota'),
    ('MS', 'Mississippi'),
    ('MO', 'Missouri'),
    ('MT', 'Montana'),
    ('NE', 'Nebraska'),
    ('NV', 'Nevada'),
    ('NH', 'New Hampshire'),
    ('NJ', 'New Jersey'),
    ('NM', 'New Mexico'),
    ('NY', 'New York'),
    ('NC', 'North Carolina'),
    ('ND', 'North Dakota'),
    ('OH', 'Ohio'),
    ('OK', 'Oklahoma'),
    ('OR', 'Oregon'),
    ('PA', 'Pennsylvania'),
    ('RI', 'Rhode Island'),
    ('SC', 'South Carolina'),
    ('SD', 'South Dakota'),
    ('TN', 'Tennessee'),
    ('TX', 'Texas'),
    ('UT', 'Utah'),
    ('VT', 'Vermont'),
    ('VA', 'Virginia'),
    ('WA', 'Washington'),
    ('WV', 'West Virginia'),
    ('WI', 'Wisconsin'),
    ('WY', 'Wyoming'),
]

#: Non contiguous states (Not connected to mainland USA)
NON_CONTIGUOUS_STATES = [
    ('AK', 'Alaska'),
    ('HI', 'Hawaii'),
]

US_STATES = (CONTIGUOUS_STATES + NON_CONTIGUOUS_STATES)
US_STATE_NAMES = {n: abbr for (abbr, n) in US_STATES}
US_STATE_ABBREVIATIONS = {abbr: n for (abbr, n) in US_STATES}

#: Non-state territories.
US_TERRITORIES = [
    ('AS', 'American Samoa'),
    ('GU', 'Guam'),
    ('MP', 'Northern Mariana Islands'),
    ('PR', 'Puerto Rico'),
    ('VI', 'Virgin Islands'),
]

#: Military postal "states". Note that 'AE' actually encompasses
#: Europe, Canada, Africa and the Middle East.
ARMED_FORCES_STATES = [
    ('AA', 'Armed Forces Americas'),
    ('AE', 'Armed Forces Europe'),
    ('AP', 'Armed Forces Pacific'),
]

#: Non-US locations serviced by USPS (under Compact of Free
#: Association).
COFA_STATES = [
    ('FM', 'Federated States of Micronesia'),
    ('MH', 'Marshall Islands'),
    ('PW', 'Palau'),
]
