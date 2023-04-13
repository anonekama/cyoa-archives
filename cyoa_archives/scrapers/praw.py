from __future__ import annotations

"""Praw API wrapper
Provides class for interacting with Reddit Praw API
"""
__author__ = "anonekama"
__version__ = 0.4

import logging
import pandas
import praw

from collections import OrderedDict
from typing import Type, List, Dict

from .utils import clean_reddit_text

logger = logging.getLogger(__name__)

class PrawAPIWrapper:

	def __init__(self, username: str, password: str, client_id: str, client_secret: str, user_agent: str, default_fields: List[str] = None):
		self.username = username
		self.password = password
		self.client_id = client_id
		self.client_secret = client_secret
		self.user_agent = user_agent
		self.default_fields = default_fields
		self.reddit = praw.Reddit(
			username = self.username,
			password = self.password,
			client_id = self.client_id,
			client_secret = self.client_secret,
			user_agent = self.user_agent
		)

	@classmethod
	def load_config(cls, config_object: Dict[str, Any]) -> PrawAPIWrapper:
		return PrawAPIWrapper(
			username = config_object.get('username'),
			password = config_object.get('password'),
			client_id = config_object.get('client_id'),
			client_secret = config_object.get('client_secret'),
			user_agent = config_object.get('user_agent'),
			default_fields = config_object.get('default_fields')
	)

	def scrape(self, subreddit_name: str, limit: int = None, colnames: List[str] = None) -> List[Dict[str, Any]]:
		logger.info(f'PRAW: Attempting to fetch submissions from [{subreddit_name}] (limit={limit})...')
		generator = self.reddit.subreddit(subreddit_name).new(limit=limit)
		results = []
		for submission in generator:
			keys = colnames if colnames else self.default_fields
			result = {}
			for key in keys:
				value = getattr(submission, key, None)
				result[key] = clean_reddit_text(value) ######### REMOVE CLEAN
			results.append(result)
		logger.info(f'PRAW: Successfully fetched {len(results)} submissions from [{subreddit_name}].')
		return results

	def scrape_pd(self, subreddit_name: str, limit: int = None, colnames: List[str] = None) -> pandas.DataFrame:
		logger.info(f'PRAW: Attempting to fetch submissions from [{subreddit_name}] (limit={limit})...')
		generator = self.reddit.subreddit(subreddit_name).new(limit=limit)

		####### NEED TO REFACTOR

		# Initialize temporary lists
		keys = colnames if colnames else self.default_fields
		result = OrderedDict()
		for key in keys:
			result[key] = []

		# Iterate through results
		for submission in generator:
			for key in keys:
				value = getattr(submission, key, None)
				result[key].append(clean_reddit_text(value))

		# Convert to pandas dataframe
		pd = pandas.DataFrame(result)
		logger.info(f'PRAW: Successfully fetched {len(pd.index)} submissions from [{subreddit_name}].')
		return pd
