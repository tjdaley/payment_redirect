"""
template_name.py - Get template name in a standard way.
"""
import os


def template_name(template_type: str, user_email: str):
    """
    Return the template file name requested.

    Args:
        template_type (str): 'letterhead', etc.
        user_email (str): Email of the user we are getting a template for.

    Returns:
        (str): Filename of template file.
    """
    filename = os.path.join(os.environ.get('DOCX_PATH'), f'{user_email}-{template_type}.docx')

    if not os.path.exists(filename):
        filename = os.path.join(os.environ.get('DOCX_PATH'), f'default-{template_type}.docx')
    if not os.path.exists(filename):
        return None
    return filename
