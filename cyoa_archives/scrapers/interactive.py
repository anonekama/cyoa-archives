import requests
import logging
import json
import math
import pathlib
import time
import base64

from typing import List

import cv2
import numpy as np

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

def stich_images(img_paths: List, overlap_size: int = 200):
    # img_paths: a list of image paths (ordered)
    if len(img_paths) > 1:
        for i in range(len(img_paths) - 1):
            imga = cv2.imread(img_paths[i])
            imgb = cv2.imread(img_paths[i+1])
            imga_bw = cv2.cvtColor(imga, cv2.COLOR_BGR2GRAY)
            imgb_bw = cv2.cvtColor(imgb, cv2.COLOR_BGR2GRAY)
            imga_h, imga_w = imga_bw.shape
            imgb_h, imgb_w = imgb_bw.shape

            # Assuming that the top of imgb has at least 100px overlap with imga
            # Take a 100 pixel slice of imga (bottom)
            overlap_size = overlap_size
            imga_start = imga_h - overlap_size if (imga_h > overlap_size) else 0
            imga_slice = imga_bw[imga_start:imga_h, 0:imga_w]

            # Now scroll through imga and find coordinates of overlap
            lowest_mse = math.inf
            lowest_j = 0
            for j in range(0, imgb_h - slice):
                imgb_slice = imgb[i:i + slice, 0:imgb_w]
                diff = cv2.subtract(imga_slice, imgb_slice)
                err = np.sum(diff ** 2)
                mse = err / (float(slice * imga_w))
                if mse < lowest_mse:
                    lowest_mse = mse
                    lowest_i = i
                    print(mse)
    else:
        # Return original image
        return None






    # Now stich images together
    imga_crop = imga[0:lowest_i, 0:imga_w]
    img_concat = np.concatenate((imga_crop, imgb), axis=0)

    ## Make pixels row and column 300-400 black
    # img[300:400,300:400] = (0,0,0)

    cv2.imshow('title', img_concat)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def inject_image(uri, url, filename):
    if not uri:
        return uri
    if 'data:image' in uri:
        return uri
    if 'http' in uri:
        absolute_url = uri
    else:
        absolute_url = url + uri
    print(absolute_url)
    r = requests.get(absolute_url)
    print(r)
    data_base64 = base64.b64encode(r.content)  # encode to base64 (bytes)
    data_base64 = data_base64.decode()

    print(data_base64)
    # img.save(filename)
    return 'data:image/jpeg;base64,' + data_base64


def download_interactive(url, out_dir):
    try:
        response = requests.get(url + 'project.json')
        data_json = response.json()


        # Remove all required elements
        data_rows = data_json['rows']
        i = 0
        for row in data_rows:
            if 'requireds' in row:
                row['requireds'] = []
            if 'image' in row:
                row['image'] = inject_image(row['image'], url, f'{i}.jpg')
                i = i + 1
            if 'objects' in row:
                data_objects = row['objects']
                for object in data_objects:
                    if 'requireds' in object:
                        object['requireds'] = []
                    if 'image' in object:
                        object['image'] = inject_image(object['image'], url, f'{i}.jpg')
                        i = i + 1

        # Generate new app.js file
        logger.info('Generating new app.js file...')
        with open('selenium/js/app.c533aa25.js', 'w') as f:
            with open('selenium/js/app_head.js', 'r') as hfile:
                f.write(hfile.read())
            f.write(json.dumps(data_json))
            with open('selenium/js/app_tail.js', 'r') as tfile:
                f.write(tfile.read())

        # Read generated file
        index_file = 'selenium/index.html'
        options = Options()
        options.add_argument("-headless")
        with webdriver.Firefox(options=options) as driver:
            driver.get("file://" + str(pathlib.Path(index_file).resolve()))
            try:
                elem = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "objectRow"))  # This is a dummy element
                )
            finally:
                # Get scroll height
                driver.set_window_size(1900, 3800)
                max_height = driver.execute_script("return document.body.scrollHeight")
                logger.info(f'Document scroll height: {max_height}')

                if max_height > 30000:
                    driver.set_window_size(1920, 30000)
                else:
                    driver.set_window_size(1920, max_height)

                # Scroll to load images
                height = 0
                i = 0
                while height < max_height:
                    # Scroll down to bottom
                    driver.execute_script(f"window.scrollTo(0, {height});")

                    # Wait to load page
                    time.sleep(5)

                    image_filename = pathlib.Path(f"image_{i}.png")
                    image_path = pathlib.Path.joinpath(out_dir, image_filename)
                    driver.save_screenshot(str(image_path.resolve()))
                    logger.info(f'Saving screenshot at: {str(image_path.resolve())}')
                    im = cv2.imread(str(image_path.resolve()))
                    im_height, im_width, im_channels = im.shape

                    # Calculate new scroll height and compare with last scroll height
                    height = height + im_height
                    i = i + 1

                    # If last scroll, resize window again
                    max_height = driver.execute_script("return document.body.scrollHeight")
                    if height + im_height > max_height:
                        # Arbitrary extra 1000 pixels because screen height isn't same as window hieght
                        last_height = max_height - height if max_height - height > 1000 else 1000
                        driver.set_window_size(1920, last_height + 1000)

                driver.close()
    except:
        logger.warning(f'Failed to read url: {url}')
        return None