"""
template_manager.py - Manage email templates.

Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import os
import re
import boto3

from dotenv import load_dotenv
load_dotenv()

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')


def _ses_client():
    """
    Instantiate boto3 client for SES service.
    """
    return boto3.client(
        'ses',
        region_name=AWS_REGION,
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )


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
        client = _ses_client()
        response = client.list_templates(MaxItems=10)
        return response['TemplatesMetadata']

    @staticmethod
    def get_template(email_address: str, template_name: str, raw: bool = False) -> dict:
        """
        Retrieve a template by name.

        Args:
            email_address (str): Email address of person wanting to retrieve the template.
            template_name (str): Template name to retrieve
            raw (bool): If True, return exactly what we retrieved, otherwise, trim it down.
        """
        client = _ses_client()
        response = client.get_template(TemplateName=template_name)
        if raw:
            return response
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
        client = _ses_client()
        try:
            my_template = {key: value for key, value in template.items()}
            my_template['TemplateName'] = re.sub(r'[^A-Za-z0-9\_\-]', '', template['TemplateName'])
            template_name = my_template['TemplateName']
            # pylint: disable=unused-variable
            response = client.get_template(TemplateName=template_name)
            # pylint: enable=unused-variable
        except client.exceptions.TemplateDoesNotExistException:
            response = client.create_template(Template=my_template)
            return {'success': True, 'message': "OK"}

        response = client.update_template(Template=my_template)  # noqa
        return {'success': True, 'message': "OK"}

    @staticmethod
    def delete_template(email_address: str, template_name: str) -> bool:
        """
        Delete a template.
        Args:
            email_address (str): Email address of person wanting to retrieve the template.
            template_name (str): Template name to delete
        """
        client = _ses_client()
        # pylint: disable=unused-variable
        response = client.delete_template(TemplateName=template_name)  # noqa
        # pylint: enable=unused-variable
        return {'success': True, 'message': "OK"}
