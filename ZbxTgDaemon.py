#!/usr/bin/env python
# coding: utf-8

import sys
import os
import hashlib
import re
import time
from os.path import dirname
import zbxtg_settings
import zbxtg
from pyzabbix import ZabbixAPI, ZabbixAPIException


class zabbixApi():
    def __init__(self, server, user, password):
        self.api = ZabbixAPI(server)
        self.user = user
        self.password = password

    def login(self):
        self.api.login(self.user, self.password)

    def triggers_active(self):
        return self.api.trigger.get(output="extend", monitored=True, filter={"value": 1}, sortfield="priority", sortorder="DESC",
                                    selectHosts="extend")



def print_message(string):
    string = str(string) + "\n"
    filename = sys.argv[0].split("/")[-1]
    sys.stderr.write(filename + ": " + string)


def file_write(filename, text):
    with open(filename, "w") as fd:
        fd.write(str(text))
    return True


def file_read(filename):
    with open(filename, 'r') as fd:
        text = fd.readlines()
    return text


def main():
    TelegramAPI = zbxtg.TelegramAPI
    ZabbixWeb = zbxtg.ZabbixWeb
    tmp_dir = zbxtg_settings.zbx_tg_tmp_dir

    if not zbxtg_settings.zbx_tg_daemon_enabled:
        print("You should enable daemon by adding 'zbx_tg_remote_control' in the configuration file")
        sys.exit(1)

    tmp_uids = tmp_dir + "/uids.txt"
    tmp_ts = {
        "message_id": tmp_dir + "/daemon_message_id.txt",
        "update_offset": tmp_dir + "/update_offset.txt",
    }

    for i, v in tmp_ts.iteritems():
        if not os.path.exists(v):
            print_message("{0} doesn't exist, creating new one...".format(v))
            file_write(v, "0")
            print_message("{0} successfully created".format(v))

    message_id_last = file_read(tmp_ts["message_id"])[0].strip()
    if message_id_last:
        message_id_last = int(message_id_last)

    update_id = file_read(tmp_ts["update_offset"])

    tg = TelegramAPI(key=zbxtg_settings.tg_key)
    if zbxtg_settings.proxy_to_tg:
        proxy_to_tg = zbxtg_settings.proxy_to_tg
        if not proxy_to_tg.find("http") and not proxy_to_tg.find("socks"):
            proxy_to_tg = "https://" + proxy_to_tg
        tg.proxies = {
            "https": "{0}".format(zbxtg_settings.proxy_to_tg),
        }
    zbx = ZabbixWeb(server=zbxtg_settings.zbx_server, username=zbxtg_settings.zbx_api_user,
                    password=zbxtg_settings.zbx_api_pass)
    if zbxtg_settings.proxy_to_zbx:
        zbx.proxies = {"http": "http://{0}/".format(zbxtg_settings.proxy_to_zbx)}

    try:
        zbx_api_verify = zbxtg_settings.zbx_api_verify
        zbx.verify = zbx_api_verify
    except:
        pass

    zbxapi = zabbixApi(zbxtg_settings.zbx_server, zbxtg_settings.zbx_api_user, zbxtg_settings.zbx_api_pass)
    zbxapi.login()

    print(tg.get_me())

    #hosts = zbxdb.db_query("SELECT hostid, host FROM hosts")

    commands = [
        "/triggers",
        "/help",
        # "/graph",
        # "/history",
        # "/screen"
    ]

    def md5(fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    md5sum = md5("ZbxTgDaemon.py")
    print md5sum

    try:
        while True:
            time.sleep(1)
            md5sum_new = md5("ZbxTgDaemon.py")
            if md5sum != md5sum_new:
                sys.exit(1)
            tg.update_offset = update_id
            updates = tg.get_updates()
            if not updates["result"]:
                continue
            for m in updates["result"]:
                if "message" not in m:
                    continue
                update_id_last = m["update_id"]
                tg.update_offset = update_id_last
                if m["message"]["from"]["id"] not in zbxtg_settings.zbx_tg_daemon_enabled_ids:
                    file_write(tmp_ts["update_offset"], update_id_last)
                    continue
                    print("Fuck this shit, I'm not going to answer to someone not from the whitelist")
                else:
                    if not "text" in m["message"]:
                        continue
                    text = m["message"]["text"]
                    to = m["message"]["from"]["id"]
                    reply_text = list()
                    if m["message"]["message_id"] > message_id_last:
                        if re.search(r"^/(start|help)", text):
                            reply_text.append("Hey, this is ZbxTgDaemon bot.")
                            reply_text.append("https://github.com/ableev/Zabbix-in-Telegram")
                            reply_text.append("If you need help, you can ask it in @ZbxTg group\n")
                            reply_text.append("Available commands:")
                            reply_text.append("\n".join(commands))
                            tg.disable_web_page_preview = True
                        if re.search(r"^/triggers", text):
                            triggers = zbxapi.triggers_active()
                            if triggers:
                                for t in triggers:
                                    reply_text.append("Severity: {0}, Host: {1}, Trigger: {2}".format(
                                        t["priority"], t["hosts"][0]["host"].encode('utf-8'), t["description"].encode('utf-8')
                                    ))
                            else:
                                reply_text.append("There are no triggers, have a nice day!")
                        if not reply_text:
                            reply_text = ["I don't know what to do about it"]
                        if tg.send_message(to, reply_text):
                            with open(tmp_ts["message_id"], "w") as message_id_file:
                                message_id_file.write(str(m["message"]["message_id"]))
                            message_id_last = m["message"]["message_id"]
                            tg.disable_web_page_preview = False
                file_write(tmp_ts["update_offset"], update_id_last)
    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == "__main__":
    main()