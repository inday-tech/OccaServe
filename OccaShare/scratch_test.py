from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import json

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
driver = webdriver.Chrome(options=options)
driver.get('http://localhost:8000/caterer/1')
time.sleep(2)

print('--- CONSOLE LOGS ---')
for log in driver.get_log('browser'):
    print(log)

print('--- TRY TO CLICK ---')
try:
    btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Explore')]")
    print('Found', len(btns), 'buttons')
    if btns:
        driver.execute_script('arguments[0].click();', btns[0])
        time.sleep(1)
        print('Clicked using JS')
except Exception as e:
    print('Error:', e)

print('--- CONSOLE LOGS AFTER CLICK ---')
for log in driver.get_log('browser'):
    print(log)
driver.quit()
