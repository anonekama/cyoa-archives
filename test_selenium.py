import time
import json
import pathlib
import requests
import base64

from PIL import Image
import cv2
import imutils

from urllib.request import urlopen


from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options

#url = "https://imnotjuice.neocities.org/CYOA/Evil%20Empire%200.8/"
url = "https://radioarc.neocities.org/cyoa/Fire%20Emblem%20v2/"
# url = 'https://dragonswhore-cyoas.neocities.org/Lure_p4_Dalet/'

# store the response of URL
response = urlopen(url + 'project.json')
# response = urlopen('https://imnotjuice.neocities.org/project.json')

# storing the JSON response
# from url in data
data_json = json.loads(response.read())
# print(data_json)

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
    #img.save(filename)
    return 'data:image/jpeg;base64,' + data_base64


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
with open('selenium/js/app.c533aa25.js', 'w') as f:
    with open('selenium/js/app_head.js', 'r') as hfile:
        f.write(hfile.read())
    f.write(json.dumps(data_json))
    with open('selenium/js/app_tail.js', 'r') as tfile:
        f.write(tfile.read())

# Inject image urls
# If image is data:image/jpeg;base64, don't touch

index_file = 'selenium/index.html'
options = Options()
options.add_argument("-headless")
with webdriver.Firefox(options=options) as driver:
    driver.get("file://" + str(pathlib.Path(index_file).resolve()))
    actions = ActionChains(driver)
    try:
        elem = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "objectRow")) #This is a dummy element
        )
    finally:
        driver.save_screenshot("image.png")

        SCROLL_PAUSE_TIME = 0.5
        # wait_until_images_loaded(driver)

        # Get scroll height
        driver.set_window_size(1900, 3800)
        max_height = driver.execute_script("return document.body.scrollHeight")

        print(max_height)
        if max_height > 30000:
            driver.set_window_size(1920, 30000)
        else:
            driver.set_window_size(1920, max_height)

        # Scroll to load images
        height = 0
        # image_filenames = []
        i = 0
        while height < max_height:
            # Scroll down to bottom
            driver.execute_script(f"window.scrollTo(0, {height});")

            # Wait to load page
            time.sleep(5)

            image_filename = f"image_{i}.png"
            driver.save_screenshot(image_filename)
            im = cv2.imread(image_filename)
            im_height, im_width, im_channels = im.shape

            # Calculate new scroll height and compare with last scroll height
            # image_filename = f"image_{i}.png"
            # driver.save_screenshot(image_filename)
            # image_filenames.append(image_filename)
            height = height + im_height
            i = i + 1

            # If last scroll, resize window again
            max_height = driver.execute_script("return document.body.scrollHeight")
            print(max_height)
            if height + im_height > max_height:
                # Arbitrary extra 1000 pixels because screen height isn't same as window hieght
                driver.set_window_size(1920, max_height - height + 1000)

        driver.close()