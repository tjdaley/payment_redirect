"""
msftconfig.py - Contains non-secret config details

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
AZURE_USER_ENDPOINT = f'{BASE_URL}/{VERSION}/users/[id]'
AZURE_TODO_LISTS_ENDPOINT = f'{BASE_URL}/{VERSION}/me/todo/lists'
AZURE_TODO_TASKS_ENDPOINT = f'{BASE_URL}/{VERSION}/me/todo/lists/[todoTaskListId]/tasks?$top=1000'
AZURE_TODO_TASK_ENDPOINT = f'{BASE_URL}/{VERSION}/me/todo/lists/[todoTaskListId]/tasks/[taskId]'
AZURE_TODO_LINKEDRESOURCES_ENDPOINT = f'{BASE_URL}/{VERSION}/me/todo/lists/[todoTaskListId]/tasks/[todoTaskId]/linkedresources'
AZURE_TODO_LINKEDRESOURCE_ENDPOINT = f'{BASE_URL}/{VERSION}/me/todo/lists/[todoTaskListId]/tasks/[todoTaskId]/linkedresources/[linkedResourceId]'
AZURE_PLANNER_PLANS_ENDPOINT = f'{BASE_URL}/{VERSION}/groups/[group-id]/planner/plans'
AZURE_PLANNER_PLAN_ENDPOINT = f'{BASE_URL}/{VERSION}/planner/plans/[plan-id]'
AZURE_PLANNER_BUCKETS_ENDPOINT = f'{BASE_URL}/{VERSION}/planner/plans/[plan-id]/buckets'
AZURE_PLANNER_BUCKET_ENDPOINT = f'{BASE_URL}/{VERSION}/planner/buckets/[id]'
AZURE_PLANNER_BUCKET_TASKS_ENDPOINT = f'{BASE_URL}/{VERSION}/planner/buckets/[id]/tasks'
AZURE_PLANNER_CREATE_BUCKET_ENDPOINT = f'{BASE_URL}/{VERSION}/planner/buckets'
AZURE_PLANNER_CREATE_BUCKET_TASK_ENDPOINT = f'{BASE_URL}/{VERSION}/planner/tasks'
