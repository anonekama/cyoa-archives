from __future__ import annotations

"""Grist API wrapper
Provides class for interacting with Grist
"""
__author__ = "anonekama"
__version__ = 0.1

import logging
import pandas

from collections import OrderedDict
from typing import Type, List, Dict, NamedTuple
from grist_api import GristDocAPI

logger = logging.getLogger(__name__)

class GristAPIWrapper:

    def __init__(self, server_url: str, document_id: str, api_key: str):
        self.server_url = server_url
        self.document_id = document_id
        self.api_key = api_key
        self.api = GristDocAPI(self.document_id, server=self.server_url, api_key=self.api_key)

    @classmethod
    def load_config(cls, config_object: Dict[str, Any]) -> GristAPIWrapper:
        return GristAPIWrapper(
            server_url = config_object.get('server_url'),
            document_id = config_object.get('document_id'),
            api_key = config_object.get('api_key')
        )

    def fetch_table(self, tablename: str, filters: Dict[str, Any] = None) -> List[NamedTuple]:
        logger.info(f'GRIST: Attempting to fetch from [{tablename}] at {self.document_id}...')
        records = self.api.fetch_table(tablename, filters=filters)
        logger.info(f'GRIST: Successfully fetched {len(records)} records from [{tablename}].')
        return records

    def fetch_table_pd(self, tablename: str, filters: Dict[str, Any] = None, colnames: List[str] = None) -> pandas.DataFrame:
        results = self.fetch_table(tablename, filters=filters)
        if len(results) > 0:
            first_result = results[0]._asdict()
            table_keys = first_result.keys()

            # Subset keys from table keys
            if colnames:
                new_keys = []
                for key in table_keys:
                    if key in colnames:
                        new_keys.append(key)
                table_keys = new_keys

            # Initialize temporary lists
            d = OrderedDict()
            for key in table_keys:
                d[key] = []

            # Iterate through results
            for result in results:
                row = result._asdict()
                for key in table_keys:
                    d[key].append(row.get(key))

            # Convert to pandas dataframe
            return pandas.DataFrame(d)
        return None

    def add_records(self, tablename: str, record_dicts: List[Dict[str, Any]], chunk_size: int = None, mock: bool = True, prompt: bool = True) -> List[int]:
        if mock:
            logger.info(record_dicts)
        else:
            if prompt:
                logger.info(record_dicts)
                confirm_submit = input(f"API: Are you sure you wish to ADD these record(s) to [{tablename}]? ")
                if confirm_submit.lower() not in ["y", "yes"]:
                    return None
            logger.info(f'GRIST: Attempting to ADD new records to [{tablename}] at {self.document_id}...')
            response = self.api.add_records(tablename, record_dicts=record_dicts, chunk_size=chunk_size)
            logger.info(f'GRIST: Successfully added {len(response)} records to [{tablename}].')
            return response

    def update_records(self, tablename: str, record_dicts: List[Dict[str, Any]], group_if_needed: bool = False, chunk_size: int = None, mock: bool = True, prompt: bool = True) -> None:
        if mock:
            logger.info(record_dicts)
        else:
            if prompt:
                logger.info(record_dicts)
                confirm_submit = input(f"API: Are you sure you wish to PATCH these record(s) in [{tablename}]? ")
                if confirm_submit.lower() not in ["y", "yes"]:
                    return None
            logger.info(f'GRIST: Attempting to PATCH records in [{tablename}] at {self.document_id}...')
            response = self.api.update_records(tablename, record_dicts=record_dicts, chunk_size=chunk_size)
            logger.info(f'GRIST: Successfully patched {len(record_dicts)} records at [{tablename}].')
            return response
