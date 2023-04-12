from __future__ import annotations

"""Pulseshift API wrapper
Provides class for interacting with Reddit Pulseshift API
"""
__author__ = "anonekama"
__version__ = 0.2

import logging
import pandas
import praw
import requests
import time
import pprint

from typing import Type, List, Dict

from .scraper_utils import object_to_df

logger = logging.getLogger(__name__)

class PulseshiftAPIWrapper:

	def __init__(self, pulseshift_url: str, pulseshift_limit: int=None, pulseshift_sleep_interval: int = 0, pulseshift_max_retry: int = 1, default_fields: List[str] = None):
		self.pulseshift_url = pulseshift_url
		self.pulseshift_limit = pulseshift_limit
		self.pulseshift_sleep_interval = pulseshift_sleep_interval
		self.pulseshift_max_retry = pulseshift_max_retry
		self.default_fields = default_fields

	@classmethod
	def load_config(cls, config_object: Dict[str, Any]) -> PulseshiftAPIWrapper:
		return PulseshiftAPIWrapper(
			pulseshift_url = config_object.get("pulseshift_url"),
			pulseshift_limit = config_object.get("pulseshift_limit"),
			pulseshift_sleep_interval = config_object.get("pulseshift_sleep_interval"),
			pulseshift_max_retry = config_object.get("pulseshift_max_retry"),
			default_fields = config_object.get("default_fields")
		)

	def rest_get(self, subreddit_name: str, size: int = None, before: int = None, after: int = None) -> List[Dict[str, Any]]:
		logger.info(f'PULSESHIFT: Attempting to fetch submissions from [{subreddit_name}] (limit={size}) ({before}-{after})...')

		# Assemble request parameters
		params = {
			'subreddit': subreddit_name,
		}
		if size or self.pulseshift_limit:
			params['size'] = size if size else self.pulseshift_limit
		if before:
			params['before'] = before
		if after:
			params['after'] = after

		# Make request
		r = requests.get(url = self.pulseshift_url, params = params)
		data = r.json().get('data')
		logger.info(f'PULSESHIFT: Successfully fetched {len(data)} submissions from [{subreddit_name}].')
		return data

	def rest_get_df(self, subreddit_name: str, size: int = None, before: int = None, after: int = None, colnames: List[str] = None) -> pandas.DataFrame:
		results = self.rest_get(subreddit_name=subreddit_name, size=size, before=before, after=after)
		colnames = colnames if colnames else self.default_fields
		return object_to_df(results, colnames)

	def scrape_loop(self, subreddit_name: str, size: int = None, before: int = None, after: int = 0) -> List[Dict[str, Any]]:
		# Initalize values for while loop
		results = []
		num_results = 1
		num_errors = 0
		chunk_size = size if size else self.pulseshift_limit
		last_timestamp = int(time.time())
		if before:
			last_timestamp = before

		# Loop until no more results or time boundaries exceeded
		while last_timestamp > after and num_errors < self.pulseshift_max_retry:

			# Sleep for time to hitting rate limits
			time.sleep(self.pulseshift_sleep_interval)

			# Make request
			try:
				response = self.rest_get(subreddit_name=subreddit_name, size=size, before=last_timestamp, after=after)
				results = results + response
				if len(response) > 0:
					last_timestamp = response[-1].get('created_utc')
				elif len(response) < chunk_size:
					break
			except:
				logger.warning(f'PULSESHIFT: Failed to complete request at {last_timestamp} from [{subreddit_name}].')
				num_errors = num_errors + 1
		return results

	def scrape_loop_df(self, subreddit_name: str, size: int = None, before: int = None, after: int = 0, colnames: List[str] = None) -> pandas.DataFrame:
		results = self.scrape_loop(subreddit_name=subreddit_name, size=size, before=before, after=after)
		colnames = colnames if colnames else self.default_fields
		return object_to_df(results, colnames)
