# payment_redirect
Redirect clients to a payment link.

<p align="center">
    <a href="https://github.com/tjdaley/payment_redirect/issues"><img alt="GitHub issues" src="https://img.shields.io/github/issues/tjdaley/payment_redirect"></a>
    <a href="https://github.com/tjdaley/payment_redirect/network"><img alt="GitHub forks" src="https://img.shields.io/github/forks/tjdaley/payment_redirect"></a>
    <a href="https://github.com/tjdaley/payment_redirect/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/tjdaley/payment_redirect"><a>
    <!-- img alt="PyPI - License" src="https://img.shields.io/pypi/l/payment_redirect" -->
    <img alt="Stage: Development" src="https://img.shields.io/badge/stage-Development-orange">
</p>
<p align="center">
    <a href="#purpose">Purpose</a> &bull;
    <a href="#installation">Installation</a> &bull;
    <a href="#author">Author</a>
</p>

## Purpose
Make it easy for clients to make the required payment on their account.
Authorized users set up a client record and update it with the amount
the client is required to pay to bring their account up to date. When the
client visits the URL and enters identifying information, the client is
redirected to a payment URL with the amount pre-filled.

## Installation
```
git clone https://github.com/tjdaley/payment_redirect
python3 -m venv env
./venv/bin/activate
pip3 install -r requirements.txt
```

After the installation scripts run, you'll need to create ```.env``` in the ```app``` folder:
```
$ cd app
$ vi .env
```

## AZURE Configuration
This application uses Microsoft Azure services for authentication and plan management. For the application
to work properly you'll need to create an Azure app as follows:

