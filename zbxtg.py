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


class TelegramAPI():
    tg_url_bot_general = "https://api.telegram.org/bot"

    def __init__(self, key, proxies):
        self.key = key
        self.proxies = proxies
        self.type = "private"  # 'private' for private chats or 'group' for group chats
        if len(sys.argv) > 4 and (sys.argv[4] == "private" or sys.argv[4] == "group"):
            self.type = sys.argv[4]

    def get_updates(self):
        url = self.tg_url_bot_general + self.key + "/getUpdates"
        res = requests.get(url, proxies=self.proxies)
        answer = res._content
        answer_json = json.loads(answer)
        if not answer_json["ok"]:
            print_message(answer_json)
            sys.exit(1)
        else:
            return answer_json

    def send_message(self, to, message):
        url = self.tg_url_bot_general + self.key + "/sendMessage"
        message = "\n".join(message)
        params = {"chat_id": to, "text": message, "parse_mode": "Markdown"}
        res = requests.post(url, params=params, proxies=self.proxies)
        answer = res._content
        answer_json = json.loads(answer)
        if not answer_json["ok"]:
            print_message(answer_json)
            sys.exit(1)
        else:
            return answer_json

    def send_photo(self, to, message, path):
        url = self.tg_url_bot_general + self.key + "/sendPhoto"
        message = "\n".join(message)
        params = {"chat_id": to, "caption": message}
        files = {"photo": open(path, 'rb')}
        res = requests.post(url, params=params, files=files, proxies=self.proxies)
        answer = res._content
        answer_json = json.loads(answer)
        if not answer_json["ok"]:
            print_message(answer_json)
            sys.exit(1)
        else:
            return answer_json

    def get_uid(self, name):
        uid = 0
        updates = self.get_updates()
        for m in updates["result"]:
            chat = m["message"]["chat"]
            if chat["type"] == self.type == "private":
                if "username" in chat:
                    if chat["username"] == name:
                        uid = chat["id"]
            if chat["type"] == self.type == "group":
                if "title" in chat:
                    if chat["title"] == name.decode("utf-8"):
                        uid = chat["id"]
        return uid

    def error_need_to_contact(self, to):
        if self.type == "private":
            print_message("User '{0}' needs to send some text bot in private".format(to))
        if self.type == "group":
            print_message("You need to mention your bot in '{0}' group chat (i.e. type @YourBot)".format(to))


class ZabbixAPI():
    def __init__(self, server, username, password, proxies, verify):
        self.server = server
        self.username = username
        self.password = password
        self.proxies = proxies
        self.verify = verify

        if not self.verify:
            requests.packages.urllib3.disable_warnings()

        data_api = {"name": self.username, "password": self.password, "enter": "Sign in"}
        req_cookie = requests.post(self.server + "/", data=data_api, proxies=self.proxies, verify=self.verify)
        cookie = req_cookie.cookies
        if len(req_cookie.history) > 1 and req_cookie.history[0].status_code == 302:
            print_message("probably the server in your config file has not full URL (for example "
                                                "'{0}' instead of '{1}')".format(self.server, self.server + "/zabbix"))
        if not cookie:
            print_message("authorization has failed, url: {0}".format(self.server + "/"))
            sys.exit(1)

        self.cookie = cookie

    def graph_get(self, itemid, period, title, width, height, tmp_dir):
        file = tmp_dir + "/{0}.png".format(itemid)

        zbx_img_url = self.server + "/chart3.php?period={1}&name={2}" \
                           "&width={3}&height={4}&graphtype=0&legend=1" \
                           "&items[0][itemid]={0}&items[0][sortorder]=0" \
                           "&items[0][drawtype]=5&items[0][color]=00CC00".format(itemid, period, title,
                                                                                 width, height)
        res = requests.get(zbx_img_url, cookies=self.cookie, proxies=self.proxies, verify=self.verify)
        res_code = res.status_code
        if res_code == 404:
            print_message("can't get image from '{0}'".format(zbx_img_url))
            sys.exit(1)
        res_img = res._content
        with open(file, 'wb') as fp:
            fp.write(res_img)
        return file

    def api_test(self):
        headers = {'Content-type': 'application/json'}
        api_data = json.dumps({"jsonrpc": "2.0","method": "user.login","params":
            {"user": self.username,"password": self.password},"id": 1})
        api_url = self.server + "/api_jsonrpc.php"
        api = requests.post(api_url, data=api_data, proxies=self.proxies, headers=headers)
        return api._content


