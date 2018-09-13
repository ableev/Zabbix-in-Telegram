#!/usr/bin/env python
# coding: utf-8

import sys
import os
import time
import random
import string
import requests
import json
import re
import stat
import hashlib
import subprocess
#import sqlite3
from os.path import dirname
import zbxtg_settings


class Cache:
    def __init__(self, database):
        self.database = database

    def create_db(self, database):
        pass


class TelegramAPI:
    tg_url_bot_general = "https://api.telegram.org/bot"

    def http_get(self, url):
        answer = requests.get(url, proxies=self.proxies)
        self.result = answer.json()
        self.ok_update()
        return self.result

    def __init__(self, key):
        self.debug = False
        self.key = key
        self.proxies = {}
        self.type = "private"  # 'private' for private chats or 'group' for group chats
        self.markdown = False
        self.html = False
        self.disable_web_page_preview = False
        self.disable_notification = False
        self.reply_to_message_id = 0
        self.tmp_dir = None
        self.tmp_uids = None
        self.location = {"latitude": None, "longitude": None}
        self.update_offset = 0
        self.image_buttons = False
        self.result = None
        self.ok = None
        self.error = None
        self.get_updates_from_file = False

    def get_me(self):
        url = self.tg_url_bot_general + self.key + "/getMe"
        me = self.http_get(url)
        return me

    def get_updates(self):
        url = self.tg_url_bot_general + self.key + "/getUpdates"
        params = {"offset": self.update_offset}
        if self.debug:
            print_message(url)
        answer = requests.post(url, params=params, proxies=self.proxies)
        self.result = answer.json()
        if self.get_updates_from_file:
            print_message("Getting updated from file getUpdates.txt")
            self.result = json.loads("".join(file_read("getUpdates.txt")))
        if self.debug:
            print_message("Content of /getUpdates:")
            print_message(json.dumps(self.result))
        self.ok_update()
        return self.result

    def send_message(self, to, message):
        url = self.tg_url_bot_general + self.key + "/sendMessage"
        message = "\n".join(message)
        params = {"chat_id": to, "text": message, "disable_web_page_preview": self.disable_web_page_preview,
                  "disable_notification": self.disable_notification}
        if self.reply_to_message_id:
            params["reply_to_message_id"] = self.reply_to_message_id
        if self.markdown or self.html:
            parse_mode = "HTML"
            if self.markdown:
                parse_mode = "Markdown"
            params["parse_mode"] = parse_mode
        if self.debug:
            print_message("Trying to /sendMessage:")
            print_message(url)
            print_message("post params: " + str(params))
        answer = requests.post(url, params=params, proxies=self.proxies)
        if answer.status_code == 414:
            self.result = {"ok": False, "description": "414 URI Too Long"}
        else:
            self.result = answer.json()
        self.ok_update()
        return self.result

    def update_message(self, to, message_id, message):
        url = self.tg_url_bot_general + self.key + "/editMessageText"
        message = "\n".join(message)
        params = {"chat_id": to, "message_id": message_id, "text": message,
                  "disable_web_page_preview": self.disable_web_page_preview,
                  "disable_notification": self.disable_notification}
        if self.markdown or self.html:
            parse_mode = "HTML"
            if self.markdown:
                parse_mode = "Markdown"
            params["parse_mode"] = parse_mode
        if self.debug:
            print_message("Trying to /editMessageText:")
            print_message(url)
            print_message("post params: " + str(params))
        answer = requests.post(url, params=params, proxies=self.proxies)
        self.result = answer.json()
        self.ok_update()
        return self.result

    def send_photo(self, to, message, path):
        url = self.tg_url_bot_general + self.key + "/sendPhoto"
        message = "\n".join(message)
        if self.image_buttons:
            reply_markup = json.dumps({"inline_keyboard": [[
                {"text": "R", "callback_data": "graph_refresh"},
                {"text": "1h", "callback_data": "graph_period_3600"},
                {"text": "3h", "callback_data": "graph_period_10800"},
                {"text": "6h", "callback_data": "graph_period_21600"},
                {"text": "12h", "callback_data": "graph_period_43200"},
                {"text": "24h", "callback_data": "graph_period_86400"},
            ], ]})
        else:
            reply_markup = json.dumps({})
        params = {"chat_id": to, "caption": message, "disable_notification": self.disable_notification,
                  "reply_markup": reply_markup}
        if self.reply_to_message_id:
            params["reply_to_message_id"] = self.reply_to_message_id
        files = {"photo": open(path, 'rb')}
        if self.debug:
            print_message("Trying to /sendPhoto:")
            print_message(url)
            print_message(params)
            print_message("files: " + str(files))
        answer = requests.post(url, params=params, files=files, proxies=self.proxies)
        self.result = answer.json()
        self.ok_update()
        return self.result

    def send_txt(self, to, text, text_name=None):
        path = self.tmp_dir + "/" + "zbxtg_txt_"
        url = self.tg_url_bot_general + self.key + "/sendDocument"
        text = "\n".join(text)
        if not text_name:
            path += "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
        else:
            path += text_name
        path += ".txt"
        file_write(path, text)
        params = {"chat_id": to, "caption": path.split("/")[-1], "disable_notification": self.disable_notification}
        if self.reply_to_message_id:
            params["reply_to_message_id"] = self.reply_to_message_id
        files = {"document": open(path, 'rb')}
        if self.debug:
            print_message("Trying to /sendDocument:")
            print_message(url)
            print_message(params)
            print_message("files: " + str(files))
        answer = requests.post(url, params=params, files=files, proxies=self.proxies)
        self.result = answer.json()
        self.ok_update()
        return self.result

    def get_uid(self, name):
        uid = 0
        if self.debug:
            print_message("Getting uid from /getUpdates...")
        updates = self.get_updates()
        for m in updates["result"]:
            if "message" in m:
                chat = m["message"]["chat"]
            elif "edited_message" in m:
                chat = m["edited_message"]["chat"]
            else:
                continue
            if chat["type"] == self.type == "private":
                if "username" in chat:
                    if chat["username"] == name:
                        uid = chat["id"]
            if (chat["type"] == "group" or chat["type"] == "supergroup") and self.type == "group":
                if "title" in chat:
                    if sys.version_info[0] < 3:
                        if chat["title"] == name.decode("utf-8"):
                            uid = chat["id"]
                    else:
                        if chat["title"] == name:
                            uid = chat["id"]
        return uid

    def error_need_to_contact(self, to):
        if self.type == "private":
            print_message("User '{0}' needs to send some text bot in private".format(to))
        if self.type == "group":
            print_message("You need start a conversation with your bot first in '{0}' group chat, type '/start@{1}'"
                          .format(to, self.get_me()["result"]["username"]))

    def update_cache_uid(self, name, uid, message="Add new string to cache file"):
        cache_string = "{0};{1};{2}\n".format(name, self.type, str(uid).rstrip())
        # FIXME
        if self.debug:
            print_message("{0}: {1}".format(message, cache_string))
        with open(self.tmp_uids, "a") as cache_file_uids:
            cache_file_uids.write(cache_string)
        return True

    def get_uid_from_cache(self, name):
        if self.debug:
            print_message("Trying to read cached uid for {0}, {1}, from {2}".format(name, self.type, self.tmp_uids))
        uid = 0
        if os.path.isfile(self.tmp_uids):
            with open(self.tmp_uids, 'r') as cache_file_uids:
                cache_uids_old = cache_file_uids.readlines()
            for u in cache_uids_old:
                u_splitted = u.split(";")
                if name == u_splitted[0] and self.type == u_splitted[1]:
                    uid = u_splitted[2]
        return uid

    def send_location(self, to, coordinates):
        url = self.tg_url_bot_general + self.key + "/sendLocation"
        params = {"chat_id": to, "disable_notification": self.disable_notification,
                  "latitude": coordinates["latitude"], "longitude": coordinates["longitude"]}
        if self.reply_to_message_id:
            params["reply_to_message_id"] = self.reply_to_message_id
        if self.debug:
            print_message("Trying to /sendLocation:")
            print_message(url)
            print_message("post params: " + str(params))
        answer = requests.post(url, params=params, proxies=self.proxies)
        self.result = answer.json()
        self.ok_update()
        return self.result

    def answer_callback_query(self, callback_query_id, text=None):
        url = self.tg_url_bot_general + self.key + "/answerCallbackQuery"
        if not text:
            params = {"callback_query_id": callback_query_id}
        else:
            params = {"callback_query_id": callback_query_id, "text": text}
        answer = requests.post(url, params=params, proxies=self.proxies)
        self.result = answer.json()
        self.ok_update()
        return self.result

    def ok_update(self):
        self.ok = self.result["ok"]
        if self.ok:
            self.error = None
        else:
            self.error = self.result["description"]
            print_message(self.error)
        return True


