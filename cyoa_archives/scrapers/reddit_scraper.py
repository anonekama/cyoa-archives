"""Simple Reddit Scraper
Scrapes posts from subreddit using praw
"""
__author__ = "anonekama"
__version__ = 0.3

import datetime
import logging
import time

import pandas
import praw
import redditcleaner

from .reddit_scraper_utils import extract_urls, get_single_url, is_CYOA, url_list_to_str


def scrape_subreddit(subreddit: str, username: str, password: str, clientid: str, clientsecret: str, useragent: str, limit: int = None, outfile: str = None):
	# Create an instance of reddit class
	log = logging.getLogger(__name__)
	reddit = praw.Reddit(username = username,
			             password = password,
			             client_id = clientid,
			             client_secret = clientsecret,
			             user_agent = useragent
	)

	# Fetch submissions (default: fetch as many submissions as possible)
	r_id = []
	author = []
	created_utc = []
	title = []
	selftext = []
	url = []
	permalink = []
	is_self = []
	over_18 = []
	removed_by_category = []
	link_flair_text = []
	num_comments = []
	score = []
	upvote_ratio = []
	log.info(f"Making query to `{subreddit}` with limit={limit}")
	for submission in reddit.subreddit(subreddit).new(limit=limit):
		text = submission.selftext
		if text is not None:
			text = redditcleaner.clean(text).replace('\n', ' ').replace('\r', '').replace('\t', ' ').replace('"', "'")
		r_id.append(submission.id)
		author.append(submission.author)
		created_utc.append(submission.created_utc)
		title.append(submission.title)
		selftext.append(text)
		url.append(submission.url)
		permalink.append(submission.permalink)
		is_self.append(submission.is_self)
		over_18.append(submission.over_18)
		removed_by_category.append(submission.removed_by_category)
		link_flair_text.append(submission.link_flair_text)
		num_comments.append(submission.num_comments)
		score.append(submission.score)
		upvote_ratio.append(submission.upvote_ratio)

    # Generate results
	df = pandas.DataFrame()
	df['r_id'] = r_id
	df['posted_by'] = author
	df['created_utc'] = created_utc
	df['title'] = title
	df['selftext'] = selftext
	df['url'] = url
	df['permalink'] = permalink
	df['is_self'] = is_self
	df['over_18'] = over_18
	df['removed_by_category'] = removed_by_category
	df['link_flair_text'] = link_flair_text
	df['num_comments'] = num_comments
	df['score'] = score
	df['upvote_ratio'] = upvote_ratio
	df['subreddit'] = subreddit
	df['parser_timestamp'] = int(time.time())

	# Process dataframe
	df.fillna('', inplace=True)
	urls = df.apply(extract_urls, axis=1)
	df['imgur_url'] = urls.apply(get_single_url, regex="imgur.")
	df['imgchest_url'] = urls.apply(get_single_url, regex="imgchest.")
	df['ireddit_url'] = urls.apply(get_single_url, regex="i.redd.it")
	df['neocities_url'] = urls.apply(get_single_url, regex="neocities")
	df['urls'] = urls.apply(url_list_to_str)
	df['is_cyoa'] = df.apply(is_CYOA, axis=1)
	df['permalink'] = "https://www.reddit.com" + df['permalink']
	df['date_posted'] = df['created_utc'].apply(datetime.datetime.fromtimestamp)
	df['date_scraped'] = df['parser_timestamp'].apply(datetime.datetime.fromtimestamp)

	df = df.sort_values(by = 'created_utc', ascending=True)

	# Print or return results
	if outfile:
		df.to_csv(outfile, index=False)
	return df
