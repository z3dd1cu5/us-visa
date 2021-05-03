import os
import re
import copy
import json
import base64
import requests
import datetime
import numpy as np
from . import global_var as g
from . import config
from . import vcode2
from bs4 import BeautifulSoup as bs

def do_register(visa_type, place):
    config.load_config()
    cracker = vcode2.Captcha()
    req = requests.Session()
    username, passwd, sid = login(cracker, place, req)
    date, info = visa_select(visa_type, place, sid, req)
    return sid, date, info

def get_date(page):
    if "Authorization Required" in page:
        return None
    try:
        soup = bs(page, "html.parser")
        text = soup.find_all(class_="leftPanelText")[-1].text
        s = text.split()
        if len(s) >= 3:
            month_str, day_str, year_str = s[-3], s[-2].replace(",", ""), s[-1].replace(".", "")
            year, month, day = int(year_str), g.MONTH[month_str], int(day_str)
            return (year, month, day)
    except:
        return (0, 0, 0)

def login(cracker, place, requests):
    proxies = g.value("proxies", None)

    # get register page
    REG_URI = "https://cgifederal.secure.force.com/SiteRegister?country=%s&language=zh_CN" % config.get("ref", place)
    r = requests.get(REG_URI, proxies=proxies)
    if r.status_code != 200:
        return None

    # In case of failure
    for _ in range(5):
        soup = bs(r.text, "html.parser")
        view_state = soup.find(id="com.salesforce.visualforce.ViewState").get("value")
        view_state_version = soup.find(id="com.salesforce.visualforce.ViewStateVersion").get("value")
        view_state_mac = soup.find(id="com.salesforce.visualforce.ViewStateMAC").get("value")
        cookies = r.cookies

        # get recaptcha
        REG_CAPTCHA_URI = "https://cgifederal.secure.force.com/SiteRegister?refURL=https%3A%2F%2Fcgifederal.secure.force.com%2F%3Flanguage%3DChinese%2520%28Simplified%29%26country%3D" + config.get("ref", place)
        data = {
            "AJAXREQUEST": "_viewRoot",
            "Registration:SiteTemplate:theForm": "Registration:SiteTemplate:theForm",
            "Registration:SiteTemplate:theForm:username": "",
            "Registration:SiteTemplate:theForm:firstname": "",
            "Registration:SiteTemplate:theForm:lastname": "",
            "Registration:SiteTemplate:theForm:password": "",
            "Registration:SiteTemplate:theForm:confirmPassword": "",
            "Registration:SiteTemplate:theForm:response": "",
            "Registration:SiteTemplate:theForm:recaptcha_response_field": "",
            "com.salesforce.visualforce.ViewState": view_state,
            "com.salesforce.visualforce.ViewStateVersion": view_state_version,
            "com.salesforce.visualforce.ViewStateMAC": view_state_mac,
            "Registration:SiteTemplate:theForm:j_id177": "Registration:SiteTemplate:theForm:j_id177"
        }
        r = requests.post(REG_CAPTCHA_URI, data=data, cookies=cookies, proxies=proxies)
        if r.status_code != 200:
            return None

        soup = bs(r.text, "html.parser")
        view_state = soup.find(id="com.salesforce.visualforce.ViewState").get("value")
        view_state_version = soup.find(id="com.salesforce.visualforce.ViewStateVersion").get("value")
        view_state_mac = soup.find(id="com.salesforce.visualforce.ViewStateMAC").get("value")
        cookies = r.cookies

        raw = soup.find_all(id='Registration:SiteTemplate:theForm:theId')
        raw = raw[0].attrs['src'].replace('data:image;base64,', '')
        img = base64.b64decode(raw)
        #gifname = 'try.gif'
        #open(gifname, 'wb').write(img)
        #open('gifname', 'w').write(gifname)
        captcha = cracker.solve(img)
        if len(captcha) == 0:
            open('state', 'w').write(
                '自动识别服务挂掉了，请到<a href="https://github.com/Trinkle23897/'
                'us-visa">GitHub</a>上提issue')
            return None

        # click and register
        username = ''.join([chr(np.random.randint(26) + ord('a')) for _ in range(15)]) + "@gmail.com"
        passwd = ''.join(np.random.permutation(' '.join('12345qwert').split()))
        data = {
            "Registration:SiteTemplate:theForm": "Registration:SiteTemplate:theForm",
            "Registration:SiteTemplate:theForm:username": username,
            "Registration:SiteTemplate:theForm:firstname": "Langpu",
            "Registration:SiteTemplate:theForm:lastname": "Te",
            "Registration:SiteTemplate:theForm:password": passwd,
            "Registration:SiteTemplate:theForm:confirmPassword": passwd,
            "Registration:SiteTemplate:theForm:j_id169": "on",
            "Registration:SiteTemplate:theForm:response": captcha,
            "Registration:SiteTemplate:theForm:recaptcha_response_field": "",
            "Registration:SiteTemplate:theForm:submit": "提交",
            "com.salesforce.visualforce.ViewState": view_state,
            "com.salesforce.visualforce.ViewStateVersion": view_state_version,
            "com.salesforce.visualforce.ViewStateMAC": view_state_mac
        }
        r = requests.post(REG_CAPTCHA_URI, data=data, cookies=cookies, proxies=proxies)
        if r.status_code != 200:
            return None
        front_door_uri = r.text.split("'")[-2]
        if front_door_uri.startswith("https"):
            #os.system('mv %s log/%s.gif' % (gifname, captcha))
            break
        else:
            #if not os.path.exists('fail'):
            #    os.makedirs('fail')
            #os.system('mv %s fail/%s.gif' % (gifname, captcha))
            if hasattr(cracker, 'wrong'):
                cracker.wrong()

    # open front door
    r = requests.get(front_door_uri, cookies=cookies, proxies=proxies)
    cookies = r.cookies
    return username, passwd, cookies["sid"]

