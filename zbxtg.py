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
    params = {"chat_id": to, "text": message}
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
    file = path.split("/")[-1]
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


def zbx_image_get(proxies, api_server, api_user, api_pass, itemid, period, title, file):
    data_api = {"name": api_user, "password": api_pass, "enter": "Sign in"}
    zbx_img_url = api_server + "/chart3.php?period={1}&name={2}" \
                               "&width=900&height=200&graphtype=0&legend=1" \
                               "&items[0][itemid]={0}&items[0][sortorder]=0" \
                               "&items[0][drawtype]=5&items[0][color]=00CC00".format(itemid, period, title)

    cookie = requests.post(api_server + "/", data=data_api, proxies=proxies).cookies
    if not cookie:
        print(zbxtg_settings.zbx_tg_prefix + " authorization has failed")
        sys.exit(1)
    res = requests.get(zbx_img_url, cookies=cookie, proxies=proxies)
    res_img = res._content
    with open(file, 'wb') as fp:
        fp.write(res_img)

    return True


def main():

    is_debug = False

    tmp_dir = "/tmp/" + zbxtg_settings.zbx_tg_prefix

    if not os.path.isdir(tmp_dir):
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

    tg_chat = False  # send message to chat or in private
    tg_contact_type = "private"
    tg_contact_type_old = "user"
    tg_method = "text"  # by default send text

    proxies_tg = {}
    if zbxtg_settings.proxy_to_tg:
        proxies_tg = {"http": "http://{0}/".format(zbxtg_settings.proxy_to_tg)}
    proxies_zbx = {}
    if zbxtg_settings.proxy_to_zbx:
        proxies_zbx = {"http": "http://{0}/".format(zbxtg_settings.proxy_to_zbx)}

    zbxtg_image_period = 3600  # default for graph
    zbxtg_itemid = 0  # itemid for graph
    zbxtg_title = None  # title for graph

    if zbx_body.find(zbxtg_settings.zbx_tg_prefix + ";graphs") > -1:
        tg_method = "image"
    if zbx_body.find(zbxtg_settings.zbx_tg_prefix + ";chat") > -1:
        tg_chat = True
    if zbx_body.find(zbxtg_settings.zbx_tg_prefix + ";debug") > -1:
        is_debug = True
    if zbx_body.find(zbxtg_settings.zbx_tg_prefix + ";debug") > -1:
        is_debug = True

    if tg_chat:
        tg_contact_type = "group"
        tg_contact_type_old = "chat"

    if is_debug:
        log_file = tmp_dir + "debug." + hash_ts + ".log"

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
                if chat["username"] == zbx_to:
                    uid = chat["id"]
            if chat["type"] == tg_contact_type == "group":
                if chat["title"] == zbx_to:
                    uid = chat["id"]
        if uid:
            tmp_update = True

    if tmp_update:
        cache_string = "{0};{1};{2}".format(zbx_to, tg_contact_type, uid)
        with open(tmp_uids, "a") as cache_file_uids:
            cache_file_uids.write(cache_string)

    if not uid:
        if tg_contact_type == "private":
            print("User '{0}' needs to send some text bot in private".format(zbx_to))
        if tg_contact_type == "chat":
            print("You need to mention your bot in '{0}' group chat (i.e. type @YourBot)".format(zbx_to))
        sys.exit(1)

    zbxtg_body = zbx_body.splitlines()
    zbxtg_body_text = []

    for l in zbxtg_body:
        if l.find(zbxtg_settings.zbx_tg_prefix) > -1:
            m0 = re.match(zbxtg_settings.zbx_tg_prefix + ";itemid(:|\ )+(\d+)", l)
            if m0:
                zbxtg_itemid = m0.group(2)

            m1 = re.match(zbxtg_settings.zbx_tg_prefix + ";title:(.*)", l)
            if m1:
                zbxtg_title = m1.group(1)

            m2 = re.match(zbxtg_settings.zbx_tg_prefix + ";graphs_period(:|\ )+(\d+)", l)
            if m2:
                zbxtg_image_period = m2.group(2)
        else:
            zbxtg_body_text.append(l)

    if tg_method == "text":
        tg_send_message(proxies_tg, zbxtg_settings.tg_key, uid, zbxtg_body_text)
    elif tg_method == "image":
        zbxtg_path_cache_img = tmp_dir + "/{0}.png".format(zbxtg_itemid)
        zbx_image = zbx_image_get(proxies_zbx, zbxtg_settings.zbx_server, zbxtg_settings.zbx_api_user, zbxtg_settings.zbx_api_pass,
                                  zbxtg_itemid, zbxtg_image_period, zbxtg_title, zbxtg_path_cache_img)
        if tg_send_photo(proxies_tg, zbxtg_settings.tg_key, uid, zbxtg_body_text, zbxtg_path_cache_img):
            os.remove(zbxtg_path_cache_img)


if __name__ == "__main__":
    main()