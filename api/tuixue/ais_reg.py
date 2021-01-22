import sys
import time
import json
import random
import requests
from threading import Lock
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from . import global_var as g
from . import config

wait_timeout = 20
refresh_interval = 30

chrome_options = Options()
chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument("--headless")

cache = {}

def register(country_code, email, password, node):
    global cache
    lock =  g.value(email + "_lock", Lock())
    lock.acquire()
    # Login
    try:
        c_service = Service("/usr/bin/chromedriver")
        c_service.command_line_args()
        c_service.start()
        if len(node) > 0:
            entry = node
        else:
            selenium_list = [x.strip() for x in open("node.txt", "r").readlines()]
            entry = random.choice(selenium_list)
        driver = webdriver.Remote(
            command_executor='http://%s:4444/wd/hub' % entry,
            desired_capabilities=chrome_options.to_capabilities()
        )
        driver.set_window_size(1036 + random.randint(0, 20), 583 + random.randint(0, 20))
        print("Choose Node:", entry)

        if email in cache:
            session, schedule_id, group_id = cache[email]
            new_session = change_region(country_code, session, group_id)
            driver.get("https://ais.usvisa-info.com")
            driver.add_cookie({'name' : '_yatri_session', 'value' : new_session, 'path' : '/', 'domain': 'ais.usvisa-info.com', 'secure': True})
            driver.get("https://ais.usvisa-info.com/%s/niv/groups/%s" % (country_code, group_id))
        else:
            ais_ng_lock = g.value("ais_ng_lock", Lock())
            ais_ng_lock.acquire()
            try:
                r = requests.get(config.get("ais_ng_api") + "?code=%s&email=%s&pswd=%s" % (country_code, email, password))
            except:
                pass
            ais_ng_lock.release()
            new_session = ""
            cookies_list = json.loads(r.text)
            for item in cookies_list:
                if item.get("name") == "_yatri_session":
                    new_session = item.get("value")

            driver.get("https://ais.usvisa-info.com")
            driver.add_cookie({'name' : '_yatri_session', 'value' : new_session, 'path' : '/', 'domain': 'ais.usvisa-info.com', 'secure': True})
            driver.get("https://ais.usvisa-info.com/%s/niv" % country_code)

        def wait_loading(xpath, option="locate"):
            try:
                if option == "locate":
                    element_present = EC.presence_of_element_located((By.XPATH, xpath))
                elif option == "clickable":
                    element_present = EC.element_to_be_clickable((By.XPATH, xpath))
                WebDriverWait(driver, wait_timeout).until(element_present)
            except TimeoutException:
                print("Timed out waiting for page to load")
                driver.execute_script("window.scrollTo(0, 1080)")
                driver.save_screenshot("test.png")

        # Continue
        continue_button_xpath = "//a[contains(text(), 'Continue')]"
        wait_loading(continue_button_xpath)
        current_url = driver.current_url
        group_id = current_url.split("/")[-1]
        continue_button = driver.find_element_by_xpath(continue_button_xpath)
        continue_button.click()

        # Choose action 
        pay_button_xpath = "//a[contains(text(), 'Pay Visa Fee')]"
        wait_loading(pay_button_xpath)
        banner = driver.find_element_by_tag_name('h5')
        banner.click()
        wait_loading(pay_button_xpath, option="clickable")
        pay_button = driver.find_element_by_xpath(pay_button_xpath)
        pay_button.click()

        # Collect result
        title_xpath = "//h2[contains(text(), 'MRV Fee Details')]"
        wait_loading(title_xpath)
        time_table = driver.find_element_by_class_name('for-layout')
        result = []
        if time_table:
            trs = time_table.find_elements_by_tag_name('tr')
            for tr in trs:
                tds = tr.find_elements_by_tag_name('td')
                if not len(tds) == 2:
                    continue
                place = tds[0].text
                date_str = tds[1].text
                s = date_str.split()
                year, month, day = 0, 0, 0
                if len(s) >= 3 and s[0] != "No":
                    day_str, month_str, year_str = s[-3], s[-2].replace(",", ""), s[-1]
                    year, month, day = int(year_str), g.MONTH[month_str], int(day_str)
                result.append([place, (year, month, day)])

        current_url = driver.current_url
        schedule_id = current_url.split("/")[-2]
        session = driver.get_cookie("_yatri_session")["value"]
        driver.quit()
        c_service.stop()
        if result:
            cache[email] = [session, schedule_id, group_id]
        else:
            del cache[email]
        lock.release()
        return result, session, schedule_id
    except Exception as e:
        if email in cache:
            del cache[email]
        print(str(e))
    lock.release()
    if driver:
        driver.quit()
    if c_service:
        c_service.stop()
    return None, None, None


def change_region(country_code, session, group_id):
    req = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36",
        "Referer": "https://ais.usvisa-info.com/%s/niv/groups/%s" % (country_code, group_id),
        "Cookie": "_yatri_session=" + session
    }
    r = req.get("https://ais.usvisa-info.com/%s/niv/groups/%s" % (country_code, group_id), headers=headers)
    if r.status_code != 200:
        print("Error")
    session = r.cookies["_yatri_session"]
    return session
