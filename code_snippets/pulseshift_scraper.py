import argparse
import datetime
import json
import requests
import time

import pandas

# Configuration
ENDPOINT = "https://api.pushshift.io/reddit/search/submission/"

def main(args):
	# Process arguments
	subreddit_name = args.subreddit
	timestamp_before = args.timestamp_before

	# Prepare data receiver
	s_id = []
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

	# Loop while results is greater than zero
	numResults = 1
	while numResults > 0:

		# Formulate request
		PARAMS = {
			'subreddit': subreddit_name,
			'before': timestamp_before
		}

		# Make request
		time.sleep(0.3)
		print("Making request at timestamp: " + str(timestamp_before) + " " + str(datetime.datetime.fromtimestamp(timestamp_before)))
		try:
			r = requests.get(url = ENDPOINT, params = PARAMS)
			data = r.json()
			numResults = len(data['data'])

			for submission in data['data']:
				text = submission.get('selftext')
				if text is not None:
					text = text.replace('\n', ' ').replace('\r', '').replace('\t', ' ').replace(',', ';').replace('"', '*').replace("'", '*').replace('\\', '|')
					text = ' '.join(text.splitlines())
				s_id.append(submission.get('id'))
				author.append(submission.get('author'))
				created_utc.append(submission.get('created_utc'))
				title.append(submission.get('title'))
				selftext.append(text)
				url.append(submission.get('url'))
				permalink.append(submission.get('permalink'))
				is_self.append(submission.get('is_self'))
				over_18.append(submission.get('over_18'))
				removed_by_category.append(submission.get('removed_by_category'))
				link_flair_text.append(submission.get('link_flair_text'))
				num_comments.append(submission.get('num_comments'))
				score.append(submission.get('score'))
				upvote_ratio.append(submission.get('upvote_ratio'))
				if submission.get('created_utc') < timestamp_before:
					timestamp_before = submission.get('created_utc')
				if submission.get('created_utc') is None:
					# Break loop
					numResults = 0

		except:
			print("Failed to complete request...")
			continue

    # Print results
	df = pandas.DataFrame()
	df['id'] = s_id
	df['author'] = author
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
	df['subreddit'] = subreddit_name
	df['parser_timestamp'] = int(time.time())
	df.to_csv(subreddit_name + "_puleshift_" + str(int(time.time())) + ".csv", lineterminator='\r\n')


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("subreddit")
	parser.add_argument("-t", "--timestamp_before", default=int(time.time()))
	args = parser.parse_args()
	main(args)
