#!/usr/bin/env python
# coding: utf-8

import sys
import os
import time
import random
import requests
import json
import re
from os.path import dirname
import zbxtg_settings


def list_cut(elements, symbols_limit):
    symbols_count = symbols_count_now = 0
    elements_new = []
    element_last = None
    element_last_list = []
    for e in elements:
        symbols_count_now = symbols_count + len(e)
        if symbols_count_now > symbols_limit:
            limit_idx = symbols_limit - symbols_count
            e_list = list(e)
            for idx, ee in enumerate(e_list):
                if idx < limit_idx:
                    element_last_list.append(ee)
                else:
                    break
            break
        else:
            symbols_count = symbols_count_now + 1
            elements_new.append(e)
    if symbols_count_now < symbols_limit:
        return elements, False
    else:
        element_last = "".join(element_last_list)
        elements_new.append(element_last)
        return elements_new, True


def tg_get_updates(proxies, key):
    tg_url_bot_general = "https://api.telegram.org/bot"
    url = tg_url_bot_general + key + "/getUpdates"
    res = requests.get(url, proxies=proxies)
    answer = res._content
    answer_json = json.loads(answer)
    if not answer_json["ok"]:
        print(answer_json)
        sys.exit(1)
    else:
        return answer_json


def tg_send_message(proxies, key, to, message):
    tg_url_bot_general = "https://api.telegram.org/bot"
    url = tg_url_bot_general + key + "/sendMessage"
    message = "\n".join(message)
    params = {"chat_id": to, "text": message, "parse_mode": "Markdown"}
    res = requests.post(url, params=params, proxies=proxies)
    answer = res._content
    answer_json = json.loads(answer)
    if not answer_json["ok"]:
        print(answer_json)
        sys.exit(1)
    else:
        return answer_json


def tg_send_photo(proxies, key, to, message, path):
    tg_url_bot_general = "https://api.telegram.org/bot"
    url = tg_url_bot_general + key + "/sendPhoto"
    message = "\n".join(message)
    params = {"chat_id": to, "caption": message}
    files = {"photo": open(path, 'rb')}
    res = requests.post(url, params=params, files=files, proxies=proxies)
    answer = res._content
    answer_json = json.loads(answer)
    if not answer_json["ok"]:
        print(answer_json)
        sys.exit(1)
    else:
        return answer_json


def zbx_image_get(proxies, verify, api_server, api_user, api_pass, itemid, period, title, width, height, file):
    if not verify:
        requests.packages.urllib3.disable_warnings()
    data_api = {"name": api_user, "password": api_pass, "enter": "Sign in"}
    zbx_img_url = api_server + "/chart3.php?period={1}&name={2}" \
                               "&width={3}&height={4}&graphtype=0&legend=1" \
                               "&items[0][itemid]={0}&items[0][sortorder]=0" \
                               "&items[0][drawtype]=5&items[0][color]=00CC00".format(itemid, period, title,
                                                                                     width, height)
    req_cookie = requests.post(api_server + "/", data=data_api, proxies=proxies, verify=verify)
    cookie = req_cookie.cookies
    if len(req_cookie.history) > 1 and req_cookie.history[0].status_code == 302:
        print(zbxtg_settings.zbx_tg_prefix, "probably the server in your config file has not full URL (for example "
                                            "'{0}' instead of '{1}')".format(api_server, api_server + "/zabbix"))
    if not cookie:
        print(zbxtg_settings.zbx_tg_prefix + "authorization has failed")
        sys.exit(1)
    res = requests.get(zbx_img_url, cookies=cookie, proxies=proxies, verify=verify)
    res_code = res.status_code
    if res_code == 404:
        print(zbxtg_settings.zbx_tg_prefix, "can't get image from '{0}'".format(zbx_img_url))
        sys.exit(1)
    res_img = res._content
    with open(file, 'wb') as fp:
        fp.write(res_img)

    return True


