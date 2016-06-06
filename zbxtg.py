#!/usr/bin/env python
# coding: utf-8

import sys
import os
import time
import random
import requests
import json
import re
import stat
from os.path import dirname
import zbxtg_settings


class TelegramAPI():
    tg_url_bot_general = "https://api.telegram.org/bot"

    def http_get(self, url):
        res = requests.get(url, proxies=self.proxies)
        answer = res.text
        answer_json = json.loads(answer.decode('utf8'))
        return answer_json

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
        self.tmp_uids = None

    def get_me(self):
        url = self.tg_url_bot_general + self.key + "/getMe"
        me = self.http_get(url)
        return me

    def get_updates(self):
        url = self.tg_url_bot_general + self.key + "/getUpdates"
        if self.debug:
            print_message(url)
        updates = self.http_get(url)
        if self.debug:
            print_message("Content of /getUpdates:")
            print_message(updates)
        if not updates["ok"]:
            print_message(updates)
            return updates
        else:
            return updates

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
        res = requests.post(url, params=params, proxies=self.proxies)
        answer = res.text
        answer_json = json.loads(answer.decode('utf8'))
        if not answer_json["ok"]:
            print_message(answer_json)
            return answer_json
        else:
            return answer_json

    def send_photo(self, to, message, path):
        url = self.tg_url_bot_general + self.key + "/sendPhoto"
        message = "\n".join(message)
        params = {"chat_id": to, "caption": message, "disable_notification": self.disable_notification}
        if self.reply_to_message_id:
            params["reply_to_message_id"] = self.reply_to_message_id
        files = {"photo": open(path, 'rb')}
        if self.debug:
            print_message("Trying to /sendPhoto:")
            print_message(url)
            print_message(params)
            print_message("files: " + str(files))
        res = requests.post(url, params=params, files=files, proxies=self.proxies)
        answer = res.text
        answer_json = json.loads(answer.decode('utf8'))
        if not answer_json["ok"]:
            print_message(answer_json)
            return answer_json
        else:
            return answer_json

    def get_uid(self, name):
        uid = 0
        if self.debug:
            print_message("Getting uid from /getUpdates...")
        updates = self.get_updates()
        for m in updates["result"]:
            if "message" in chat:
                chat = m["message"]["chat"]
            elif "edited_message" in chat:
                chat = m["edited_message"]["chat"]
            if chat["type"] == self.type == "private":
                if "username" in chat:
                    if chat["username"] == name:
                        uid = chat["id"]
            if (chat["type"] == "group" or chat["type"] == "supergroup") and self.type == "group":
                if "title" in chat:
                    if chat["title"] == name.decode("utf-8"):
                        uid = chat["id"]
        return uid

    def error_need_to_contact(self, to):
        if self.type == "private":
            print_message("User '{0}' needs to send some text bot in private".format(to))
        if self.type == "group":
            print_message("You need to mention your bot in '{0}' group chat (i.e. type @YourBot)".format(to))

    def update_cache_uid(self, name, uid, message="Add new string to cache file"):
        cache_string = "{0};{1};{2}\n".format(name, self.type, str(uid).rstrip())
        # FIXME
        if self.debug:
            print_message("{0}: {1}".format(message, cache_string))
        with open(self.tmp_uids, "a") as cache_file_uids:
            cache_file_uids.write(cache_string)

    def get_uid_from_cache(self, name):
        uid = 0
        if os.path.isfile(self.tmp_uids):
            with open(self.tmp_uids, 'r') as cache_file_uids:
                cache_uids_old = cache_file_uids.readlines()

            for u in cache_uids_old:
                u_splitted = u.split(";")
                if name == u_splitted[0] and self.type == u_splitted[1]:
                    uid = u_splitted[2]

        return uid