def visa_select(visa_type, place, sid, requests):
    type_info = ""
    proxies = g.value("proxies", None)
    cookies = copy.deepcopy(g.COOKIES)
    cookies["sid"] = sid

    # select immigrant/nonimmigrant visa
    select_visa_type_uri = "https://cgifederal.secure.force.com/selectvisatype"
    r = requests.get(select_visa_type_uri, cookies=cookies, proxies=proxies)
    if r.status_code != 200:
        return None, type_info
    soup = bs(r.text, "html.parser")
    view_state = soup.find(id="com.salesforce.visualforce.ViewState").get("value")
    view_state_version = soup.find(id="com.salesforce.visualforce.ViewStateVersion").get("value")
    view_state_mac = soup.find(id="com.salesforce.visualforce.ViewStateMAC").get("value")
    view_state_csrf = soup.find(id="com.salesforce.visualforce.ViewStateCSRF").get("value")
    data = {
        "j_id0:SiteTemplate:theForm": "j_id0:SiteTemplate:theForm",
        "j_id0:SiteTemplate:theForm:ttip": "Nonimmigrant Visa",
        "j_id0:SiteTemplate:theForm:j_id176": "继续",
        "com.salesforce.visualforce.ViewState": view_state,
        "com.salesforce.visualforce.ViewStateVersion": view_state_version,
        "com.salesforce.visualforce.ViewStateMAC": view_state_mac,
        "com.salesforce.visualforce.ViewStateCSRF": view_state_csrf
    }
    r = requests.post(select_visa_type_uri, data=data, cookies=cookies, proxies=proxies)
    if r.status_code != 200:
        return None, type_info

    # select place
    if place in config.get("place2id").keys():
        select_post_uri = "https://cgifederal.secure.force.com/selectpost"
        r = requests.get(select_post_uri, cookies=cookies, proxies=proxies)
        if r.status_code != 200:
            return None, type_info
        soup = bs(r.text, "html.parser")
        view_state = soup.find(id="com.salesforce.visualforce.ViewState").get("value")
        view_state_version = soup.find(id="com.salesforce.visualforce.ViewStateVersion").get("value")
        view_state_mac = soup.find(id="com.salesforce.visualforce.ViewStateMAC").get("value")
        view_state_csrf = soup.find(id="com.salesforce.visualforce.ViewStateCSRF").get("value")
        contact_id = soup.find(id="j_id0:SiteTemplate:j_id112:contactId").get("value")
        target_id = "j_id0:SiteTemplate:j_id112:j_id165:" + str(config.get("place2id", place))
        place_code = soup.find(id=target_id).get("value")
        data = {
            "j_id0:SiteTemplate:j_id112": "j_id0:SiteTemplate:j_id112",
            "j_id0:SiteTemplate:j_id112:j_id165": place_code,
            "j_id0:SiteTemplate:j_id112:j_id169": "继续",
            "j_id0:SiteTemplate:j_id112:contactId": contact_id,
            "com.salesforce.visualforce.ViewState": view_state,
            "com.salesforce.visualforce.ViewStateVersion": view_state_version,
            "com.salesforce.visualforce.ViewStateMAC": view_state_mac,
            "com.salesforce.visualforce.ViewStateCSRF": view_state_csrf
        }
        r = requests.post(select_post_uri, data=data, cookies=cookies, proxies=proxies)
        if r.status_code != 200:
            return None, type_info

    is_valid = True
    for try_count in range(10):
        # select visa category
        select_visa_category_uri = "https://cgifederal.secure.force.com/selectvisacategory"
        r = requests.get(select_visa_category_uri, cookies=cookies, proxies=proxies)
        if r.status_code != 200:
            return None, type_info
        soup = bs(r.text, "html.parser")
        view_state = soup.find(id="com.salesforce.visualforce.ViewState").get("value")
        view_state_version = soup.find(id="com.salesforce.visualforce.ViewStateVersion").get("value")
        view_state_mac = soup.find(id="com.salesforce.visualforce.ViewStateMAC").get("value")
        view_state_csrf = soup.find(id="com.salesforce.visualforce.ViewStateCSRF").get("value")
        contact_id = soup.find(id="j_id0:SiteTemplate:j_id109:contactId").get("value")
        prefix = "j_id0:SiteTemplate:j_id109:j_id162:"
        if not place in config.get("category2id", visa_type):
            config.set(0, "category2id", visa_type, place)
            is_valid = False
        category_count = len(soup.find_all("input", {"type": "radio"}))
        choice_idx = config.get("category2id", visa_type, place)
        if not choice_idx < category_count:
            config.set(0, "category2id", visa_type, place)
            choice_idx = 0
            is_valid = False
        category_code = soup.find(id=prefix + str(choice_idx)).get("value")
        data = {
            "j_id0:SiteTemplate:j_id109": "j_id0:SiteTemplate:j_id109",
            "j_id0:SiteTemplate:j_id109:j_id162": category_code,
            "j_id0:SiteTemplate:j_id109:j_id166": "继续",
            "j_id0:SiteTemplate:j_id109:contactId": contact_id,
            "com.salesforce.visualforce.ViewState": view_state,
            "com.salesforce.visualforce.ViewStateVersion": view_state_version,
            "com.salesforce.visualforce.ViewStateMAC": view_state_mac,
            "com.salesforce.visualforce.ViewStateCSRF": view_state_csrf
        }
        r = requests.post(select_visa_category_uri, data=data, cookies=cookies, proxies=proxies)
        if r.status_code != 200:
            return None, type_info

        # select visa type
        select_visa_code_uri = "https://cgifederal.secure.force.com/selectvisacode"
        r = requests.get(select_visa_code_uri, cookies=cookies, proxies=proxies)
        # if r.status_code != 200:
        #     return None, type_info
        soup = bs(r.text, "html.parser")
        view_state = soup.find(id="com.salesforce.visualforce.ViewState").get("value")
        view_state_version = soup.find(id="com.salesforce.visualforce.ViewStateVersion").get("value")
        view_state_mac = soup.find(id="com.salesforce.visualforce.ViewStateMAC").get("value")
        view_state_csrf = soup.find(id="com.salesforce.visualforce.ViewStateCSRF").get("value")
        inputs = soup.find_all("input")
        type_codes = [x.get("value") for x in inputs if x.get("name") == "selectedVisaClass"]
        type_infos = [re.sub('<[^>]*>', "", x.parent.label.text.strip()) for x in inputs if x.get("name") == "selectedVisaClass"]
        #print(type_infos)
        if try_count > category_count:
            # in case of no choice
            break
        if sum([i.startswith(g.VISA_PROMPT[visa_type]) for i in type_infos]) == 0:
            tmp = config.get("category2id", visa_type, place) 
            config.set((tmp + 1) % category_count, "category2id", visa_type, place)
            is_valid = False
            continue
        type_idx = [i.startswith(g.VISA_PROMPT[visa_type]) for i in type_infos].index(True)
        type_code = type_codes[type_idx]
        type_info = type_infos[type_idx]
        data = {
            "j_id0:SiteTemplate:theForm": "j_id0:SiteTemplate:theForm",
            "j_id0:SiteTemplate:theForm:j_id178": "继续",
            "selectedVisaClass": type_code,
            "com.salesforce.visualforce.ViewState": view_state,
            "com.salesforce.visualforce.ViewStateVersion": view_state_version,
            "com.salesforce.visualforce.ViewStateMAC": view_state_mac,
            "com.salesforce.visualforce.ViewStateCSRF": view_state_csrf
        }
        r = requests.post(select_visa_code_uri, data=data, cookies=cookies, proxies=proxies)
        if r.status_code != 200:
            return None, type_info
        break

    if not is_valid:
        config.save_config()

    # select visa priority
    for _ in range(1):
        select_prior_code_uri = "https://cgifederal.secure.force.com/selectvisapriority"
        r = requests.get(select_prior_code_uri, cookies=cookies, proxies=proxies)
        if r.status_code != 200:
            break
        soup = bs(r.text, "html.parser")
        view_state = soup.find(id="com.salesforce.visualforce.ViewState").get("value")
        view_state_version = soup.find(id="com.salesforce.visualforce.ViewStateVersion").get("value")
        view_state_mac = soup.find(id="com.salesforce.visualforce.ViewStateMAC").get("value")
        view_state_csrf = soup.find(id="com.salesforce.visualforce.ViewStateCSRF").get("value")
        inputs = soup.find_all("input")
        type_codes = [x.get("value") for x in inputs if x.get("name") == "j_id0:SiteTemplate:theForm:SelectedVisaPriority"]
        type_infos = [re.sub('<[^>]*>', "", x.parent.label.text.strip()) for x in inputs if x.get("name") == "j_id0:SiteTemplate:theForm:SelectedVisaPriority"]
        choose_option = "Regular" if place.endswith("r") else "Non-Resident"
        if len(type_infos) > 0:
            for idx, info in enumerate(type_infos):
                if not info.startswith(choose_option):
                    continue
                type_code = type_codes[idx]
                data = {
                    "j_id0:SiteTemplate:theForm": "j_id0:SiteTemplate:theForm",
                    "j_id0:SiteTemplate:theForm:j_id170": "继续",
                    "j_id0:SiteTemplate:theForm:SelectedVisaPriority": type_code,
                    "com.salesforce.visualforce.ViewState": view_state,
                    "com.salesforce.visualforce.ViewStateVersion": view_state_version,
                    "com.salesforce.visualforce.ViewStateMAC": view_state_mac,
                    "com.salesforce.visualforce.ViewStateCSRF": view_state_csrf
                }
                r = requests.post(select_prior_code_uri, data=data, cookies=cookies, proxies=proxies)

    # update data
    update_data_uri = "https://cgifederal.secure.force.com/updatedata"
    r = requests.get(update_data_uri, cookies=cookies, proxies=proxies)
    if r.status_code != 200:
        return None, type_info
    date = get_date(r.text)
    if date:
        g.assign("status_%s_%s" % (visa_type, place), date)
    return date, type_info

def operation(keys, value, op):
    config.load_config()
    if op == "get":
        obj = config.get(*keys)
        return json.dumps(obj, ensure_ascii=False)
    elif op == "set":
        try:
            value = int(value)
        except:
            pass
        config.set(value, *keys)
        config.save_config()
        obj = config.get(*keys)
        return json.dumps(obj, ensure_ascii=False)
    elif op == "del":
        config.delete(*keys)
        config.save_config()
        return "Done"
