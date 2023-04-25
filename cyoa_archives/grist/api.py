"""Grist API wrapper

Provides a class for interacting with the Grist API.

"""

import logging
from collections import OrderedDict
from typing import Optional, List, Dict, NamedTuple, Any

import pandas
from grist_api import GristDocAPI

logger = logging.getLogger(__name__)


class GristAPIWrapper:

    def __init__(self, server_url: str, document_id: str, api_key: str):
        """Constructs a GristAPIWrapper.

        :param server_url: Server URL to use as an endpoint.
        :param document_id: Document ID to use as an endpoint.
        :param api_key: Grist user API key.
        """
        self.server_url = server_url
        self.document_id = document_id
        self.api_key = api_key
        self.api = GristDocAPI(self.document_id, server=self.server_url, api_key=self.api_key)

    @classmethod
    def from_config(cls, config_object: Dict):
        """Constructs a GristAPIWrapper given a configuration object.

        :param config_object: Configuration settings for grist.
        :return:
        """
        # TODO: Assert that configuration file is appropriately formatted
        server_url = config_object.get('server_url')
        document_id = config_object.get('document_id')
        api_key = config_object.get('api_key')
        return cls(
            server_url=server_url,
            document_id=document_id,
            api_key=api_key
        )

    def fetch_table(self, table_name: str, filters: Dict[str, Any] = None) -> List[NamedTuple]:
        """Wrapper around the Grist API fetch_table method.

        :param table_name: Table name to fetch records from.
        :param filters: Filters to provide to Grist API.
        :return: A list of records (NamedTuple) where the keys are the column names.
        """
        logger.info(f'GRIST: Attempting to fetch from [{table_name}] at {self.document_id}...')
        records = self.api.fetch_table(table_name, filters=filters)
        logger.info(f'GRIST: Successfully fetched {len(records)} records from [{table_name}].')
        return records

    def fetch_table_pd(self,
                       table_name: str,
                       filters: Dict[str, Any] = None,
                       col_names: List[str] = None
                       ) -> Optional[pandas.DataFrame]:
        """Fetch a table from grist and return the results as a dataframe.

        :param table_name: Table name to fetch records from.
        :param filters: Filters to provide to Grist API.
        :param col_names: Column names to select in the final dataframe.
        :return: A pandas dataframe of the results or None if there are no results.
        """
        results = self.fetch_table(table_name, filters=filters)
        if len(results):
            # First we get the existing column names provided by grist
            first_result = results[0]._asdict()
            table_keys = first_result.keys()

            # If the user selected particular columns, subset them from the existing columns
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

    def add_records(self,
                    table_name: str,
                    record_dicts: List[Dict[str, Any]],
                    chunk_size: Optional[int] = None,
                    mock: bool = True,
                    prompt: bool = True
                    ) -> Optional[List[int]]:
        """Add new records to Grist.

        Note that this method assumes that the records do not already exist, and it may fail depending on table
        -specific rules (e.g. no duplicates) on the server.

        :param table_name: Table name to insert.
        :param record_dicts: A list of objects to insert, where the keys are column names.
        :param chunk_size: Passing chunk_size argument to Grist API.
        :param mock: Does not actually perform the update if set to True.
        :param prompt: Prompts the user for confirmation if set to True.
        :return: A list of Grist ids of successfully inserted records.
        """
        if mock:
            # Print the records
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

    def update_records(self,
                       table_name: str,
                       record_dicts: List[Dict[str, Any]],
                       chunk_size: int = None,
                       mock: bool = True,
                       prompt: bool = True
                       ) -> None:
        """Update records in Grist based on their id.

        :param table_name: Table name to patch.
        :param record_dicts: A list of objects to patch; note that 'id' is a mandatory key.
        :param chunk_size: Passing chunk_size argument to Grist API.
        :param mock: Does not actually perform the update if set to True.
        :param prompt: Prompts the user for confirmation if set to True.
        """
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
