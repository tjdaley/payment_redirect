"""
dialer.py - Dial calls and send SMS messages.

Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import json
import os
from ringcentral import SDK


class Dialer(object):
    DEBUG = os.environ.get('DEBUG', 0) == 1
    RING_CENTRAL_CLIENTID = os.environ.get('RING_CENTRAL_CLIENTID')
    RING_CENTRAL_CLIENTSECRET = os.environ.get('RING_CENTRAL_CLIENTSECRET')
    RING_CENTRAL_SERVER = os.environ.get('RING_CENTRAL_SERVER')

    RING_OUT_ENDPOINT = '/restapi/v1.0/account/~/extension/~/ring-out'
    SMS_ENDPOINT = '/restapi/v1.0/account/~/extension/~/sms'

    @staticmethod
    def dial(
        from_number: str,
        to_number: str,
        username: str,
        extension: str,
        password: str,
        play_prompt: bool = True
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

        Returns:
            None
        """
        try:
            step = "Instantiating SDK"
            if Dialer.DEBUG:
                print("Params:", Dialer.RING_CENTRAL_CLIENTID, Dialer.RING_CENTRAL_CLIENTSECRET, Dialer.RING_CENTRAL_SERVER)
            rcsdk = SDK(Dialer.RING_CENTRAL_CLIENTID, Dialer.RING_CENTRAL_CLIENTSECRET, Dialer.RING_CENTRAL_SERVER)
            step = "Instantiating Platform"
            platform = rcsdk.platform()
            step = "Logging in to platform"
            if Dialer.DEBUG:
                print("Params:", username, extension, password)
            platform.login(username, extension, password)
            step = "Connecting to Rint-Out End Point"
            response = platform.post(
                Dialer.RING_OUT_ENDPOINT,
                {
                    'from': {'phoneNumber': username},
                    'to': {'phoneNumber': to_number},
                    'playPrompt': play_prompt
                }
            )
            if Dialer.DEBUG:
                print("RESPONSE:", json.dumps(response.json_dict(), indent=4))
        except Exception as e:
            return {'success': False, 'message': str(e), 'step': step}
        return {'success': True, 'message': "Call in progress"}

    @staticmethod
    def message(
        from_number: str,
        to_number: str,
        username: str,
        extension: str,
        password: str,
        message: str
    ):
        """
        Dial a number on behalf of our user.

        Args:
            from_number (str): Number that appears in call recipient's caller-id
            to_number (str): Number we want to dial
            username (str): Ringcentral username (probably our user's main number or direct-dial number)
            extension (str): Ringcentral extension for our user
            password (str): Ringcentral password for our user
            message (text): Message text to send

        Returns:
            None
        """
        try:
            step = "Instantiating SDK"
            if Dialer.DEBUG:
                print("Params:", Dialer.RING_CENTRAL_CLIENTID, Dialer.RING_CENTRAL_CLIENTSECRET, Dialer.RING_CENTRAL_SERVER)
            rcsdk = SDK(Dialer.RING_CENTRAL_CLIENTID, Dialer.RING_CENTRAL_CLIENTSECRET, Dialer.RING_CENTRAL_SERVER)
            step = "Instantiating Platform"
            platform = rcsdk.platform()
            step = "Logging in to platform"
            if Dialer.DEBUG:
                print("Params:", username, extension, password)
            platform.login(username, extension, password)
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
                print("RESPONSE:", json.dumps(response.json_dict(), indent=4))
        except Exception as e:
            return {'success': False, 'message': str(e), 'step': step}
        return {'success': True, 'message': "Message sent"}
