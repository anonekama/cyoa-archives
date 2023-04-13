"""Representation of reddit submissions (posts)

Provides a class for representing and manipulating reddit posts/submissions.

Typical usage example:

  RedditSubmission.load_config(config.get('reddit_scraper')
  r = RedditSubmission({"JSON": "THIS IS JSON OBJECT"})

"""

import json
import logging
import re
import time

from typing import Optional, List, Dict, Any

import redditcleaner

logger = logging.getLogger(__name__)
YES = "Yes"
NO = "No"
NULL = ""


class RedditSubmission:
    """Represents a Reddit Submission.

    Contains methods to process a reddit submission for data. May also add attributes to json.

    """

    # Class variable storing configuration
    CONFIG = None

    def __init__(self, json_data: Dict[str, Any]):
        """Initializes an instance of RedditSubmission.

        :param json_data: JSON representation of a reddit submission returned by API.
        """
        # Load object with JSON
        self.json = json_data

        # Assert that config file is set
        if not self.CONFIG:
            raise ValueError(f'Configuration file for RedditSubmission class was not set.')

        # Assert that JSON contains essential required values
        if 'id' not in self.json:
            raise ValueError(f'Reddit submission lacks (id) attribute.')
        if 'created_utc' not in self.json:
            raise ValueError(f'Reddit submission lacks (created_utc) attribute.')
        if 'permalink' not in self.json:
            raise ValueError(f'Reddit submission lacks (permalink) attribute.')
        if 'url' not in self.json:
            raise ValueError(f'Reddit submission lacks (url) attribute.')
        if 'title' not in self.json:
            raise ValueError(f'Reddit submission lacks (title) attribute.')
        if 'is_self' not in self.json:
            raise ValueError(f'Reddit submission lacks (is_self) attribute.')
        if 'locked' not in self.json:
            raise ValueError(f'Reddit submission lacks (locked) attribute.')
        if 'num_comments' not in self.json:
            raise ValueError(f'Reddit submission lacks (num_comments) attribute.')
        if 'score' not in self.json:
            raise ValueError(f'Reddit submission lacks (score) attribute.')

        # Assert that JSON contains essential optional values
        if 'selftext' not in self.json:
            raise ValueError(f'Reddit submission lacks (selftext) attribute.')
        if 'link_flair_text' not in self.json:
            raise ValueError(f'Reddit submission lacks (link_flair_text) attribute.')
        if 'removed_by_category' not in self.json:
            raise ValueError(f'Reddit submission lacks (removed_by_category) attribute.')

        # Perform any processing
        self.json['urls'] = self.extract_urls()
        self.json['urls'] = self.parse_urls()
        self.json['static_url'] = self.get_first_url('static')
        self.json['interactive_url'] = self.get_first_url('interactive')
        self.json['is_cyoa'] = self.parse_is_cyoa()
        self.json['selftext'] = self.clean_text('selftext')
        self.json['permalink'] = self.CONFIG.get('reddit_url') + self.json['permalink']
        self.json['parser_timestamp'] = int(time.time())

    @classmethod
    def load_config(cls, config_object: Dict[str, Any]) -> None:
        cls.CONFIG = config_object

    def clean_text(self, attribute: str) -> str:
        if attribute not in self.json:
            raise ValueError(f'Reddit submission lacks ({attribute}) attribute.')
        text: str = self.json.get(attribute)
        text = redditcleaner.clean(text, link=False)
        text = text.replace('\n', ' ').replace('\r', '').replace('\t', ' ').replace('\\', '')
        text = " ".join(text.split())
        return text

    def extract_urls(self) -> List[str]:
        # Append url text to selftext
        text = self.json.get('selftext') + ' ' + self.json.get('url')

        # Next, extract urls using regex
        text = text.replace('\\', '')
        pattern = re.compile(
            r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))""")
        urls = re.findall(pattern, str(text))

        # Next append the url field and remove duplicate urls
        urls = list(set(urls))

        return urls

    def parse_urls(self) -> List[str]:
        # First, define all bad url substrings
        bad_url_substrings = [self.json.get('permalink')]
        if self.CONFIG:
            bad_url_substrings = bad_url_substrings + self.CONFIG.get('bad_urls')

        # Next, remove urls that contain bad substrings
        good_urls = []
        if self.json.get('urls'):
            for url in self.json.get('urls'):
                is_good = True
                for substring in bad_url_substrings:
                    if substring in url:
                        is_good = False
                        break
                if is_good:
                    good_urls.append(url)

        return good_urls

    def get_first_url(self, cyoa_type) -> Optional[str]:
        if self.CONFIG:
            urls = self.json.get('urls')
            static_url_substrings = self.CONFIG.get('good_urls').get(cyoa_type)
            image_urls = []
            gallery_urls = []
            for url in urls:
                for substring in static_url_substrings:
                    if substring in url:
                        is_gallery = True
                        for extension in ['.jpg', '.jpeg', '.png']:
                            if extension in url:
                                is_gallery = False
                                image_urls.append(url)
                                break
                        if is_gallery:
                            gallery_urls.append(url)
            if len(gallery_urls) > 0:
                return gallery_urls[0]
            elif len(image_urls) == 1:
                return image_urls[0]
        return None

    def parse_is_cyoa(self, remove_low_score: bool = True) -> str:
        # Check if post is removed
        if self.json.get('removed_by_category') or self.json.get('locked'):
            return NO

        if self.CONFIG:
            # Check if selftext contains bad substrings
            bad_selftext_substrings = self.CONFIG.get('bad_selftext')
            for substring in bad_selftext_substrings:
                if substring in self.json.get('selftext'):
                    return NO

            # Check if title is bad
            bad_title_substrings = self.CONFIG.get('bad_title')
            for substring in bad_title_substrings:
                if substring in self.json.get('title'):
                    return NO

            # Exclude text only posts
            if self.CONFIG.get('remove_text_only'):
                urls = self.json.get('urls')
                if self.json.get('is_self') and len(urls) == 0:
                    return NO

            # Exclude posts with comments and a score below threshold
            if remove_low_score:
                num_comments = int(self.json.get('num_comments'))
                score = int(self.json.get('score'))
                comment_threshold = self.CONFIG.get('low_karma_threshold').get('comments')
                score_threshold = self.CONFIG.get('low_karma_threshold').get('score')
                if num_comments <= comment_threshold and score <= score_threshold:
                    return NO

            post_flair = self.json.get('link_flair_text')
            if post_flair:
                # Check if flair is bad
                bad_flair_substrings = self.CONFIG.get('bad_flair')
                for substring in bad_flair_substrings:
                    if substring in self.json.get('link_flair_text'):
                        return NO

                # Check if flair is good
                good_flair_substrings = self.CONFIG.get('good_flair')
                for substring in good_flair_substrings:
                    if substring in self.json.get('title'):
                        return YES

        return NULL

    def __repr__(self):
        return json.dumps(self.json)