def markdown_fix(message, offset):
    offset = int(offset)
    message = "\n".join(message)
    message = message[:offset] + message[offset+1:]
    message = message.split("\n")
    return message


class ZabbixWeb:
    def __init__(self, server, username, password):
        self.debug = False
        self.server = server
        self.username = username
        self.password = password
        self.proxies = {}
        self.verify = True
        self.cookie = None
        self.basic_auth_user = None
        self.basic_auth_pass = None
        self.tmp_dir = None

    def login(self):
        if not self.verify:
            requests.packages.urllib3.disable_warnings()

        data_api = {"name": self.username, "password": self.password, "enter": "Sign in"}
        answer = requests.post(self.server + "/", data=data_api, proxies=self.proxies, verify=self.verify,
                               auth=requests.auth.HTTPBasicAuth(self.basic_auth_user, self.basic_auth_pass))
        cookie = answer.cookies
        if len(answer.history) > 1 and answer.history[0].status_code == 302:
            print_message("probably the server in your config file has not full URL (for example "
                          "'{0}' instead of '{1}')".format(self.server, self.server + "/zabbix"))
        if not cookie:
            print_message("authorization has failed, url: {0}".format(self.server + "/"))
            cookie = None

        self.cookie = cookie

    def graph_get(self, itemid, period, title, width, height):
        file_img = self.tmp_dir + "/{0}.png".format("".join(itemid))

        title = requests.utils.quote(title)

        colors = {
            0: "00CC00",
            1: "CC0000",
            2: "0000CC",
            3: "CCCC00",
            4: "00CCCC",
            5: "CC00CC",
        }

        drawtype = 5
        if len(itemid) > 1:
            drawtype = 2

        zbx_img_url_itemids = []
        for i in range(0, len(itemid)):
            itemid_url = "&items[{0}][itemid]={1}&items[{0}][sortorder]={0}&" \
                         "items[{0}][drawtype]={3}&items[{0}][color]={2}".format(i, itemid[i], colors[i], drawtype)
            zbx_img_url_itemids.append(itemid_url)

        zbx_img_url = self.server + "/chart3.php?period={0}&name={1}" \
                                    "&width={2}&height={3}&graphtype=0&legend=1".format(period, title, width, height)
        zbx_img_url += "".join(zbx_img_url_itemids)

        if self.debug:
            print_message(zbx_img_url)
        answer = requests.get(zbx_img_url, cookies=self.cookie, proxies=self.proxies, verify=self.verify,
                              auth=requests.auth.HTTPBasicAuth(self.basic_auth_user, self.basic_auth_pass))
        status_code = answer.status_code
        if status_code == 404:
            print_message("can't get image from '{0}'".format(zbx_img_url))
            return False
        res_img = answer.content
        with open(file_img, 'wb') as fp:
            fp.write(res_img)
        return file_img

    def api_test(self):
        headers = {'Content-type': 'application/json'}
        api_data = json.dumps({"jsonrpc": "2.0", "method": "user.login", "params":
                              {"user": self.username, "password": self.password}, "id": 1})
        api_url = self.server + "/api_jsonrpc.php"
        api = requests.post(api_url, data=api_data, proxies=self.proxies, headers=headers)
        return api.text


