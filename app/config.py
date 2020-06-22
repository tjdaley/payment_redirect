"""
config.py - Contains non-secret config details

This file contains config settings that are easiest expressed in Python.
"""
AZURE_SCOPE = ['User.ReadBasic.All']
AZURE_USERS_ENDPOINT = 'https://graph.microsoft.com/v1.0/users?$top=500'
