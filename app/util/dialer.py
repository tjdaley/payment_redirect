"""
dialer.py - Dial calls and send SMS messages.

Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import json
import os
from ringcentral import SDK, http
from util.logger import get_logger


class Dialer(object):
    DEBUG = os.environ.get('DEBUG', 0) == 1
    RING_CENTRAL_CLIENTID = os.environ.get('RING_CENTRAL_CLIENTID')
    RING_CENTRAL_CLIENTSECRET = os.environ.get('RING_CENTRAL_CLIENTSECRET')
    RING_CENTRAL_SERVER = os.environ.get('RING_CENTRAL_SERVER')
    RING_CENTRAL_AUTH_METHOD = os.environ.get('RING_CENTRAL_AUTH_METHOD', 'password')

    # Index into session where we'll find the RingCentral access token from OAuth
    RING_CENTRAL_SESSION_KEY = os.environ.get('RING_CENTRAL_ACESS_TOKEN_SESSION_KEY', 'rcSessionAccessToken')
    RING_CENTRAL_AUTH_KEY = os.environ.get('RING_CENTRAL_AUTH_CODE_KEY', 'rcAuthCode')

    RING_OUT_ENDPOINT = '/restapi/v1.0/account/~/extension/~/ring-out'
    SMS_ENDPOINT = '/restapi/v1.0/account/~/extension/~/sms'

    rcsdk = SDK(RING_CENTRAL_CLIENTID, RING_CENTRAL_CLIENTSECRET, RING_CENTRAL_SERVER)

    LOGGER = get_logger('.dialer')

    @staticmethod
    def get_oauth_tokens(auth_code: str, redirect_url: str):
        """
        Get OAuth Tokens for application login.
        """
        platform = Dialer.rcsdk.platform()
        platform.login('', '', '', auth_code, redirect_url)
        tokens = platform.auth().data()
        return tokens

    @staticmethod
    def logout(session_access_token):
        """
        Logout of RingCentral's OAuth Service.
        """
        platform = Dialer.rcsdk.platform()
        platform.auth().set_data(session_access_token)
        if platform.logged_in():
            platform.logout()

    @staticmethod
    def logged_in(session_access_token: str):
        """
        Return True if logged in OR if auth method is not OAUTH
        """
        if Dialer.RING_CENTRAL_AUTH_METHOD != 'OAUTH':
            return True

        if session_access_token is None:
            return False

        platform = Dialer.rcsdk.platform()
        platform.auth().set_data(session_access_token)

        return platform.logged_in()

    @staticmethod
    def dial(
        from_number: str,
        to_number: str,
        username: str,
        extension: str,
        password: str,
        play_prompt: bool = True,
        session_access_token: str = None
    ):
        """
        Dial a number on behalf of our user.

        Args:
            from_number (str): Number that appears in call recipient's caller-id
            to_number (str): Number we want to dial
            username (str): Ringcentral username (probably our user's main number or direct-dial number)
            extension (str): Ringcentral extension for our user
            password (str): Ringcentral password for our user
            play_prompt (bool): Whether to prompt our user to press 1 before connecting the call (default=True)
            session_access_token (str): Saved to session when using OAuth vs. password authorization

        Returns:
            None
        """
        if not Dialer.logged_in(session_access_token):
            return {'success': False, 'message': 'Need to login to RingCentral', 'rc_login_needed': True}

        try:
            step = "Instantiating Platform"
            platform = Dialer.rcsdk.platform()
            step = "Logging in to platform"
            if Dialer.DEBUG:
                Dialer.LOGGER.debug("Params: Username=%s  x=%s  pwd=%s", username, extension, password)
            if Dialer.RING_CENTRAL_AUTH_METHOD != 'OAUTH':
                platform.login(username, extension, password)
            # else:
            #    platform.auth().set_data(session_access_token)
            step = "Connecting to Ring-Out End Point"
            response = platform.post(
                Dialer.RING_OUT_ENDPOINT,
                {
                    'from': {'phoneNumber': username},
                    'to': {'phoneNumber': to_number},
                    'playPrompt': play_prompt
                }
            )
            if Dialer.DEBUG:
                Dialer.LOGGER.debug("RESPONSE: %s", json.dumps(response.json_dict(), indent=4))
        except http.api_exception.ApiException as e:
            status = {'success': False, 'message': str(e), 'step': step, 'rc_login_needed': True}
            return status
        except Exception as e:
            status = {'success': False, 'message': str(e), 'step': step}
            get_logger('.dialer.dial').exception(e)
            return status
        return {'success': True, 'message': "Call in progress"}

    @staticmethod
    def message(
        from_number: str,
        to_number: str,
        username: str,
        extension: str,
        password: str,
        message: str,
        session_access_token: str = None
    ):
        """
        Send an SMS text message on behalf of our user.

        Args:
            from_number (str): Number that appears in call recipient's caller-id
            to_number (str): Number we want to dial
            username (str): Ringcentral username (probably our user's main number or direct-dial number)
            extension (str): Ringcentral extension for our user
            password (str): Ringcentral password for our user
            message (text): Message text to send
            session_access_token (str): Saved to session when using OAuth vs. password authorization

        Returns:
            None
        """
        if not Dialer.logged_in(session_access_token):
            return {'success': False, 'message': 'Need to login to RingCentral', 'rc_login_needed': True}

        try:
            step = "Instantiating Platform"
            platform = Dialer.rcsdk.platform()
            step = "Logging in to platform"
            if Dialer.DEBUG:
                Dialer.LOGGER.debug("Params: Username=%s  x=%s  pwd=%s", username, extension, password)
            if Dialer.RING_CENTRAL_AUTH_METHOD != 'OAUTH':
                platform.login(username, extension, password)
            # else:
            #    platform.auth().set_data(session_access_token)
            step = "Connecting to Rint-Out End Point"
            response = platform.post(
                Dialer.SMS_ENDPOINT,
                {
                    'from': {'phoneNumber': username},
                    'to': [{'phoneNumber': to_number}],
                    'text': message
                }
            )
            if Dialer.DEBUG:
                Dialer.LOGGER.debug("RESPONSE: %s", json.dumps(response.json_dict(), indent=4))
        except http.api_exception.ApiException as e:
            status = {'success': False, 'message': str(e), 'step': step, 'rc_login_needed': True}
            return status
        except Exception as e:
            status = {'success': False, 'message': str(e), 'step': step}
            get_logger('.dialer.message').exception(e)
            return status
        return {'success': True, 'message': "Message sent"}