def print_message(message):
    message = str(message) + "\n"
    filename = sys.argv[0].split("/")[-1]
    sys.stderr.write(filename + ": " + message)


def list_cut(elements, symbols_limit):
    symbols_count = symbols_count_now = 0
    elements_new = []
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


class Maps:
    # https://developers.google.com/maps/documentation/geocoding/intro
    def __init__(self):
        self.key = None
        self.proxies = {}

    def get_coordinates_by_address(self, address):
        coordinates = {"latitude": 0, "longitude": 0}
        url_api = "https://maps.googleapis.com/maps/api/geocode/json?key={0}&address={1}".format(self.key, address)
        url = url_api
        answer = requests.get(url, proxies=self.proxies)
        result = answer.json()
        try:
            coordinates_dict = result["results"][0]["geometry"]["location"]
        except:
            if "error_message" in result:
                print_message("[" + result["status"] + "]: " + result["error_message"])
            return coordinates
        coordinates = {"latitude": coordinates_dict["lat"], "longitude": coordinates_dict["lng"]}
        return coordinates


def file_write(filename, text):
    with open(filename, "w") as fd:
        fd.write(str(text))
    return True


def file_read(filename):
    with open(filename, "r") as fd:
        text = fd.readlines()
    return text


def file_append(filename, text):
    with open(filename, "a") as fd:
        fd.write(str(text))
    return True


