from __future__ import annotations

"""Praw API wrapper
Provides class for interacting with Reddit Praw API
"""
__author__ = "anonekama"
__version__ = 0.5

import logging
import praw

from typing import List, Dict, Any

from .submission import RedditSubmission

logger = logging.getLogger(__name__)


class PrawAPIWrapper:

    def __init__(self, config_object: Dict[str, Any]):
        self.config = config_object
        self.reddit = praw.Reddit(
            username=self.config.get('username'),
            password=self.config.get('password'),
            client_id=self.config.get('client_id'),
            client_secret=self.config.get('client_secret'),
            user_agent=self.config.get('user_agent')
        )
        RedditSubmission.load_config(config_object)

    def scrape(self, subreddit_name: str, limit: int = None, col_names: List[str] = None) -> List[Dict]:
        logger.info(f'PRAW: Attempting to fetch submissions from [{subreddit_name}] (limit={limit})...')
        generator = self.reddit.subreddit(subreddit_name).new(limit=limit)
        results = []
        for submission in generator:
            keys = col_names if col_names else self.config.get('default_fields')
            d = {}
            for key in keys:
                value = getattr(submission, key, None)
                d[key] = value
            result = RedditSubmission(d)
            results.append(dict(result))
        logger.info(f'PRAW: Successfully fetched {len(results)} submissions from [{subreddit_name}].')
        return results
