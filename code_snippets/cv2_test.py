import argparse
import json
import pathlib
import numpy as np
import logging
import pathlib
import shutil
import subprocess
import sys
import os
import math

import cv2
import pandas as pd
import yaml

from cyoa_archives.predictor.image import CyoaImage


def main():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)


    #image_fn = pathlib.Path('test.png')
    #image_fn = pathlib.Path('test1.jpeg')
    #image_fn = pathlib.Path('test2.jpeg')
    #image_fn = pathlib.Path('test3.jpeg')
    #image_fn = pathlib.Path('test4.jpg')
    #image_fn = pathlib.Path('test7.jpeg')
    #image_fn = pathlib.Path('test8.png')
    # image_fn = pathlib.Path('test11.png')

    image_fns = [
        pathlib.Path('data/test1.jpeg'),
        pathlib.Path('data/test2.jpeg'),
        pathlib.Path('data/test3.jpeg'),
        pathlib.Path('data/test4.jpg'),
        pathlib.Path('data/test5.png'),
        pathlib.Path('data/test6.png'),
        pathlib.Path('data/test7.jpeg'),
        pathlib.Path('data/test8.png'),
        pathlib.Path('data/test10.png'),
        pathlib.Path('data/test11.png'),
        pathlib.Path('data/test12.jpg'),
        pathlib.Path('data/test13.png'),
        pathlib.Path('data/test14.jpg'),
        pathlib.Path('data/test15.jpg'),
        pathlib.Path('data/test16.png'),
        pathlib.Path('data/test17.jpg'),
        pathlib.Path('data/test18.png'),
        pathlib.Path('data/test19.jpeg'),
        pathlib.Path('data/test20.jpeg')
    ]

    d = {}
    for image_fn in image_fns:
        cyoa_image = CyoaImage(image_fn)
        #cyoa_image.make_chunks()
        #text = cyoa_image.get_text()
        filename = image_fn.stem
        result = cyoa_image.run_deepdanbooru_random(1)
        d[filename] = result

    dataframe = pd.DataFrame(d)
    dataframe.to_csv(f'all_data.csv')

    """
    csv_list = []
    for image_fn in image_fns:
        stem = image_fn.stem
        csv_list.append(f'img_{stem}.csv')


    data = pd.read_csv('img_test1.csv', index_col=False)
    print(data)
    data = data.iloc[:, 1:-1]
    for csv_file in csv_list[1:]:
        df = pd.read_csv(csv_file, index_col=False)
        df = df.iloc[:, 1:-1]
        data = pd.merge(data, df, left_on='keys', right_on='keys')
    data.to_csv(f'all_data.csv')
    """


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a subreddit for submissions using praw."
    )
    # parser.add_argument("-c", "--config_file", help="Configuration file to use")

    # Parse arguments
    args = parser.parse_args()
    """
    # Load arguments from configuration file if provided
    if args.config_file:
        filepath = pathlib.Path(args.config_file)
        try:
            with open(filepath) as f:
                config = yaml.safe_load(f)
        except OSError:
            print(f"Could not read file: {filepath}")
            sys.exit(1)
    """

    # Pass to main function
    main()
