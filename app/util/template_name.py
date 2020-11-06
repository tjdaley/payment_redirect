"""
template_name.py - Get template name in a standard way.
"""
from util.file_cache_manager import FileCacheManager


def template_name(template_type: str, user_email: str):
    """
    Return the template file name requested.

    Args:
        template_type (str): 'letterhead', etc.
        user_email (str): Email of the user we are getting a template for.

    Returns:
        (str): Filename of template file.
    """
    filename = f'{user_email}-{template_type}.docx'
    cache_manager = FileCacheManager()
    file_path = cache_manager.get_filename(filename)
    if not file_path:
        filename = f'default-{template_type}.docx'
        file_path = cache_manager.get_filename(filename)
    return file_path