def main():

    tmp_dir = zbxtg_settings.zbx_tg_tmp_dir

    if not os.path.isdir(tmp_dir):
        try:
            os.makedirs(tmp_dir)
        except:
            tmp_dir = "/tmp"

    tmp_cookie = tmp_dir + "/cookie.py.txt"
    tmp_uids = tmp_dir + "/uids.txt"
    tmp_update = False  # do we need to update cache file with uids or not

    rnd = random.randint(0,999)
    ts = time.time()
    hash_ts = str(ts) + "." + str(rnd)

    log_file = "/dev/null"

    zbx_to = sys.argv[1]
    zbx_subject = sys.argv[2]
    zbx_body = sys.argv[3]

    zbx_to = zbx_to.replace("@", "")

    tg_contact_type = "private"
    tg_contact_type_old = "user"

    proxies_tg = {}
    if zbxtg_settings.proxy_to_tg:
        proxies_tg = {"http": "http://{0}/".format(zbxtg_settings.proxy_to_tg)}
    proxies_zbx = {}
    if zbxtg_settings.proxy_to_zbx:
        proxies_zbx = {"http": "http://{0}/".format(zbxtg_settings.proxy_to_zbx)}

    zbxtg_body = (zbx_subject + "\n" + zbx_body).splitlines()
    zbxtg_body_text = []

    settings = {
        "zbxtg_itemid": "0",  # itemid for graph
        "zbxtg_title": None,  # title for graph
        "zbxtg_image_period": "3600",
        "zbxtg_image_width": "900",
        "zbxtg_image_height": "200",
        "tg_method_image": False,  # if True - default send images, False - send text
        "tg_chat": False,  # send message to chat or in private
        "is_debug": False,
    }
    settings_description = {
        "itemid": {"name": "zbxtg_itemid", "type": "int"},
        "title": {"name": "zbxtg_title", "type": "str"},
        "graphs_period": {"name": "zbxtg_image_period", "type": "int"},
        "graphs_width": {"name": "zbxtg_image_width", "type": "int"},
        "graphs_height": {"name": "zbxtg_image_height", "type": "int"},
        "graphs": {"name": "tg_method_image", "type": "bool"},
        "chat": {"name": "tg_chat", "type": "bool"},
        "debug": {"name": "is_debug", "type": "bool"},
    }

    for line in zbxtg_body:
        if line.find(zbxtg_settings.zbx_tg_prefix) > -1:
            setting = re.split("[\s:]+", line, maxsplit=1)
            key = setting[0].replace(zbxtg_settings.zbx_tg_prefix + ";", "")
            if len(setting) > 1:
                value = setting[1]
            else:
                value = True
            if key in settings_description:
                settings[settings_description[key]["name"]] = value
        else:
            zbxtg_body_text.append(line)

    tg_method_image = bool(settings["tg_method_image"])
    tg_chat = bool(settings["tg_chat"])
    is_debug = bool(settings["is_debug"])

    # experimental way to send message to the group https://github.com/ableev/Zabbix-in-Telegram/issues/15
    if sys.argv[0].split("/")[-1] == "zbxtg_group.py":
        tg_chat = True

    if tg_chat:
        tg_contact_type = "group"
        tg_contact_type_old = "chat"

    if is_debug:
        log_file = tmp_dir + ".debug." + hash_ts + ".log"

    uid = None

    if os.path.isfile(tmp_uids):
        with open(tmp_uids, 'r') as cache_file_uids:
            cache_uids_old = cache_file_uids.readlines()

        for u in cache_uids_old:
            u_splitted = u.split(";")
            if zbx_to == u_splitted[0] and tg_contact_type == u_splitted[1]:
                uid = u_splitted[2]

        if not uid:
            for u in cache_uids_old:
                u_splitted = u.split(";")
                if zbx_to == u_splitted[0] and tg_contact_type_old == u_splitted[1]:
                    uid = u_splitted[2]
            if uid:
                tmp_update = True

    if not uid:
        tg_updates = tg_get_updates(proxies_tg, zbxtg_settings.tg_key)
        for m in tg_updates["result"]:
            chat = m["message"]["chat"]
            if chat["type"] == tg_contact_type == "private":
                if "username" in chat:
                    if chat["username"] == zbx_to:
                        uid = chat["id"]
            if chat["type"] == tg_contact_type == "group":
                if "title" in chat:
                    if chat["title"] == zbx_to:
                        uid = chat["id"]
        if uid:
            tmp_update = True

    if tmp_update:
        cache_string = "{0};{1};{2}\n".format(zbx_to, tg_contact_type, str(uid).rstrip())
        with open(tmp_uids, "a") as cache_file_uids:
            cache_file_uids.write(cache_string)

    if not uid:
        if tg_contact_type == "private":
            print("User '{0}' needs to send some text bot in private".format(zbx_to))
        if tg_contact_type == "chat":
            print("You need to mention your bot in '{0}' group chat (i.e. type @YourBot)".format(zbx_to))
        sys.exit(1)


    # add signature, turned off by default, you can turn it on in config
    try:
        if zbxtg_settings.zbx_tg_signature:
            zbxtg_body_text.append("--")
            zbxtg_body_text.append(zbxtg_settings.zbx_server)
    except:
        pass

    if not tg_method_image:
        tg_send_message(proxies_tg, zbxtg_settings.tg_key, uid, zbxtg_body_text)
    else:
        zbxtg_path_cache_img = tmp_dir + "/{0}.png".format(settings["zbxtg_itemid"])
        zbx_api_verify = True
        try:
            zbx_api_verify = zbxtg_settings.zbx_api_verify
        except:
            pass
        zbx_image = zbx_image_get(proxies_zbx, zbx_api_verify,
                                  zbxtg_settings.zbx_server, zbxtg_settings.zbx_api_user, zbxtg_settings.zbx_api_pass,
                                  settings["zbxtg_itemid"], settings["zbxtg_image_period"], settings["zbxtg_title"],
                                  settings["zbxtg_image_width"], settings["zbxtg_image_height"],
                                  zbxtg_path_cache_img)
        zbxtg_body_text, is_modified = list_cut(zbxtg_body_text, 200)
        if is_modified:
            print(zbxtg_settings.zbx_tg_prefix, "probably you will see MEDIA_CAPTION_TOO_LONG error, "
                                                "the message has been cut to 200 symbols, "
                                                "https://github.com/ableev/Zabbix-in-Telegram/issues/9"
                                                "#issuecomment-166895044")
        if tg_send_photo(proxies_tg, zbxtg_settings.tg_key, uid, zbxtg_body_text, zbxtg_path_cache_img):
            os.remove(zbxtg_path_cache_img)


if __name__ == "__main__":
    main()