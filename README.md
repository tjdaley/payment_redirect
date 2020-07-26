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
./env/bin/activate
pip3 install -r requirements.txt
```

After the installtion scripts run, you'll need to create ```.env``` in the ```app``` folder:
```
$ cd app
$ vi .env
```

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

## Author

Thomas J. Daley, J.D. is an active family law litigation attorney practicing primarily in Collin County, Texas, a family law mediator, and software developer. My Texas based family law practice is limited to divorce, child custody, child support, enforcment, and modification suits. [Web Site](https://koonsfuller.com/attorneys/tom-daley/)
