"""
db_admins.py - Class for access our persistent data store for admins.

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import os

from util.logger import get_logger
from util.database import Database

try:
    DB_URL = os.environ["DB_URL"]
except KeyError as e:
    get_logger('db_admins').fatal(
            "Database connection string environment variable is not set: %s",
            str(e))
    exit()

COLLECTION_NAME = 'admins'


class DbAdmins(Database):
    """
    Encapsulates a database accessor for admins
    """
    # FKA get_admin_record
    def admin_record(self, email: str) -> dict:
        """
        Retrieve the admin record associated with the given email.
        The admin record will have a list call 'for', which is a list
        of attorney initials for which the admin user is an administrator.
        For attorneys, this list will probably just have their initials,
        e.g. ['TJD']. For paralegals, it will probably have a list with
        an entry for each attorney she or he supports, e.g. ['TJD', 'BSL']
        """
        # Create lookup filter
        filter_ = {'email': email.lower()}

        # Locate matching admin record
        document = self.dbconn[COLLECTION_NAME].find_one(filter_)
        return document

    # FKA get_authorizations
    def authorizations(self, email: str) -> list:
        """
        Retrieve a list of authorizations for the user identified by *email*.
        """
        admin_record = self.admin_record(email)
        return list(admin_record.get('authorizations', []))

    def click_up_team_name(self, email: str) -> str:
        """
        Retrieve the Click Up team name for this user.

        Params:
            email (str): Email of the user to look up.

        Returns:
            (str): Team name
        """
        admin_record = self.admin_record(email)
        return admin_record.get('click_up_team_name', os.environ.get('CLICK_UP_DEFAULT_TEAM'))

    def click_up_workspace_name(self, email: str) -> str:
        """
        Retrieve the Click Up workspace name for this user.

        Params:
            email (str): Email of the user to look up.

        Returns:
            (str): Workspace name
        """
        admin_record = self.admin_record(email)
        print(f"********* EMAIL: '{email}'")
        return admin_record.get('click_up_workspace_name', os.environ.get('CLICK_UP_DEFAULT_WORKSPACE'))