class ZabbixAPI():
    def __init__(self, server, username, password):
        self.debug = False
        self.server = server
        self.username = username
        self.password = password
        self.proxies = {}
        self.verify = True
        self.cookie = None

    def login(self):

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
            cookie = None

        self.cookie = cookie

    def graph_get(self, itemid, period, title, width, height, tmp_dir):
        file_img = tmp_dir + "/{0}.png".format(itemid)

        title = requests.utils.quote(title)

        zbx_img_url = self.server + "/chart3.php?period={1}&name={2}" \
                                    "&width={3}&height={4}&graphtype=0&legend=1" \
                                    "&items[0][itemid]={0}&items[0][sortorder]=0" \
                                    "&items[0][drawtype]=5&items[0][color]=00CC00".format(itemid, period, title,
                                                                                          width, height)
        if self.debug:
            print_message(zbx_img_url)
        res = requests.get(zbx_img_url, cookies=self.cookie, proxies=self.proxies, verify=self.verify)
        res_code = res.status_code
        if res_code == 404:
            print_message("can't get image from '{0}'".format(zbx_img_url))
            return False
        res_img = res.content
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

    tmp_cookie = tmp_dir + "/cookie.py.txt"
    tmp_uids = tmp_dir + "/uids.txt"
    tmp_need_update = False  # do we need to update cache file with uids or not

    rnd = random.randint(0, 999)
    ts = time.time()
    hash_ts = str(ts) + "." + str(rnd)

    log_file = "/dev/null"

    zbx_to = sys.argv[1]
    zbx_subject = sys.argv[2]
    zbx_body = sys.argv[3]

    tg = TelegramAPI(key=zbxtg_settings.tg_key)

    tg.tmp_uids = tmp_uids

    if zbxtg_settings.proxy_to_tg:
        tg.proxies = {
            "http": "http://{0}/".format(zbxtg_settings.proxy_to_tg),
            "https": "https://{0}/".format(zbxtg_settings.proxy_to_tg)
            }

    zbx = ZabbixAPI(server=zbxtg_settings.zbx_server, username=zbxtg_settings.zbx_api_user,
                    password=zbxtg_settings.zbx_api_pass)

    if zbxtg_settings.proxy_to_zbx:
        zbx.proxies = {
            "http": "http://{0}/".format(zbxtg_settings.proxy_to_zbx),
            "https": "https://{0}/".format(zbxtg_settings.proxy_to_zbx)
            }

    try:
        zbx_api_verify = zbxtg_settings.zbx_api_verify
        zbx.verify = zbx_api_verify
    except:
        pass

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
        "is_channel": False,
        "disable_web_page_preview": False,
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
        "channel": {"name": "is_channel", "type": "bool"},
        "disable_web_page_preview": {"name": "disable_web_page_preview", "type": "bool"},
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
    is_channel = bool(settings["is_channel"])
    disable_web_page_preview = bool(settings["disable_web_page_preview"])

    # experimental way to send message to the group https://github.com/ableev/Zabbix-in-Telegram/issues/15
    if sys.argv[0].split("/")[-1] == "zbxtg_group.py" or "--group" in sys.argv or tg_chat:
        tg_chat = True
        tg.type = "group"

    if "--debug" in sys.argv or is_debug:
        is_debug = True
        tg.debug = True
        zbx.debug = True
        print_message(tg.get_me())
        print_message("Cache file with uids: " + tg.tmp_uids)
        log_file = tmp_dir + ".debug." + hash_ts + ".log"
        #print_message(log_file)

    if "--markdown" in sys.argv:
        tg.markdown = True

    if "--html" in sys.argv:
        tg.html = True

    if "--channel" in sys.argv or is_channel:
        tg.type = "channel"

    if "--disable_web_page_preview" in sys.argv or disable_web_page_preview:
        if is_debug:
            print_message("'disable_web_page_preview' option has been enabled")
        tg.disable_web_page_preview = True

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

    uid = None

    if tg.type == "channel":
        uid = zbx_to
    else:
        zbx_to = zbx_to.replace("@", "")

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
        if zbxtg_settings.zbx_tg_signature:
            zbxtg_body_text.append("--")
            zbxtg_body_text.append(zbxtg_settings.zbx_server)
    except:
        pass

    # replace text with emojis
    if hasattr(zbxtg_settings, "emoji_map"):
        zbxtg_body_text_emoji_support = []
        for l in zbxtg_body_text:
            l_new = l
            for k, v in zbxtg_settings.emoji_map.iteritems():
                l_new = l_new.replace("{{" + k + "}}", v)
            zbxtg_body_text_emoji_support.append(l_new)
        zbxtg_body_text = zbxtg_body_text_emoji_support

    if not tg_method_image:
        result = tg.send_message(uid, zbxtg_body_text)
        if not result["ok"]:
            if result["description"] == "[Error]: Bad Request: group chat is migrated to supergroup chat":
                migrate_to_chat_id = result["parameters"]["migrate_to_chat_id"]
                tg.update_cache_uid(zbx_to, uid, message="Group chat is migrated to supergroup, updating cache file")
                uid = migrate_to_chat_id
                result = tg.send_message(uid, zbxtg_body_text)
    else:
        zbx.login()
        if not zbx.cookie:
            print_message("Login to Zabbix web UI has failed, check manually...")
        else:
            zbxtg_file_img = zbx.graph_get(settings["zbxtg_itemid"], settings["zbxtg_image_period"],
                                           settings["zbxtg_title"], settings["zbxtg_image_width"],
                                           settings["zbxtg_image_height"], tmp_dir)
            #zbxtg_body_text, is_modified = list_cut(zbxtg_body_text, 200)
            result = tg.send_message(uid, zbxtg_body_text)
            message_id = result["result"]["message_id"]
            tg.reply_to_message_id = message_id
            tg.disable_notification = True
            if not zbxtg_file_img:
                tg.send_message(uid, ["Can't get graph image, check script manually, see logs, or disable graphs"])
                print_message("Can't get image, check URL manually")
            else:

                zbxtg_body_text = ""
                """
                if is_modified:
                    print_message("probably you will see MEDIA_CAPTION_TOO_LONG error, "
                                  "the message has been cut to 200 symbols, "
                                  "https://github.com/ableev/Zabbix-in-Telegram/issues/9"
                                  "#issuecomment-166895044")
                """
                if tg.send_photo(uid, zbxtg_body_text, zbxtg_file_img):
                    os.remove(zbxtg_file_img)


if __name__ == "__main__":
    main()