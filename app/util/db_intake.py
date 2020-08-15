"""
db_intakes.py - Class to access client intake entries from Cognito Forms

@author Thomas J. Daley, J.D.
@version 0.0.1
Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
from datetime import datetime
import json  # noqa
from pymongo import DESCENDING
from bson.objectid import ObjectId

from util.database import Database

COLLECTION_NAME = 'intakes'


class DbIntakes(Database):
    """
    Encapsulates a database accessor for intake entries
    """
    def get_one(self, entry_number: int) -> dict:
        """
        Return a notes record given entry_number.

        Args:
            entry_number (int): Entry Number assigned by Cognito Forms
        Returns:
            (dict): The located document or None
        """
        filter_ = {'entry_number': entry_number}
        document = self.dbconn[COLLECTION_NAME].find_one(filter_)
        return document

    def get_list(self, where: dict = None, page_num: int = 1, page_size: int = 25) -> list:
        """
        Retrieve a list of intake entries
        This method supports pagination.

        Args:
            where (dict): Filter
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=25)
        Returns:
            (list): List of documents from 'notes' or None
        """

        skips = page_size * (page_num - 1)

        order_by = [
            ('entry_number', DESCENDING)
        ]

        intakes = self.dbconn[COLLECTION_NAME].find(where).sort(order_by).skip(skips).limit(page_size)

        if not intakes:
            return None

        return list(intakes)

    def search(self, query: str, page_num: int = 1, page_size: int = 25) -> list:
        """
        Search for intakes matching the words in *query*.

        Args:
            query (str): Query string from user
            page_num (int): Which page number is going to be displayed? (default=1)
            page_size (int): Number of documents per page (default=25)
        Returns:
            (list): List of docs or None
        """
        search_fields = [
            'AboutYou.Name.FirstAndLast',
            'AboutYou.Address.FullInternationalAddress',
            'AboutYou.Email',
            'AboutYou.HomeTelephone',
            'AboutYou.CellPhone',
            'Op.Name.FirstAndLast',
            'Op.Address.FullInternationalAddress',
            'Op.Email',
            'Op.HomeTelephone',
            'Op.CellPhone',
        ]
        search_words = query.split()
        conditions = []
        for search_field in search_fields:
            for search_word in search_words:
                regex = f'.*{search_word}.*'
                conditions.append({search_field: {'$regex': regex, '$options': 'i'}})

        where = {'$or': conditions}

        return self.get_list(
            where=where,
            page_num=page_num,
            page_size=page_size
        )

    def save(self, doc: dict) -> dict:
        """
        Save a notes record
        """
        try:
            # Indexed by Entry number
            doc['entry_number'] = doc.get('Entry', {}).get('Number', 0)
            filter_ = {'entry_number': doc['entry_number']}

            # Remove '$'-prefixed fields
            doc['_$etag'] = doc.get('$etag', None)
            del doc['$etag']
            doc['_$version'] = doc.get('$version', None)
            del doc['$version']

            update_result = self.dbconn[COLLECTION_NAME].update_one(filter_, {'$set': doc}, upsert=True)
        except Exception as e:
            result = {'success': False, 'message': str(e)}
            return result

        return {'success': True, 'message': f"Matched: {update_result.matched_count}  Modified: {update_result.modified_count}  ID (if inserted): {update_result.upserted_id}"}
