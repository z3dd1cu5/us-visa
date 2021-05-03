import sys
import time
import json
import random
import requests
import traceback
from bs4 import BeautifulSoup
from threading import Lock
from . import global_var as g
from . import config

wait_timeout = 120
cache = {}

def register(country_code, email, password, node):
    global cache
    lock = g.value(email + "_lock", Lock())
    with lock:
        try:
            new_session = None
            if email in cache:
                session, schedule_id, group_id = cache[email]
                new_session = change_region(country_code, session, group_id)

            if not new_session:
                code, new_session = ais_ng(country_code, email, password)
                if not new_session:
                    return code, None, None

            group_id, schedule_id, new_session = account_page(new_session)
            if not schedule_id:
                return None, None, None
            content, session = payment_page(new_session, schedule_id)
            if not content:
                return None, None, None

            result = parse_date(content)
            if result:
                cache[email] = [session, schedule_id, group_id]
            else:
                del cache[email]
            return result, session, schedule_id
        except Exception as e:
            if email in cache:
                del cache[email]
            traceback.print_exc()
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
    if "Sign Out" not in r.text:
        return None
    session = r.cookies["_yatri_session"]
    return session


def ais_ng(country_code, email, password):
    ais_ng_lock = g.value("ais_ng_lock", Lock())
    with ais_ng_lock:
        try:
            r = requests.get(config.get("ais_ng_api") + "?code=%s&email=%s&pswd=%s" % (country_code, email, password), timeout=wait_timeout)
        except:
            pass
    new_session = ""
    cookies_list = json.loads(r.text)
    if not type(cookies_list) == list:
        return cookies_list["code"], None
    for item in cookies_list:
        if item.get("name") == "_yatri_session":
            new_session = item.get("value")
            return 0, new_session
    return None, None


def account_page(new_session):
    r = requests.get(
        "https://ais.usvisa-info.com/en-gb/niv/account", 
        cookies={
            "_yatri_session": new_session
        }, 
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
            "Referer": "https://ais.usvisa-info.com/en-gb/niv/users/sign_in"
        },
        allow_redirects=False
    )
    if r.status_code != 302:
        return None, None, None
    group_id = r.headers["Location"].split("/")[-1]
    new_session = r.cookies["_yatri_session"]

    r = requests.get(
        "https://ais.usvisa-info.com/en-gb/niv/groups/" + group_id, 
        cookies={
            "_yatri_session": new_session
        }, 
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
            "Referer": "https://ais.usvisa-info.com/en-gb/niv/users/sign_in"
        }
    )
    if r.status_code != 200:
        return None, None, None
    soup = BeautifulSoup(r.text, "html.parser")
    link = soup.find('a', text="Continue").get('href')
    schedule_id = link.split("/")[-2]
    new_session = r.cookies["_yatri_session"]
    return group_id, schedule_id, new_session


def payment_page(new_session, schedule_id):
    r = requests.get(
        "https://ais.usvisa-info.com/en-gb/niv/schedule/%s/payment" % schedule_id, 
        cookies={
            "_yatri_session": new_session
        }, 
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
            "Referer": "https://ais.usvisa-info.com/en-gb/niv/schedule/%s/continue_actions" % schedule_id
        }
    )
    if r.status_code != 200:
        return None, None
    session = r.cookies["_yatri_session"]
    return r.text, session


def parse_date(content):
    soup = BeautifulSoup(content, "html.parser")
    time_table = soup.find("table", {"class": "for-layout"})
    result = []
    if time_table:
        trs = time_table.find_all('tr')
        for tr in trs:
            tds = tr.find_all('td')
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
    return result