1. Login to your Azure portal by browsing to [https://portal.azure.com](https://portal.azure.com)
2. At the top of the portal, search for "App Registration"
3. Register a new app.
   A. Name: your users will see this
   B. Supported Account Types: Select the top option, "Accounts in this organizational directory only (Default Directory only - single tenant)
   C. Redirect URI: The URL to your installation plus "/getAToken", e.g. on a test machine "http://localhost:5000/getAToken" and on
      production server it might be "https://myurl.com/getAToken"
   D. Click "REGISTER"
4. After you save your registration, select the app you just registered to bring up the full configuration screen.
   A. OVERVIEW
      i. Redirect URIs: Click here if you need to add another URI. For example, if you entered your test machine's URI at step 3.C above
         now you can add your production machine.
   B. BRANDING
      i. NAME: Whatever you want. Users will see this.
      ii. UPLOAD NEW LOGO: Upload your logo file.
      iii. HOME PAGE URL: https://yoururl.com/crm
      iv. TERMS OF SERVICE URL: https://yoururl.com/terms_and_conditions
      v. PRIVACY STATEMENT: https://yoururl.com/privacy
   C. AUTHENTICATION
      i. FRONT-CHANNEL LOGOUT URL: https://yoururl.com/logout
      ii. IMPLICIT GRANT AND HYBRID FLOWS: Don't select either option.
      iii. SUPPORTED ACCOUNT TYPES: Select "Accounts in this organizational directory only (XXX - Single Tenant)
   D. CERTIFICATES & SECRETS
      i. CLIENT SECRETS: Add a new client secret and save the **VALUE** and the **ID** properties.
   E. API PERMISSIONS: You'll need to grant the following permissions (delegated):
      i. openid
      ii. profile
      iii. Tasks.ReadWrite
      iv. Tasks.ReadWrite.Shared
      v. User.Read
      vi. User.ReadBasic.All

      To grant these permissions:
      i. Click "Add a permission"
      ii. Click "Microsoft Graph" under the "Microsoft APIs" tab
      iii. Selected "Delegated permissions"
      iv. Type in the permission name from the list above and select each one.
      

## Startup
```python
python3 server.py
```

## Implemented Utilities

### /clients, /client

Authenticates an administrative user and let's the user CRUD client
records including payment due amount and date. Authentication is
performed through Microsoft's identity provider service API.

### /crm

A client relationship management view of the database, with RingCentral integration
for SMS messaging and phone calls and Amazon SES integration for bulk email.

### /pay

Prompts the user for the last three digits of their Social Security number
and the last three digits of their driver's license. If a match is found in
the database, the user is redirected to a pre-populated payment page.

### /pay/<string:client_id>

*client_id* is formatted so that the first three characters are the last
three digits of the user's Social Security number, the next three characters
are the last three digits of the user's Driver's License number, and the last
character is a check-digit, for now A-Z.

For example, if the user's Social Security number is XXX-XX-X123 and their
driver's license number is XXXXX456, the *client_id* would be '123456V'.

## Azure Configuration

Start at [portal.azure.com](https://portal.azure.com).

## Email Lists

There are several email lists that are combined in differnt ways, depending on the context of the email.

Here are the lists:
1. clients.email_cc_list
1. clients.admin_users
2. admins.default_cc_list
3. contacts.email_cc
4. clients_contacts.email_cc

### Emails to Clients

When generating an email to our client, we combine these lists:
1. If clients.email_cc_list is populated, use clients.email_cc_list.
2. Otherwise use clients.admin_users

_Client wants all emails copied to another person_
So, if a client has a parent or other person who is to be copied on all emails,
populate the clients.email_cc_list with the email addresses provided by the client
to copy **AND** include internal email addresses that should receive all client
communications.

For example: Suppose the client wants all emails to her to be copied to her brother at
brother@family.com and that the following internal people need to be copied: tom@lawfirm.com and james@lawfirm.com. In that
scenario, populate clients.email_cc_list as follows: ```brother@family.com;tom@lawfirm.com;james@lawfirm.com```.

_Some internal people who have access to this client record do NOT want to be copied on all emails to the client_
Say lawyer1@lawfirm.com; lawyer2@lawfirm.com, and para1@lawfirm.com all have access to this client. That means
that each of those emails is in the clients.admin_users list. However, suppose laweryer1@lawfirm.com does NOT want
to be copied on all client emails. To override this list, and assuming the client did not ask for someone to
be copied on all emails, populate clients.email_cc_list as follows: ```lawer2@lawfirm.com;para1@lawfirm.com```. In
doing that, lawye1@lawfirm.com will still have access to the case file, but will not receive emails sent to clients.

### Emails to Contacts in Connection with a Case

When generating an email to a contact in connection with a case, e.g. clicking the email button from within the
_players_ tab of the _client_ view, we use these lists:
1. If clients_contacts.email_cc is populated, use clients_contacts.email_cc
2. Otherwise, combine contacts.email_cc with clients.admin_users

_Contact wants all emails sent to an assistant, specific to this case._
When linking the contact to the case, specify an email cc list. This list must contain the emails that the contact
wants us to copy PLUS internal emails that should be copied when emailing this contact.

_Some internal people who have access to this client record do NOT want to be copied on all emails to the contact_
Say lawyer1@lawfirm.com; lawyer2@lawfirm.com, and para1@lawfirm.com all have access to this client. That means
that each of those emails is in the clients.admin_users list. However, suppose laweryer1@lawfirm.com does NOT want
to be copied on all emails to a particular contact. To override this list, and assuming the contact did not ask for someone to
be copied on all emails, populate clients_contacts.email_cc as follows: ```lawer2@lawfirm.com;para1@lawfirm.com```. In
doing that, lawye1@lawfirm.com will still have access to the case file, but will not receive emails sent to this contact.


## Author

Thomas J. Daley, J.D. is an active, board-certified family law litigation attorney practicing primarily in Collin County, Texas, a family law mediator, and software developer. My Texas based family law practice is limited to divorce, child custody, child support, enforcment, and modification suits. [Web Site](https://koonsfuller.com/attorneys/tom-daley/)
