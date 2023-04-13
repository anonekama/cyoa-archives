import argparse
import datetime
import math
import re
import time
import html
import sys

from collections import OrderedDict

import pandas
import redditcleaner

MULTIPLE_URLS = "MULTIPLE_URLS"
GOOD_FLAIR = [
    "New",
    "OC",
    "Interactive",
    "Repost",
    "WIP",
    "Update"
]
BAD_FLAIR = [
    "Meta",
    "Discussion",
    "Search",
    "Announcement"
]

def clean_reddit_text(text, stripws=True):
    if isinstance(text, str):
        text = redditcleaner.clean(text, link=False)
        if stripws:
            text = text.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
            text = " ".join(text.split())
    return text

def extract_urls(text):
    text = text.replace('\\', '')
    pattern = re.compile(r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))""")
    urls = re.findall(pattern, str(text))
    return urls

def remove_url_substr_from_urls(urls, substr_list):
    results = []
    for url in urls:
        is_good = True
        for substr in substr_list:
            if substr in url:
                is_good = False
        if is_good:
            results.append(url)
    return results

def extract_urls(record, config=None):
    pass

def extract_urls_from_df(df, config=None):
    # Get all urls from self-post
    df['urls'] = df['selftext'].apply(extract_urls)
    df['urls'] = df['urls'] + df['url'].apply(lambda x: [x])

    # Remove duplicate urls
    df['urls'] = df['urls'].apply(lambda x: list(set(x)))

    # Remove self_url
    df = df.apply(lambda r: remove_url_substr_from_urls(r.urls, [r.permalink]), axis=1)

    # Remove bad_urls
    if config is not None:
        df['urls']  = df['urls'].apply(remove_url_substr_from_urls, substr_list=config.get('bad_urls'))

    ######### STILL WORKING ON THIS

    return keep_urls['urls']

def get_single_url(url_list, regex):
    galleries = []
    direct_images = []
    for url in url_list:
        if regex in url:
            if ".jpg" or ".jpeg" or ".png" or ".webp" or ".gif" or ".svg" in url:
                direct_images.append(url)
            else:
                galleries.append(url)
    if len(galleries) > 0:
        return galleries[0]
    elif len(direct_images) > 1:
        return None
    elif len(direct_images) > 0:
        return direct_images[0]
    else:
        return None

def has_text(text, substr_list):
    for substr in substr_list:
        if substr in text:
            return True
    return False

def extract_is_CYOA(df, config):
    # Check if post is removed
    is_removed = ~df['removed_by_category'].isnull()
    is_bad_selftext = df['selftext'].apply(has_text, substr_list=config.get('bad_selftext'))

    # Next check bad flairs and other bad indicators
    is_bad_flar = df['link_flair_text'].apply(has_text, substr_list=config.get('bad_flair'))
    is_bad_title = df['title'].apply(has_text, substr_list=config.get('bad_title'))

    # Exclude text only posts
    if config.get('remove_textonly'):
        if 'urls' not in df:
            df['urls'] = extract_urls_from_df(df, config)
        is_textonly = df.apply(lambda r: r.is_self & len(r.urls) == 0 , axis=1)

    # Finally, apply good indicators

    print(df[['selftext', 'urls']])
    return is_textonly

    """
    removed = str(row['removed_by_category'])
    flair_text = str(row['link_flair_text'])
    if len(removed) > 0:
        return "No"
    for flair in GOOD_FLAIR:
        if flair in flair_text:
            return "Yes"
    for flair in BAD_FLAIR:
        if flair in flair_text:
            return "No"
    """
    # return None

def object_to_df(results, colnames, process_reddit_data=False):
    if len(results) > 0:
        # Initialize temporary lists
        d = OrderedDict()
        for key in colnames:
            d[key] = []

        # Iterate through results
        for result in results:
            for key in colnames:
                cleaned_result = clean_reddit_text(result.get(key))
                d[key].append(cleaned_result)

            # Process data and expand columns if flag is set
            if process_reddit_data:
                d['urls'] = None
                ######### STILL WORKING ON THIS


        # Convert to pandas dataframe
        return pandas.DataFrame(d)
    return None

def url_list_to_str(url_list):
    if len(url_list) > 0:
        return ", ".join(url_list)
    return ""
