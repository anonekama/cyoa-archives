import argparse
import json
import pathlib
import sys
import yaml
import re
import logging

import pandas as pd

from cyoa_archives.grist.api import GristAPIWrapper

logger = logging.getLogger(__name__)

# Parse args
parser = argparse.ArgumentParser(
    description="Parse a subreddit for submissions using praw."
)
parser.add_argument("-c", "--config_file", help="Configuration file to use")
args = parser.parse_args()
if args.config_file:
    filepath = pathlib.Path(args.config_file)
    try:
        with open(filepath) as f:
            config = yaml.safe_load(f)
    except OSError:
        print(f"Could not read file: {filepath}")
        sys.exit(1)


# Set up API
api = GristAPIWrapper(config.get('grist'))

grist_pd = api.fetch_table_pd('Records', col_names=['id', 'selftext', 'DeepL', 'cyoa', 'is_self'])
cyoa_pd = grist_pd[grist_pd['cyoa'] > 0]
selftext_pd = cyoa_pd[cyoa_pd['is_self']]
print(selftext_pd)


result_list = []
for index, row in selftext_pd.iterrows():
    g_id = row['id']
    selftext = row['selftext']
    deepl = row['DeepL']

    if deepl:
        continue

    # Extract urls
    text = selftext.replace('\\', '')

    pattern = re.compile(
       r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))""")

    urls = re.findall(pattern, str(text))

    # Next append the url field and remove duplicate urls
    seen_urls = {}
    unique_url_list = []
    for url in urls:
        if url not in seen_urls:
            seen_urls[url] = True
            unique_url_list.append(url)

    # Remove bad urls
    bad_url_substrings = config.get('reddit_scraper').get('bad_urls')

    # Next, remove urls that contain bad substrings
    good_urls = []
    if unique_url_list:
        for url in unique_url_list:
            is_good = True
            for substring in bad_url_substrings:
                if substring in url:
                    is_good = False
                    break
            if is_good:
                good_urls.append(url)

    # Now get first static url
    static_substrings = config.get('reddit_scraper').get('good_urls').get('static')
    static_urls = []
    for url in good_urls:
        for substring in static_substrings:
            if substring in url:
                static_urls.append(url)
                break
    static_url = static_urls[0] if static_urls else None

    # Now get first interactive url
    int_substrings = config.get('reddit_scraper').get('good_urls').get('interactive')
    int_urls = []
    for url in good_urls:
        for substring in int_substrings:
            if substring in url:
                int_urls.append(url)
                break
    static_url = static_urls[0] if static_urls else None
    int_url = int_urls[0] if int_urls else None

    result_list.append({
        'id': g_id,
        'urls': ', '.join(good_urls),
        'static_url': static_url,
        'interactive_url': int_url
    })
# print(result_list[0:1])

# Update grist
api.update_records('Records', result_list, mock=False, prompt=False)
