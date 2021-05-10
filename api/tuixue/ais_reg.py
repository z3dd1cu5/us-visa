import sys
import time
import json
import random
import requests
import traceback
from bs4 import BeautifulSoup
from threading import Lock
from django.utils import timezone
from . import global_var as g
from . import config
from . import settings
from db.models import AISAccountCache, AISNGLastCall

wait_timeout = 120

def register(country_code, email, password, node):
    lock = g.value(email + "_lock", Lock())
    with lock:
        try:
            new_session = None
            r = AISAccountCache.objects.filter(email=email)
            if len(r) > 0:
                session = r[0].session
                schedule_id = r[0].schedule_id
                group_id = r[0].group_id
                new_session = change_region(country_code, session, group_id)

            if not new_session:
                code, new_session = ais_ng(country_code, email, password)
                if not new_session:
                    return code, None, None

            group_id, schedule_id, new_session = account_page(new_session, country_code)
            if group_id == -1:
                # Cache invalid
                code, new_session = ais_ng(country_code, email, password)
                if not new_session:
                    return code, None, None
                group_id, schedule_id, new_session = account_page(new_session, country_code)

            if not schedule_id:
                return None, None, None
            content, session = payment_page(new_session, schedule_id, country_code)
            if not content:
                return None, None, None

            result = parse_date(content)
            if result:
                if len(r) > 0:
                    r.update(session=session, schedule_id=schedule_id, group_id=group_id)
                else:
                    item = AISAccountCache(email=email, session=session, schedule_id=schedule_id, group_id=group_id)
                    item.save()
            else:
                if len(r) > 0:
                    r.delete()
            return result, session, schedule_id
        except Exception as e:
            if len(r) > 0:
                r.delete()
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
    r = AISNGLastCall.objects.filter(email=email)
    if len(r) == 0:
        item = AISNGLastCall(email=email, last_call_time=timezone.now())
        item.save()
    else:
        last_call_time = r[0].last_call_time
        interval = timezone.now() - last_call_time
        if interval.total_seconds() < 12 * 60:
            return 405, None
        else:
            r.update(last_call_time=timezone.now())
    ais_ng_lock = g.value("ais_ng_lock", Lock())
    with ais_ng_lock:
        try:
            r = requests.get(settings.AIS_CAPTCHA_API_ENDPOINT + "?code=%s&email=%s&pswd=%s" % (country_code, email, password), timeout=wait_timeout)
            new_session = ""
            cookies_list = json.loads(r.text)
            if not type(cookies_list) == list:
                return cookies_list["code"], None
            for item in cookies_list:
                if item.get("name") == "_yatri_session":
                    new_session = item.get("value")
                    return 0, new_session
        except:
            pass
    return None, None


def account_page(new_session, country_code):
    r = requests.get(
        "https://ais.usvisa-info.com/%s/niv/account" % country_code, 
        cookies={
            "_yatri_session": new_session
        }, 
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
            "Referer": "https://ais.usvisa-info.com/%s/niv/users/sign_in" % country_code
        },
        allow_redirects=False
    )
    if r.status_code != 302:
        return None, None, None
    group_id = r.headers["Location"].split("/")[-1]
    new_session = r.cookies["_yatri_session"]

    r = requests.get(
        "https://ais.usvisa-info.com/" + country_code + "/niv/groups/" + group_id, 
        cookies={
            "_yatri_session": new_session
        }, 
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
            "Referer": "https://ais.usvisa-info.com/%s/niv/users/sign_in" % country_code
        }
    )
    if r.status_code != 200:
        return None, None, None
    soup = BeautifulSoup(r.text, "html.parser")
    continue_button = soup.find('a', text="Continue")
    if not continue_button:
        return -1, None, None
    link = continue_button.get('href')
    schedule_id = link.split("/")[-2]
    new_session = r.cookies["_yatri_session"]
    return group_id, schedule_id, new_session


def payment_page(new_session, schedule_id, country_code):
    r = requests.get(
        "https://ais.usvisa-info.com/%s/niv/schedule/%s/payment" % (country_code, schedule_id), 
        cookies={
            "_yatri_session": new_session
        }, 
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
            "Referer": "https://ais.usvisa-info.com/%s/niv/schedule/%s/continue_actions" % (country_code, schedule_id)
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
