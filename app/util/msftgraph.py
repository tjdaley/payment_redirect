"""
msftgraph.py - Microsoft Graph convenience API
"""
import config
from flask import jsonify, redirect, session, url_for
import msal
import requests
import uuid
import os

from util.logger import get_logger


class MicrosoftGraph(object):
    """
    Encapsulates our interface into Microsoft's Graph interface for
    retrieving information from Azure services.
    """
    @staticmethod
    def build_msal_app(cache=None, authority=None):
        client_id = os.environ['AZURE_CLIENT_ID']
        client_secret = os.environ['AZURE_CLIENT_SECRET']
        config_authority = os.environ['AZURE_AUTHORITY']
        return msal.ConfidentialClientApplication(
            client_id,
            authority=authority or config_authority,
            client_credential=client_secret,
            token_cache=cache,
        )

    @staticmethod
    def build_auth_url(authority=None, scopes: list = None, state=None):
        redirect_uri = os.environ.get('AZURE_REDIRECT_PATH')
        get_logger("pmtredir.admin").info("B %s", redirect_uri)
        return MicrosoftGraph.build_msal_app(authority=authority).get_authorization_request_url(
            scopes or [],
            state=state or str(uuid.uuid4()),
            redirect_uri=redirect_uri
        )

    @staticmethod
    def load_cache():
        cache = msal.SerializableTokenCache()
        if session.get("token_cache"):
            cache.deserialize(session["token_cache"])
        return cache

    @staticmethod
    def save_cache(cache):
        if cache.has_state_changed:
            session["token_cache"] = cache.serialize()

    @staticmethod
    def get_token_from_cache(scope=None):
        cache = MicrosoftGraph.load_cache()  # This web app maintains one cache per session
        cca = MicrosoftGraph.build_msal_app(cache=cache)
        accounts = cca.get_accounts()
        if accounts:  # So all account(s) belong to the current signed-in user
            result = cca.acquire_token_silent(scope, account=accounts[0])
            MicrosoftGraph.save_cache(cache)
            return result

    @staticmethod
    def graphcall(endpoint: str) -> dict:
        """
        Make a call to a Microsoft Office 365 Graph endpoint.

        Args:
            endpoint (str): URL of endpoint.

        Returns:
            (dict): Data returned by Microsoft Office 365 Graph endpoint.
        """
        print(endpoint)
        token = MicrosoftGraph.get_token_from_cache(config.AZURE_SCOPE)
        if not token:
            return redirect(url_for(os.environ['LOGIN_FUNCTION']))
        graph_data = requests.get(  # Use token to call downstream service
            endpoint,
            headers={
                'Authorization': 'Bearer ' + token['access_token']
            },
        ).json()
        return graph_data

    @staticmethod
    def browser_graphcall(endpoint: str):
        """
        Wrapper for graphcall() that returns a result that can be returned
        through an HTTP response.

        Args:
            endpoint (str): URL of endpoint
        """
        graph_data = MicrosoftGraph.graphcall(endpoint)

        if 'error' in graph_data:
            return graph_data['error']['message']
        return jsonify(graph_data)
