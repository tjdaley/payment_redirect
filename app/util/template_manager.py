"""
template_manager.py - Manage email templates.

Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import json  # for debugging
import re
import boto3
from botocore.exceptions import ClientError


AWS_REGION = "us-east-1"


class TemplateManager(object):
    """
    Class to manage email templates.
    """
    @staticmethod
    def get_templates(email_address: str) -> list:
        """
        Retrieve a list of email templates for this email
        address.

        Args:
            email_address (str): Email address of person wanting to retrieve templates.
        """
        client = boto3.client('ses', region_name=AWS_REGION, )
        response = client.list_templates(MaxItems=10)
        return response['TemplatesMetadata']

    @staticmethod
    def get_template(email_address: str, template_name: str) -> dict:
        """
        Retrieve a template by name.

        Args:
            email_address (str): Email address of person wanting to retrieve the template.
            template_name (str): Template name to retrieve
        """
        client = boto3.client('ses', region_name=AWS_REGION, )
        response = client.get_template(TemplateName=template_name)
        return response['Template']

    @staticmethod
    def save_template(email_address: str, template: dict) -> bool:
        """
        Save a template either by creating a new one or updating an
        existing template.

        Args:
            email_address (str): Email address of person wanting to save the template.
            template (dict): Description of template:
                {
                    'TemplateName': 'string',
                    'SubjectPart': 'string',
                    'TextPart': 'string',
                    'HtmlPart': 'string'
                }
        """
        client = boto3.client('ses', region_name=AWS_REGION, )
        try:
            my_template = {key: value for key, value in template.items()}
            my_template['TemplateName'] = re.sub(r'[^A-Za-z0-9\_\-]', '', template['TemplateName'])
            template_name = my_template['TemplateName']
            response = client.get_template(TemplateName=template_name)
        except client.exceptions.TemplateDoesNotExistException:
            response = client.create_template(Template=my_template)
            return {'success': True, 'message': "OK"}

        response = client.update_template(Template=my_template)
        return {'success': True, 'message': "OK"}

    @staticmethod
    def delete_template(email_address: str, template_name: str) -> bool:
        """
        Delete a template.
        Args:
            email_address (str): Email address of person wanting to retrieve the template.
            template_name (str): Template name to delete
        """
        client = boto3.client('ses', region_name=AWS_REGION, )
        response = client.delete_template(TemplateName=template_name)
        return {'success': True, 'message': "OK"}
