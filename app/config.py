"""
config.py - Contains non-secret config details

This file contains config settings that are easiest expressed in Python.
"""
AZURE_SCOPE = [
    'User.ReadBasic.All',
    'Tasks.Read',
    'Tasks.Read.Shared',
    'Tasks.ReadWrite',
    'Tasks.ReadWrite.Shared'
]
BASE_URL = 'https://graph.microsoft.com'
VERSION = 'v1.0'
AZURE_USERS_ENDPOINT = f'{BASE_URL}/{VERSION}/users?$top=500'
AZURE_TODO_LISTS_ENDPOINT = f'{BASE_URL}/{VERSION}/me/todo/lists'
AZURE_TODO_TASKS_ENDPOINT = f'{BASE_URL}/{VERSION}/me/todo/lists/[todoTaskListId]/tasks?$top=1000'
AZURE_TODO_TASK_ENDPOINT = f'{BASE_URL}/{VERSION}/me/todo/lists/[todoTaskListId]/tasks/[taskId]'
AZURE_TODO_LINKEDRESOURCES_ENDPOINT = f'{BASE_URL}/{VERSION}/me/todo/lists/[todoTaskListId]/tasks/[todoTaskId]/linkedresources'
AZURE_TODO_LINKEDRESOURCE_ENDPOINT = f'{BASE_URL}/{VERSION}/me/todo/lists/[todoTaskListId]/tasks/[todoTaskId]/linkedresources/[linkedResourceId]'