def external_image_get(url, tmp_dir, timeout=6):
    image_hash = hashlib.md5()
    image_hash.update(url)
    file_img = tmp_dir + "/external_{0}.png".format(image_hash.hexdigest())
    try:
        answer = requests.get(url, timeout=timeout)
    except requests.exceptions.ReadTimeout as ex:
        print_message("Can't get external image from '{0}': timeout".format(url))
        return False
    status_code = answer.status_code
    if status_code == 404:
        print_message("Can't get external image from '{0}': HTTP 404 error".format(url))
        return False
    answer_image = answer.content
    file_write(file_img, answer_image)
    return file_img


def age2sec(age_str):
    age_sec = 0
    age_regex = "([0-9]+d)?\s?([0-9]+h)?\s?([0-9]+m)?"
    age_pattern = re.compile(age_regex)
    intervals = age_pattern.match(age_str).groups()
    for i in intervals:
        if i:
            metric = i[-1]
            if metric == "d":
                age_sec += int(i[0:-1])*86400
            if metric == "h":
                age_sec += int(i[0:-1])*3600
            if metric == "m":
                age_sec += int(i[0:-1])*60
    return age_sec


def main():

    tmp_dir = zbxtg_settings.zbx_tg_tmp_dir
    if tmp_dir == "/tmp/" + zbxtg_settings.zbx_tg_prefix:
        print_message("WARNING: it is strongly recommended to change `zbx_tg_tmp_dir` variable in config!!!")
        print_message("https://github.com/ableev/Zabbix-in-Telegram/wiki/Change-zbx_tg_tmp_dir-in-settings")

    tmp_cookie = tmp_dir + "/cookie.py.txt"
    tmp_uids = tmp_dir + "/uids.txt"
    tmp_need_update = False  # do we need to update cache file with uids or not

    rnd = random.randint(0, 999)
    ts = time.time()
    hash_ts = str(ts) + "." + str(rnd)

    log_file = "/dev/null"

    args = sys.argv

    settings = {
        "zbxtg_itemid": "0",  # itemid for graph
        "zbxtg_title": None,  # title for graph
        "zbxtg_image_period": None,
        "zbxtg_image_age": "3600",
        "zbxtg_image_width": "900",
        "zbxtg_image_height": "200",
        "tg_method_image": False,  # if True - default send images, False - send text
        "tg_chat": False,  # send message to chat or in private
        "tg_group": False,  # send message to chat or in private
        "is_debug": False,
        "is_channel": False,
        "disable_web_page_preview": False,
        "location": None,  # address
        "lat": 0,  # latitude
        "lon": 0,  # longitude
        "is_single_message": False,
        "markdown": False,
        "html": False,
        "signature": False,
        "signature_disable": False,
        "graph_buttons": False,
        "extimg": None,
        "to": None,
        "to_group": None,
        "forked": False,
    }

    url_github = "https://github.com/ableev/Zabbix-in-Telegram"
    url_wiki_base = "https://github.com/ableev/Zabbix-in-Telegram/wiki"
    url_tg_group = "https://t.me/ZbxTg"
    url_tg_channel = "https://t.me/Zabbix_in_Telegram"

    settings_description = {
        "itemid": {"name": "zbxtg_itemid", "type": "list",
                   "help": "script will attach a graph with that itemid (could be multiple)", "url": "Graphs"},
        "title": {"name": "zbxtg_title", "type": "str", "help": "title for attached graph", "url": "Graphs"},
        "graphs_period": {"name": "zbxtg_image_period", "type": "int", "help": "graph period", "url": "Graphs"},
        "graphs_age": {"name": "zbxtg_image_age", "type": "str", "help": "graph period as age", "url": "Graphs"},
        "graphs_width": {"name": "zbxtg_image_width", "type": "int", "help": "graph width", "url": "Graphs"},
        "graphs_height": {"name": "zbxtg_image_height", "type": "int", "help": "graph height", "url": "Graphs"},
        "graphs": {"name": "tg_method_image", "type": "bool", "help": "enables graph sending", "url": "Graphs"},
        "chat": {"name": "tg_chat", "type": "bool", "help": "deprecated, don't use it, see 'group'",
                 "url": "How-to-send-message-to-the-group-chat"},
        "group": {"name": "tg_group", "type": "bool", "help": "sends message to a group",
                  "url": "How-to-send-message-to-the-group-chat"},
        "debug": {"name": "is_debug", "type": "bool", "help": "enables 'debug'",
                  "url": "How-to-test-script-in-command-line"},
        "channel": {"name": "is_channel", "type": "bool", "help": "sends message to a channel",
                    "url": "Channel-support"},
        "disable_web_page_preview": {"name": "disable_web_page_preview", "type": "bool",
                                     "help": "disable web page preview", "url": "Disable-web-page-preview"},
        "location": {"name": "location", "type": "str", "help": "address of location", "url": "Location"},
        "lat": {"name": "lat", "type": "str", "help": "specify latitude (and lon too!)", "url": "Location"},
        "lon": {"name": "lon", "type": "str", "help": "specify longitude (and lat too!)", "url": "Location"},
        "single_message": {"name": "is_single_message", "type": "bool", "help": "do not split message and graph",
                           "url": "Why-am-I-getting-two-messages-instead-of-one"},
        "markdown": {"name": "markdown", "type": "bool", "help": "markdown support", "url": "Markdown-and-HTML"},
        "html": {"name": "html", "type": "bool", "help": "markdown support", "url": "Markdown-and-HTML"},
        "signature": {"name": "signature", "type": "bool",
                      "help": "bot's signature", "url": "Bot-signature"},
        "signature_disable": {"name": "signature_disable", "type": "bool",
                              "help": "enables/disables bot's signature", "url": "Bot-signature"},
        "graph_buttons": {"name": "graph_buttons", "type": "bool",
                          "help": "activates buttons under graph, could be using in ZbxTgDaemon",
                          "url": "Interactive-bot"},
        "external_image": {"name": "extimg", "type": "str",
                           "help": "should be url; attaches external image from different source",
                           "url": "External-image-as-graph"},
        "to": {"name": "to", "type": "str", "help": "rewrite zabbix username, use that instead of arguments",
               "url": "Custom-to-and-to_group"},
        "to_group": {"name": "to_group", "type": "str",
                     "help": "rewrite zabbix username, use that instead of arguments", "url": "Custom-to-and-to_group"},
        "forked": {"name": "forked", "type": "bool", "help": "internal variable, do not use it. Ever.", "url": ""},
    }

    if len(args) < 4:
        do_not_exit = False
        if "--features" in args:
            print(("List of available settings, see {0}/Settings\n---".format(url_wiki_base)))
            for sett, proprt in list(settings_description.items()):
                print(("{0}: {1}\ndoc: {2}/{3}\n--".format(sett, proprt["help"], url_wiki_base, proprt["url"])))

        elif "--show-settings" in args:
            do_not_exit = True
            print_message("Settings: " + str(json.dumps(settings, indent=2)))

        else:
            print(("Hi. You should provide at least three arguments.\n"
                  "1. Read main page and/or wiki: {0} + {1}\n"
                  "2. Public Telegram group (discussion): {2}\n"
                  "3. Public Telegram channel: {3}\n"
                  "4. Try dev branch for test purposes (new features, etc): {0}/tree/dev"
                  .format(url_github, url_wiki_base, url_tg_group, url_tg_channel)))
        if not do_not_exit:
            sys.exit(0)


    zbx_to = args[1]
    zbx_subject = args[2]
    zbx_body = args[3]

    tg = TelegramAPI(key=zbxtg_settings.tg_key)

    tg.tmp_dir = tmp_dir
    tg.tmp_uids = tmp_uids

    if zbxtg_settings.proxy_to_tg:
        proxy_to_tg = zbxtg_settings.proxy_to_tg
        if not proxy_to_tg.find("http") and not proxy_to_tg.find("socks"):
            proxy_to_tg = "https://" + proxy_to_tg
        tg.proxies = {
            "https": "{0}".format(zbxtg_settings.proxy_to_tg),
        }

    zbx = ZabbixWeb(server=zbxtg_settings.zbx_server, username=zbxtg_settings.zbx_api_user,
                    password=zbxtg_settings.zbx_api_pass)

    zbx.tmp_dir = tmp_dir

    if zbxtg_settings.proxy_to_zbx:
        zbx.proxies = {
            "http": "http://{0}/".format(zbxtg_settings.proxy_to_zbx),
            "https": "https://{0}/".format(zbxtg_settings.proxy_to_zbx)
        }

    # https://github.com/ableev/Zabbix-in-Telegram/issues/55
    try:
        if zbxtg_settings.zbx_basic_auth:
            zbx.basic_auth_user = zbxtg_settings.zbx_basic_auth_user
            zbx.basic_auth_pass = zbxtg_settings.zbx_basic_auth_pass
    except:
        pass

    try:
        zbx_api_verify = zbxtg_settings.zbx_api_verify
        zbx.verify = zbx_api_verify
    except:
        pass

    map = Maps()
    # api key to resolve address to coordinates via google api
    try:
        if zbxtg_settings.google_maps_api_key:
            map.key = zbxtg_settings.google_maps_api_key
        if zbxtg_settings.proxy_to_tg:
            map.proxies = {
                "http": "http://{0}/".format(zbxtg_settings.proxy_to_tg),
                "https": "https://{0}/".format(zbxtg_settings.proxy_to_tg)
            }
    except:
        pass

    zbxtg_body = (zbx_subject + "\n" + zbx_body).splitlines()
    zbxtg_body_text = []

    for line in zbxtg_body:
        if line.find(zbxtg_settings.zbx_tg_prefix) > -1:
            setting = re.split("[\s:=]+", line, maxsplit=1)
            key = setting[0].replace(zbxtg_settings.zbx_tg_prefix + ";", "")
            if key not in settings_description:
                if "--debug" in args:
                    print_message("[ERROR] There is no '{0}' method, use --features to get help")
                continue
            if settings_description[key]["type"] == "list":
                value = setting[1].split(",")
            elif len(setting) > 1 and len(setting[1]) > 0:
                value = setting[1]
            elif settings_description[key]["type"] == "bool":
                value = True
            else:
                value = settings[settings_description[key]["name"]]
            if key in settings_description:
                settings[settings_description[key]["name"]] = value
        else:
            zbxtg_body_text.append(line)

    tg_method_image = bool(settings["tg_method_image"])
    tg_chat = bool(settings["tg_chat"])
    tg_group = bool(settings["tg_group"])
    is_debug = bool(settings["is_debug"])
    is_channel = bool(settings["is_channel"])
    disable_web_page_preview = bool(settings["disable_web_page_preview"])
    is_single_message = bool(settings["is_single_message"])

    # experimental way to send message to the group https://github.com/ableev/Zabbix-in-Telegram/issues/15
    if args[0].split("/")[-1] == "zbxtg_group.py" or "--group" in args or tg_chat or tg_group:
        tg_chat = True
        tg_group = True
        tg.type = "group"

    if "--debug" in args or is_debug:
        is_debug = True
        tg.debug = True
        zbx.debug = True
        print_message(tg.get_me())
        print_message("Cache file with uids: " + tg.tmp_uids)
        log_file = tmp_dir + ".debug." + hash_ts + ".log"
        #print_message(log_file)

    if "--markdown" in args or settings["markdown"]:
        tg.markdown = True

    if "--html" in args or settings["html"]:
        tg.html = True

    if "--channel" in args or is_channel:
        tg.type = "channel"

    if "--disable_web_page_preview" in args or disable_web_page_preview:
        if is_debug:
            print_message("'disable_web_page_preview' option has been enabled")
        tg.disable_web_page_preview = True

    if "--graph_buttons" in args or settings["graph_buttons"]:
        tg.image_buttons = True

    if "--forked" in args:
        settings["forked"] = True

    location_coordinates = {"latitude": None, "longitude": None}
    if settings["lat"] > 0 and settings["lat"] > 0:
        location_coordinates = {"latitude": settings["lat"], "longitude": settings["lon"]}
        tg.location = location_coordinates
    else:
        if settings["location"]:
            location_coordinates = map.get_coordinates_by_address(settings["location"])
            if location_coordinates:
                settings["lat"] = location_coordinates["latitude"]
                settings["lon"] = location_coordinates["longitude"]
                tg.location = location_coordinates

    if not os.path.isdir(tmp_dir):
        if is_debug:
            print_message("Tmp dir doesn't exist, creating new one...")
        try:
            os.makedirs(tmp_dir)
            open(tg.tmp_uids, "a").close()
            os.chmod(tmp_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            os.chmod(tg.tmp_uids, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except:
            tmp_dir = "/tmp"
        if is_debug:
            print_message("Using {0} as a temporary dir".format(tmp_dir))

    done_all_work_in_the_fork = False
    # issue75

    to_types = ["to", "to_group", "to_channel"]
    to_types_to_telegram = {"to": "private", "to_group": "group", "to_channel": "channel"}
    multiple_to = {}
    for i in to_types:
        multiple_to[i]=[]

    for t in to_types:
        try:
            if settings[t] and not settings["forked"]:
                # zbx_to = settings["to"]
                multiple_to[t] = re.split(",", settings[t])
        except KeyError:
            pass

    # example:
    # {'to_channel': [], 'to': ['usr1', 'usr2', 'usr3'], 'to_group': []}

    if (sum([len(v) for k, v in list(multiple_to.items())])) == 1:
        # if we have only one recipient, we don't need fork to send message, just re-write "to" vaiable
        tmp_max = 0
        for t in to_types:
            if len(multiple_to[t]) > tmp_max:
                tmp_max = len(multiple_to[t])
                tg.type = to_types_to_telegram[t]
                zbx_to = multiple_to[t][0]
    else:
        for t in to_types:
            for i in multiple_to[t]:
                args_new = list(args)
                args_new[1] = i
                if t == "to_group":
                    args_new.append("--group")
                args_new.append("--forked")
                args_new.insert(0, sys.executable)
                if is_debug:
                    print_message("Fork for custom recipient ({1}), new args: {0}".format(args_new,
                                                                                          to_types_to_telegram[t]))
                subprocess.call(args_new)
                done_all_work_in_the_fork = True

    if done_all_work_in_the_fork:
        sys.exit(0)

    uid = None

    if tg.type == "channel":
        uid = zbx_to
    if tg.type == "private":
        zbx_to = zbx_to.replace("@", "")

    if zbx_to.isdigit():
        uid = zbx_to

    if not uid:
        uid = tg.get_uid_from_cache(zbx_to)

    if not uid:
        uid = tg.get_uid(zbx_to)
        if uid:
            tmp_need_update = True
    if not uid:
        tg.error_need_to_contact(zbx_to)
        sys.exit(1)

    if tmp_need_update:
        tg.update_cache_uid(zbx_to, str(uid).rstrip())

    if is_debug:
        print_message("Telegram uid of {0} '{1}': {2}".format(tg.type, zbx_to, uid))

    # add signature, turned off by default, you can turn it on in config
    try:
        if "--signature" in args or settings["signature"] or zbxtg_settings.zbx_tg_signature\
                and not "--signature_disable" in args and not settings["signature_disable"]:
            zbxtg_body_text.append("--")
            zbxtg_body_text.append(zbxtg_settings.zbx_server)
    except:
        pass

    # replace text with emojis
    if hasattr(zbxtg_settings, "emoji_map"):
        zbxtg_body_text_emoji_support = []
        for l in zbxtg_body_text:
            l_new = l
            for k, v in list(zbxtg_settings.emoji_map.items()):
                l_new = l_new.replace("{{" + k + "}}", v)
            zbxtg_body_text_emoji_support.append(l_new)
        zbxtg_body_text = zbxtg_body_text_emoji_support

    if not is_single_message:
        tg.send_message(uid, zbxtg_body_text)
        if not tg.ok:
            # first case – if group has been migrated to a supergroup, we need to update chat_id of that group
            if tg.error.find("migrated") > -1 and tg.error.find("supergroup") > -1:
                migrate_to_chat_id = tg.result["parameters"]["migrate_to_chat_id"]
                tg.update_cache_uid(zbx_to, migrate_to_chat_id, message="Group chat is migrated to supergroup, "
                                                                        "updating cache file")
                uid = migrate_to_chat_id
                tg.send_message(uid, zbxtg_body_text)

            # another case if markdown is enabled and we got parse error, try to remove "bad" symbols from message
            if tg.markdown and tg.error.find("Can't find end of the entity starting at byte offset") > -1:
                markdown_fix_attempts = 0
                while not tg.ok and markdown_fix_attempts != 10:
                    offset = re.search("Can't find end of the entity starting at byte offset ([0-9]+)", tg.error).group(1)
                    zbxtg_body_text = markdown_fix(zbxtg_body_text, offset)
                    tg.send_message(uid, zbxtg_body_text)
                    markdown_fix_attempts += 1
                if tg.ok:
                    print_message("Original message has been fixed due to {0}"
                                  .format(url_wiki_base + "/" + settings_description["markdown"]["url"]))

    if is_debug:
        print((tg.result))

    if settings["zbxtg_image_age"]:
        age_sec = age2sec(settings["zbxtg_image_age"])
        if age_sec > 0 and age_sec > 3600:
            settings["zbxtg_image_period"] = age_sec

    message_id = 0
    if tg_method_image:
        zbx.login()
        if not zbx.cookie:
            text_warn = "Login to Zabbix web UI has failed (web url, user or password are incorrect), "\
                        "unable to send graphs check manually"
            tg.send_message(uid, [text_warn])
            print_message(text_warn)
        else:
            if not settings["extimg"]:
                zbxtg_file_img = zbx.graph_get(settings["zbxtg_itemid"], settings["zbxtg_image_period"],
                                               settings["zbxtg_title"], settings["zbxtg_image_width"],
                                               settings["zbxtg_image_height"])
            else:
                zbxtg_file_img = external_image_get(settings["extimg"], tmp_dir=zbx.tmp_dir)
            zbxtg_body_text, is_modified = list_cut(zbxtg_body_text, 200)
            if tg.ok:
                message_id = tg.result["result"]["message_id"]
            tg.reply_to_message_id = message_id
            if not zbxtg_file_img:
                text_warn = "Can't get graph image, check script manually, see logs, or disable graphs"
                tg.send_message(uid, [text_warn])
                print_message(text_warn)
            else:
                if not is_single_message:
                    zbxtg_body_text = ""
                else:
                    if is_modified:
                        text_warn = "probably you will see MEDIA_CAPTION_TOO_LONG error, "\
                                    "the message has been cut to 200 symbols, "\
                                    "https://github.com/ableev/Zabbix-in-Telegram/issues/9"\
                                    "#issuecomment-166895044"
                        print_message(text_warn)
                if not is_single_message:
                    tg.disable_notification = True
                tg.send_photo(uid, zbxtg_body_text, zbxtg_file_img)
                if tg.ok:
                    settings["zbxtg_body_text"] = zbxtg_body_text
                    os.remove(zbxtg_file_img)
                else:
                    if tg.error.find("PHOTO_INVALID_DIMENSIONS") > -1:
                        if not tg.disable_web_page_preview:
                            tg.disable_web_page_preview = True
                        text_warn = "Zabbix user couldn't get graph (probably has no rights to get data from host), " \
                                    "check script manually, see {0}".format(url_wiki_base + "/" +
                                                                            settings_description["graphs"]["url"])
                        tg.send_message(uid, [text_warn])
                        print_message(text_warn)
    if tg.location and location_coordinates["latitude"] and location_coordinates["longitude"]:
        tg.reply_to_message_id = message_id
        tg.disable_notification = True
        tg.send_location(to=uid, coordinates=location_coordinates)

    if "--show-settings" in args:
        print_message("Settings: " + str(json.dumps(settings, indent=2)))

if __name__ == "__main__":
    main()
