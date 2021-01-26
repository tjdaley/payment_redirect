"""
msftgraph.py - Microsoft Graph convenience API
"""
import datetime
import msftconfig
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
    def graphcall(endpoint: str, method: str = 'get', data: dict = None) -> dict:
        """
        Make a call to a Microsoft Office 365 Graph endpoint.
        If we can't get a token from the token cache, either the user never logged in
        OR the AZURE_SCOPE constant in msftconfig.py has changed since the user's last
        login, which happens when I add features that need additional Msft Graph scopes.

        Therefore, if we can't find the token, we'll return an error.

        Args:
            endpoint (str): URL of endpoint.

        Returns:
            (dict): Data returned by Microsoft Office 365 Graph endpoint.
        """
        print(endpoint)
        token = MicrosoftGraph.get_token_from_cache(msftconfig.AZURE_SCOPE)
        if not token:
            return {'error': {'message': "<html><H1>Login required</h1></html>"}, 'require_login': True}

        headers = {
                    'Authorization': 'Bearer ' + token['access_token']
        }

        if method == 'get':
            graph_data = requests.get(  # Use token to call downstream service
                endpoint,
                headers={
                    'Authorization': 'Bearer ' + token['access_token']
                },
            ).json()

        if method == 'post':
            headers['Content-Type'] = 'application/json'
            graph_data = requests.post(
                endpoint,
                json=data,
                headers=headers
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
            if graph_data.get('require_login', False) is True:
                return redirect(url_for(os.environ['LOGIN_FUNCTION']))
            return graph_data['error']['message']
        return jsonify(graph_data)

    @staticmethod
    def create_bucket(plan_id: str, plan: dict):
        """
        Create a bucket within a plan.

        Args:
            plan_id (str): The m365 plan-id associated with our client.
            plan (dict): Contains the name and orderHint properties
        Returns:
            (dict): The response from the Microsoft Graph call.
        """
        graph_data = MicrosoftGraph.graphcall(
            msftconfig.AZURE_PLANNER_CREATE_BUCKET_ENDPOINT,
            'post',
            {
                'name': plan.get('name'),
                'planId': plan_id,
                'orderHint': ' !'
            }
        )
        return graph_data

    @staticmethod
    def create_bucket_task(task: dict):
        """
        Create a task within a bucket.

        Args:
            task (dict): Dict containing these keys:
                planId (str): Microsoft graph plan id
                bucketId (str): Microsoft graph bucket id
                title (str): Title of the task
                dueDateTime (str): Date task is due
                orderHint (str): Microsoft graph string to set the order of items.

        Returns:
            (dict): The response from the Microsoft Graph Call.
        """
        graph_data = MicrosoftGraph.graphcall(
            msftconfig.AZURE_PLANNER_CREATE_BUCKET_TASK_ENDPOINT,
            'post',
            task
        )
        return graph_data

    @staticmethod
    def create_bucket_from_template(plan_id, template, start_date=None):
        plan = template.get('plan')
        graph_data = MicrosoftGraph.create_bucket(plan_id, plan)
        if 'error' in graph_data:
            return graph_data
        bucket_id = graph_data.get('id')

        if start_date:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%s.%f')
        else:
            start_date = datetime.datetime.now()

        tasks = plan.get('tasks', [])
        if not tasks:
            return {'success': True, 'message': "Plan created without tasks."}

        due_dates = {}  # indexed by stepName
        due_dates[tasks[0]['stepName']] = start_date
        graph_tasks = []  # This is the payload for the call to Microsoft Graph's endpoint

        # Create the task objects (dicts)
        for task in tasks:
            ref_key, increment_days, day_type = task.get('dueDateTime', '').split(' ')
            int_days = int(increment_days)
            due_date = add_days(due_dates.get(ref_key, start_date), int_days, day_type)
            due_dates[task.get('stepName', ' !')] = due_date
            title = task.get('title')
            t = {
                'planId': plan_id,
                'bucketId': bucket_id,
                'title': title,
                'dueDateTime': str(due_date)[:10]
            }
            graph_tasks.insert(0, t)  # Maintain the list with the newest on top. It's a Graph thing . . .

        # Now add them to the plan.
        # We do it this way because, without some horrible gymnastics, the UI will show the tasks in
        # bucket view in the order in which they were created, newest at the top. That's the opposite
        # of what we want.
        prev_order_hint = ''
        for task in graph_tasks:
            task['orderHint'] = f'{prev_order_hint} !'
            graph_data = MicrosoftGraph.create_bucket_task(task)
            if 'error' in graph_data:
                print(graph_data)
            prev_order_hint = graph_data.get('orderHint')
        return {'success': True}


def add_days(start_date, increment_days: int, day_type: str):
    """
    Compute a date by adding (or subtracting) days from the start date.
    We can add/subtract calendar days or work days.

    Args:
        start_date (datetime): Starting date
        increment_days (int): Number of days to add or subtract
        day_type (str): "W" for work days or "C" for calendar days.

    Returns:
        (datetime): New date.
    """
    # wd = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    # print("Start: ", str(start_date), "(", wd[start_date.weekday()], ")",
    #      "Increment:", increment_days, "Type:", day_type)
    if day_type.upper() == 'C':
        result = start_date + datetime.timedelta(days=increment_days)
    #    print(".......", result, "(", wd[result.weekday()], ")")
        return result

    # Here to handle work days (but, for now, does not consider holidays)
    days_added = 0
    while days_added < abs(increment_days):
        start_date = start_date + datetime.timedelta(days=1)
        if start_date.weekday() <= 4:  # Mon - Fri
            days_added += 1

    # print(".......", start_date, "[", wd[start_date.weekday()], "]")
    return start_date
