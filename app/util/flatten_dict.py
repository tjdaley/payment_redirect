"""
flatten_dict.py - Flatten a multi-level dict
"""
import collections


def flatten_dict(d: dict, parent_key: str = '', sep: str = '_') -> dict:
    """
    Flatten a dict so that innter dicts are pulled up. For example:
    {
        'name': {'first_name': "TOM", 'last_name': "DALEY"},
        'telephone': "214-555-5555"
    }

    becomes:

    {
        'name_first_name': "TOM",
        'name_last_name': "DALEY",
        'telephone': "214-555-5555"
    }

    This is required for merging into Microsoft Word templates

    From: https://stackoverflow.com/questions/6027558/flatten-nested-dictionaries-compressing-keys

    Args:
        d (dict): dict to flatten
        parent_key (str): Prefex to add to keys. Used only for recursive calls.
        sep (str): separator between keys, default = "_"
    Returns:
        (dict): Flattened dict
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))

    new_dict = dict(items)

    # Some fix-ups to compensate for issues in the docx-mailmerge package
    name = ""
    if new_dict.get('name_title'):
        name += new_dict['name_title'] + " "
    if new_dict.get('name_first_name'):
        name += new_dict['name_first_name'] + " "
    if new_dict.get('name_middle_name'):
        name += new_dict['name_middle_name'] + " "
    if new_dict.get('name_last_name'):
        name += new_dict['name_last_name']
    if new_dict.get('name_suffix'):
        name += ", " + new_dict['name_suffix']
    new_dict['name_full_name'] = name

    return new_dict
