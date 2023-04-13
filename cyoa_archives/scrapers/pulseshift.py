"""Pulseshift API wrapper

Provides a class for interacting with Reddit Pulseshift API.

Typical usage example:

  api = PulseshiftAPIWrapper('URL', 25, 0.3, 5)
  api_from_config = PulseshiftAPIWrapper(config.get('reddit_scraper')

"""

import logging
import pandas
import requests
import time
import pprint

from typing import Optional, TypeVar, List, Dict, Any

from .utils import object_to_df
from .submission import RedditSubmission

logger = logging.getLogger(__name__)
TPulseshiftAPIWrapper = TypeVar('TPulseshiftAPIWrapper', bound='PulseshiftAPIWrapper')


class PulseshiftAPIWrapper:
    """Wrapper of the Pulseshift API around the python requests library."""

    def __init__(self, config_object: Dict[str, Any]):
        """Initializes a PulseshiftAPIWrapper instance.

        :param config_object: A dictionary of configuration values
        """
        self.config = config_object
        RedditSubmission.load_config(config_object)

    def rest_get(self, subreddit_name: str, size: Optional[int] = None, before: Optional[int] = None,
                 after: Optional[int] = None) -> List[RedditSubmission]:
        """Get a single response from the Pulseshift API endpoint using the python requests library.

        The Pulseshift API currently limits requests to a maximum of 500 results.

        :param subreddit_name: Name of subreddit as a string (without r/ prefixed).
        :param size: Maximum number of results to fetch. If None, allow default behavior.
        :param before: Fetch  results before unix timestamp.
        :param after: Fetch results after unix timestamp.
        :return: A list of .
        """
        logger.info(f'PULSESHIFT: Attempting to fetch submissions '
                    f'from [{subreddit_name}] (limit={size}) ({before}-{after})...')

        # Assemble request parameters
        params = {
            'subreddit': subreddit_name,
        }
        if size or self.config.get('pulseshift_limit'):
            params['size'] = size if size else self.config.get('pulseshift_limit')
        if before:
            params['before'] = before
        if after:
            params['after'] = after

        # Make request
        r = requests.get(url=self.config.get('pulseshift_url'), params=params)
        data = r.json().get('data')
        l: List[RedditSubmission] = []
        for row in data:
            rs = RedditSubmission(row)
            l.append(rs)
        logger.info(f'PULSESHIFT: Successfully fetched {len(data)} submissions from [{subreddit_name}].')
        return l

    def scrape(self, subreddit_name: str, size: int = None, before: int = None, after: int = 0) -> List[
        RedditSubmission]:
        # Initalize values for while loop
        results = []
        num_errors = 0
        chunk_size = size if size else self.config.get('pulseshift_limit')
        last_timestamp = int(time.time())
        if before:
            last_timestamp = before

        # Loop until no more results or time boundaries exceeded
        while last_timestamp > after and num_errors < self.config.get('pulseshift_max_retry'):

            # Sleep for time to hitting rate limits
            time.sleep(self.config.get('pulseshift_sleep_interval'))

            # Make request
        # try:
            response = self.rest_get(subreddit_name=subreddit_name, size=size, before=last_timestamp, after=after)
            results = results + response
            if len(response) > 0:
                last_timestamp = response[-1].json.get('created_utc')
            elif len(response) < chunk_size:
                break
        # except Exception as e:
        #    logger.warning(f'PULSESHIFT: Failed to complete request at {last_timestamp} from [{subreddit_name}].')
        #    logger.warning(f'Exception: {e}')
            num_errors = num_errors + 1

        logger.info(f'PULSESHIFT: Fetched a total of {len(results)} submissions from [{subreddit_name}].')
        return results
