
import os
import pathlib

import pandas as pd


# Taglist
tag_path='deepdanbooru-v3-20211112-sgd-e28/tags.txt'
tags_list = []
with open(tag_path, 'r') as f:
    for line in f.readlines():
        tags_list.append(line.strip())

# Scan directory
data = {}
folder_path = '../db'
for item in os.scandir(folder_path):
    item_path = pathlib.Path(item)
    if item_path.is_dir():
        cyoa_title = item_path.stem
        data_file = pathlib.Path.joinpath(item_path, 'dd.txt')
        vector = []
        with open(data_file, 'r') as f:
            for line in f.readlines():
                vector.append(float(line.strip()))
        data[cyoa_title] = vector

# Print to pandas
df = pd.DataFrame(data)
df.insert(0, 'tags', tags_list)
df.to_csv('merged_data.csv')