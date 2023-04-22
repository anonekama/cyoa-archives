import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from Screenshot import Screenshot

ob = Screenshot.Screenshot()
driver = webdriver.Chrome()
driver.get("http://www.python.org")
assert "Python" in driver.title
img_url = ob.full_Screenshot(driver, save_path=r'.', image_name='Myimage.png')
print(img_url)
time.sleep(10)
driver.close()