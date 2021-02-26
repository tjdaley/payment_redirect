"""
client_tabs.py - Data to define tabs on the crm client view.

Data used to create divs in this form:

<li class="nav-item">
    <a class="nav-link active" id="name-tab" data-toggle="tab" href="#name" role="tab" aria-controls="name"
        aria-selected="true">Name</a>
</li>


Copyright (c) 2020 by Thomas J. Daley, J.D.
"""
default_li_class = 'nav-item'
default_a_class = 'nav-link'

# Tabs will appear in the order below.
client_tabs = [{
    'li_class': default_li_class,
    'a_class': 'nav-link active',
    'name': 'name',
    'label': "Name",
    'selected': 'true'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'address',
    'label': "Address",
    'selected': 'false'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'contact',
    'label': "Contact",
    'selected': 'false'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'case',
    'label': "Case",
    'selected': 'false'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'contacts',
    'label': "Players",
    'selected': 'false'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'children',
    'label': "Children",
    'selected': 'false'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'billing',
    'label': "Billing",
    'selected': 'false'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'id',
    'label': "ID",
    'selected': 'false'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'dates',
    'label': "Dates",
    'selected': 'false'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'plan',
    'label': "Plan",
    'selected': 'false',
    'required_authorization': 'PIONEER_USER'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'insurance',
    'label': "Insurance",
    'selected': 'false'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'marketing',
    'label': "Marketing",
    'selected': 'false'
}, {
    'li_class': default_li_class,
    'a_class': default_a_class,
    'name': 'access',
    'label': "Access",
    'selected': 'false'
}]
