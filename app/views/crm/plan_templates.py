"""
plan_templates.py - Retrieve plan templates

NOTE: The plans should be in the database. They are coded here while
I figure out the best way to represent them. /tjd/ 2020-01-10.

Copyright (c) 2021 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from enum import Enum


class PlanTemplates(object):
    class Template(Enum):
        """
        Plan IDs
        """
        OPEN_ENGAGEMENT = 1
        INITIAL_DISCLOSURES = 2
        DEPO_WRITTEN_QUES = 3
        DEPO_WRITTEN_QUES_DT = 4
        NON_PARTY_PROD = 5
        CLOSE_ENGAGEMENT = 9999

    def get(self, plan_id: Template) -> dict:
        """
        Retrieve a plan by ID

        Args:
            plan_id (Template): ID of plan template to retrieve.

        Returns:
            (dict): Result and, if successfully retrieved, the template.
        """
        plan = _retrieve(plan_id)
        if plan:
            return {
                'success': True,
                'plan': plan
            }
        return {
            'success': False,
            'message': "Plan not found"
        }


"""
The naming convention is taken from Msft's Graph naming convension.
"""
__PLANS = {
    1: {
        'name': "Engagement Open",
        'tasks': [
            {
                'title': "Verify fee agreement in file",
                'stepName': '0000.0000',
                'dueDateTime': '+2W',
                'assignTo': 'PARALEGAL'
            },
            {
                'title': "Verify intake form in file",
                'stepName': '0001.0000',
                'dueDateTime': '+2W',
                'assignTo': 'PARALEGAL'
            },
            {
                'title': "Collect initial retainer",
                'stepName': '0002.0000',
                'dueDateTime': '+2W',
                'assignTo': 'PARALEGAL'
            },
            {
                'title': "ProDoc setup",
                'stepName': '0003.0000',
                'dueDateTime': '+2W',
                'assignTo': 'PARALEGAL'
            },
            {
                'title': "Clean up CRM record",
                'stepName': '0004.0000',
                'dueDateTime': '+2W',
                'assignTo': 'PARALEGAL'
            }
        ]
    },
    2: {
        'name': "Initial Disclosures",
        'tasks': [
            {
                'title': "Send disclosure link to client",
                'stepName': '0000v0000',
                'dueDateTime': '0000v0000 +0 W',
                'assignTo': 'PARALEGAL'
            },
            {
                'title': "Receive disclosure information from client",
                'stepName': '0001v0000',
                'dueDateTime': '0000v0000 +10 W',
                'assignTo': 'PARALEGAL'
            },
            {
                'title': "Create disclosures document",
                'stepName': '0002v0000',
                'dueDateTime': '0001v0000 +3 W',
                'assignTo': 'PARALEGAL'
            },
            {
                'title': "First review",
                'stepName': '0003v0000',
                'dueDateTime': '0002v0000 +2 W',
                'assignTo': 'ATTORNEY'
            },
            {
                'title': "Revise disclosures",
                'stepName': '0004v0000',
                'dueDateTime': '0003v0000 +3 W',
                'assignTo': 'PARALEGAL'
            },
            {
                'title': "Final review and approval",
                'stepName': '0005v0000',
                'dueDateTime': '0000v0000 +30 C',
                'assignTo': 'ATTORNEY'
            },
            {
                'title': "Serve initial disclosures",
                'stepName': '0006v0000',
                'dueDateTime': '0000v0000 +30 C',
                'assignTo': 'PARALEGAL'
            }
        ]
    }
}


def _retrieve(plan_id) -> dict:
    return __PLANS.get(plan_id)
