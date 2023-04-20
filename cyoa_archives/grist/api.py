"""Grist API wrapper
Provides class for interacting with Grist
"""

import logging
import pandas

from collections import OrderedDict
from typing import Optional, List, Dict, NamedTuple, Any
from grist_api import GristDocAPI

logger = logging.getLogger(__name__)


class GristAPIWrapper:

    def __init__(self, config_object: Dict):
        # Assert that configuration file is appropriately formatted


        self.server_url = config_object.get('server_url')
        self.document_id = config_object.get('document_id')
        self.api_key = config_object.get('api_key')
        self.api = GristDocAPI(self.document_id, server=self.server_url, api_key=self.api_key)

    def fetch_table(self, table_name: str, filters: Dict[str, Any] = None) -> List[NamedTuple]:
        logger.info(f'GRIST: Attempting to fetch from [{table_name}] at {self.document_id}...')
        records = self.api.fetch_table(table_name, filters=filters)
        logger.info(f'GRIST: Successfully fetched {len(records)} records from [{table_name}].')
        return records

    def fetch_table_pd(self, table_name: str, filters: Dict[str, Any] = None,
                       col_names: List[str] = None) -> pandas.DataFrame:
        results = self.fetch_table(table_name, filters=filters)
        if len(results) > 0:
            first_result = results[0]._asdict()
            table_keys = first_result.keys()

            # Subset keys from table keys
            if col_names:
                new_keys = []
                for key in table_keys:
                    if key in col_names:
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

    def add_records(self, table_name: str, record_dicts: List[Dict[str, Any]], chunk_size: int = None, mock: bool = True,
                    prompt: bool = True) -> Optional[List[int]]:
        if mock:
            logger.info(record_dicts)
        else:
            if prompt:
                logger.info(record_dicts)
                confirm_submit = input(f"API: Are you sure you wish to ADD these record(s) to [{table_name}]? ")
                if confirm_submit.lower() not in ["y", "yes"]:
                    return None
            logger.info(f'GRIST: Attempting to ADD new records to [{table_name}] at {self.document_id}...')
            response = self.api.add_records(table_name, record_dicts=record_dicts, chunk_size=chunk_size)
            logger.info(f'GRIST: Successfully added {len(response)} records to [{table_name}].')
            return response

    def update_records(self, table_name: str, record_dicts: List[Dict[str, Any]],
                       chunk_size: int = None, mock: bool = True, prompt: bool = True) -> None:
        if mock:
            logger.info(record_dicts)
        else:
            if prompt:
                logger.info(record_dicts)
                confirm_submit = input(f"API: Are you sure you wish to PATCH these record(s) in [{table_name}]? ")
                if confirm_submit.lower() not in ["y", "yes"]:
                    return None
            logger.info(f'GRIST: Attempting to PATCH records in [{table_name}] at {self.document_id}...')
            response = self.api.update_records(table_name, record_dicts=record_dicts, chunk_size=chunk_size)
            logger.info(f'GRIST: Successfully patched {len(record_dicts)} records at [{table_name}].')
            return response
