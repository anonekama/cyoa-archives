import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

options = webdriver.ChromeOptions()
options.headless = True

driver = webdriver.Chrome(options=options)
driver.get("https://scarlet-m.neocities.org/cyoa/Bloody_Heaven/")
actions = ActionChains(driver)
try:
    elem = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, "objectRow")) #This is a dummy element
    )
finally:
    driver.save_screenshot("image.png")

    SCROLL_PAUSE_TIME = 0.5

    # Get scroll height
    driver.set_window_size(1920, 1080)
    max_height = driver.execute_script("return document.body.scrollHeight")
    print(max_height)
    driver.set_window_size(1920, max_height)

    el = driver.find_element(By.TAG_NAME, 'body')
    time.sleep(5)
    el.screenshot('full.png')

    """
    rows = driver.find_elements(By.CLASS_NAME, "objectRow")
    for row in rows:
        divs = row.find_elements(By.TAG_NAME, "div")
        for div in divs:
            actions.move_to_element(div).perform()
            div.click()
            time.sleep(1)

            # Check height of document
            current_height = driver.execute_script("return document.body.scrollHeight")
            print(current_height)
            if current_height > max_height:
                max_height = current_height
                continue
            else:
                div.click()
                time.sleep(1)
    """

    """
    i = 1
    height = 0
    while height < max_height:
        # Scroll down to bottom
        driver.execute_script(f"window.scrollTo(0, {height});")

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        driver.save_screenshot(f"image_{i}.png")
        height = height + 500
        i = i + 1
    """

    # For every child in object row

    driver.close()