def print_message(string):
    string = str(string) + "\n"
    filename = sys.argv[0].split("/")[-1]
    sys.stderr.write(filename + ": " + string)


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

    tg_contact_type_old = "user"

    proxies_tg = {}
    if zbxtg_settings.proxy_to_tg:
        proxies_tg = {"http": "http://{0}/".format(zbxtg_settings.proxy_to_tg)}

    tg = TelegramAPI(key=zbxtg_settings.tg_key, proxies=proxies_tg)

    zbx_api_verify = True
    try:
        zbx_api_verify = zbxtg_settings.zbx_api_verify
    except:
        pass
    proxies_zbx = {}
    if zbxtg_settings.proxy_to_zbx:
        proxies_zbx = {"http": "http://{0}/".format(zbxtg_settings.proxy_to_zbx)}

    zbx = ZabbixAPI(server=zbxtg_settings.zbx_server, username=zbxtg_settings.zbx_api_user,
                    password=zbxtg_settings.zbx_api_pass, proxies=proxies_zbx, verify=zbx_api_verify)

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
            setting = re.split("[\s\:\=]+", line, maxsplit=1)
            key = setting[0].replace(zbxtg_settings.zbx_tg_prefix + ";", "")
            if len(setting) > 1 and len(setting[1]) > 0:
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
        tg.type = "group"
        tg_contact_type_old = "chat"

    if is_debug:
        log_file = tmp_dir + ".debug." + hash_ts + ".log"

    uid = None

    if os.path.isfile(tmp_uids):
        with open(tmp_uids, 'r') as cache_file_uids:
            cache_uids_old = cache_file_uids.readlines()

        for u in cache_uids_old:
            u_splitted = u.split(";")
            if zbx_to == u_splitted[0] and tg.type == u_splitted[1]:
                uid = u_splitted[2]

        if not uid:
            for u in cache_uids_old:
                u_splitted = u.split(";")
                if zbx_to == u_splitted[0] and tg_contact_type_old == u_splitted[1]:
                    uid = u_splitted[2]
            if uid:
                tmp_update = True

    if not uid:
        uid = tg.get_uid(zbx_to)
        if uid:
            tmp_update = True

    if tmp_update:
        cache_string = "{0};{1};{2}\n".format(zbx_to, tg.type, str(uid).rstrip())
        with open(tmp_uids, "a") as cache_file_uids:
            cache_file_uids.write(cache_string)

    if not uid:
        tg.error_need_to_contact(zbx_to)
        sys.exit(1)


    # add signature, turned off by default, you can turn it on in config
    try:
        if zbxtg_settings.zbx_tg_signature:
            zbxtg_body_text.append("--")
            zbxtg_body_text.append(zbxtg_settings.zbx_server)
    except:
        pass

    if not tg_method_image:
        tg.send_message(uid, zbxtg_body_text)
    else:
        zbxtg_file_img = zbx.graph_get(settings["zbxtg_itemid"], settings["zbxtg_image_period"], settings["zbxtg_title"],
                                  settings["zbxtg_image_width"], settings["zbxtg_image_height"],
                                  tmp_dir)
        zbxtg_body_text, is_modified = list_cut(zbxtg_body_text, 200)
        if is_modified:
            print_message("probably you will see MEDIA_CAPTION_TOO_LONG error, "
                                                "the message has been cut to 200 symbols, "
                                                "https://github.com/ableev/Zabbix-in-Telegram/issues/9"
                                                "#issuecomment-166895044")
        if tg.send_photo(uid, zbxtg_body_text, zbxtg_file_img):
            os.remove(zbxtg_file_img)


if __name__ == "__main__":
    main()
