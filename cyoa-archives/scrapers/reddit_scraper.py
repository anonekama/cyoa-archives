"""Simple Reddit Scraper
Scrapes posts from subreddit using praw
"""
__author__ = "anonekama"
__version__ = 0.2


import argparse
import logging
import pathlib
import sys
import time

import pandas
import praw
import redditcleaner
import yaml


def scrape_subreddit(subreddit, username, password, clientid, clientsecret, useragent, limit=None, outfile=None):
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
	df['rid'] = r_id
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

	# Print or return results
	if outfile:
		df.to_csv(outfile, index=False)
	else:
		return df.to_json(orient='records')


if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description="Parse a subreddit for submissions using praw."
	)
	parser.add_argument("subreddit", help="Name of subreddit to parse (example: makeyourchoice)")
	parser.add_argument("-u", "--username", help="Reddit API account username")
	parser.add_argument("-p", "--password", help="Reddit API account password")
	parser.add_argument("-i", "--clientid", help="Reddit API account client id")
	parser.add_argument("-s", "--clientsecret", help="Reddit API account client secret")
	parser.add_argument("-a", "--useragent", help="User agent to display")
	parser.add_argument("-l", "--limit", help="Limit number of submissions to return", default=None)
	parser.add_argument("-c", "--config_file", help="Configuration file to use")
	parser.add_argument("-o", "--outfile", help="Output results to filename")
	parser.add_argument("-v", "--verbose", help="Be verbose", action="store_const", dest="loglevel", const=logging.INFO)
	parser.add_argument("--version", action="version", version=str(__version__))

	# Parse arguments
	args = parser.parse_args()
	logging.basicConfig(level=args.loglevel)
	username = args.username
	password = args.password
	clientid = args.clientid
	clientsecret = args.clientsecret
	useragent = args.useragent

	# Load arguments from configuration file if provided
	if args.config_file:
		filepath = pathlib.Path(args.config_file)
		try:
			with open(filepath) as f:
				config = yaml.safe_load(f).get('reddit_scraper')
				username = username if username else config.get('username')
				password = password if password else config.get('password')
				clientid = clientid if clientid else config.get('clientid')
				clientsecret = clientsecret if clientsecret else config.get('clientsecret')
				useragent = useragent if useragent else config.get('useragent')
		except OSError:
			print(f"Could not read file: {filepath}")
			sys.exit(1)

	# Raise error if required arguments are missing
	if not username:
		parser.error("username is required")
	if not password:
		parser.error("password is required")
	if not clientid:
		parser.error("clientid is required")
	if not clientsecret:
		parser.error("clientsecret is required")
	if not useragent:
		parser.error("useragent is required")

	# Pass to main function
	scrape_subreddit(
		args.subreddit,
		username,
		password,
		clientid,
		clientsecret,
		useragent,
		int(args.limit) if args.limit else None,
		args.outfile
	)
