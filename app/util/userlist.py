"""
userlist.py - A cache of user IDs from the Microsoft Graph API

Retrieving the list is a slow operation so we cache the list here.
Copyright (c) 2021 by Thomas J. Daley. All Rights Reserved.
"""
from enum import Enum


class Users(dict):
    """
    Extend Python's dict class for additional functions.
    """
    class UserFields(Enum):
        FIRST_NAME = 'givenName'
        LAST_NAME = 'surName'
        FULL_NAME = 'displayName'
        EMAIL = 'mail'
        ID = 'id'

    def __init__(this, userlist: dict):
        """
        Organize the given _userlist_ for our purposes.

        Args:
            userlist (dict): Retreived from Microsoft's Graph API.
        Returns:
            None
        """
        this.refresh(userlist)

    def refresh(this, userlist: dict):
        """
        Update our internal data with new data.

        Args:
            userlist (dict): Retrieved from Microsoft's Graph API.
        Returns:
            None
        """
        if 'value' not in userlist:
            raise ValueError("userlist does not contain a 'value' element. Check for errors.")

        this.clear()
        users = userlist.get('value', [])

        # Index users by userid and by email
        for user in users:
            this[user.get('id')] = user
            this[(user.get('mail', '') or '').lower()] = user

    def get_field(this, id_or_email: str, field_name: UserFields) -> str:
        """
        Returns the requested field.

        Args:
            id_or_email (str): Can be either the user's ID or their lowercase email address.
            field_name (UserFields enum): Key in the user's dict
        Returns:
            (str): The requested field's value or None.
        """
        return this.get(id_or_email, {}).get(field_name.value)


"""
Sample Data from Microsoft's Graph. This is what we're expecting as input.

{
    "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
    "value": [
    {
      "businessPhones": [],
      "displayName": "John Doe",
      "givenName": "John",
      "id": "77X27X74-X870-412X-X43X-75X5945b5649",
      "jobTitle": None,
      "mail": "jdoe@yourdomain.com",
      "mobilePhone": None,
      "officeLocation": None,
      "preferredLanguage": None,
      "surname": "Doe",
      "userPrincipalName": "jdoe@yourdomain.com"
    },
    {
      "businessPhones": [],
      "displayName": "Marshall Dillon",
      "givenName": "Marshall",
      "id": "898X6892-450X-4762-XX98-0XXXX5X5X2cX",
      "jobTitle": None,
      "mail": "mdillon@yourdomain.com",
      "mobilePhone": None,
      "officeLocation": None,
      "preferredLanguage": None,
      "surname": "Dillon",
      "userPrincipalName": "mdillon@yourdomain.com"
    },
    ]
}
"""
