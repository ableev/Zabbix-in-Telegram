#!/usr/bin/env python
# coding: utf-8

import sys
import os
import hashlib
import time
import random
import requests
import json
import re
import stat
import time
import MySQLdb
from os.path import dirname
import zbxtg_settings
import zbxtg


class ZabbixDB():
    def __init__(self, host, database, user, password):
        self.host = host
        self.database = database
        self.user = user
        self.password = password

    def connect(self):
        db = MySQLdb.connect(host=self.host,
                             user=self.user,
                             passwd=self.password,
                             db=self.database,
                             charset='utf8',
                             init_command='SET NAMES UTF8')

        self.sql = db.cursor(MySQLdb.cursors.DictCursor)

    def db_query(self, query):

        result = None

        try:
            self.sql.execute(query)
            result = list(self.sql.fetchall())

        except self.sql.Error, err:
            print "ERROR %d: %s" % (err.args[0], err.args[1])

        return result

    def triggers(self):
        q = "SELECT h.name AS host, h.hostid AS hostid, t.triggerid," \
            "t.description AS `trigger`, t.priority AS severity, t.lastchange " \
            "FROM triggers t " \
            "LEFT JOIN functions f ON t.triggerid = f.triggerid " \
            "LEFT JOIN items i ON f.itemid = i.itemid " \
            "LEFT JOIN hosts h ON i.hostid = h.hostid " \
            "LEFT JOIN hosts_groups hg ON h.hostid = hg.hostid " \
            "LEFT JOIN groups g ON hg.groupid = g.groupid " \
            "LEFT JOIN interface ifa ON h.hostid = ifa.hostid AND ifa.main = 1 " \
            "WHERE t.value = 1 " \
            "AND h.status = 0 " \
            "AND t.status = 0 " \
            "AND i.status = 0 " \
            "AND t.priority > 0 " \
            "GROUP BY t.triggerid;"
        print q
        result = self.db_query(q)
        return result

    def close(self):
        self.sql.close()


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
    ZabbixAPI = zbxtg.ZabbixAPI
    tmp_dir = zbxtg_settings.zbx_tg_tmp_dir

    if not zbxtg_settings.zbx_tg_daemon_enabled:
        print("You should enable daemon by adding 'zbx_tg_remote_control' into configuration")
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
        tg.proxies = {"http": "http://{0}/".format(zbxtg_settings.proxy_to_tg)}

    zbx = ZabbixAPI(server=zbxtg_settings.zbx_server, username=zbxtg_settings.zbx_api_user,
                    password=zbxtg_settings.zbx_api_pass)
    if zbxtg_settings.proxy_to_zbx:
        zbx.proxies = {"http": "http://{0}/".format(zbxtg_settings.proxy_to_zbx)}

    try:
        zbx_api_verify = zbxtg_settings.zbx_api_verify
        zbx.verify = zbx_api_verify
    except:
        pass

    zbxdb = ZabbixDB(host=zbxtg_settings.zbx_db_host, database=zbxtg_settings.zbx_db_database,
                   user=zbxtg_settings.zbx_db_user, password=zbxtg_settings.zbx_db_password)

    zbxdb.connect()

    print tg.get_me()

    hosts = zbxdb.db_query("SELECT hostid, host FROM hosts")

    commands = [
        "graphs_on_host",
        "graph_get",
        "graphs_by_item",
        "hosts",
        "triggers",
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
            #print updates
            if not updates["result"]:
                continue
            for m in updates["result"]:
                update_id_last = m["update_id"]
                print update_id_last
                tg.update_offset = update_id_last
                if m["message"]["from"]["id"] not in zbxtg_settings.zbx_tg_daemon_wl_ids:
                    file_write(tmp_ts["update_offset"], update_id_last)
                    continue
                    print("Fuck this shit")
                else:
                    print json.dumps(m)
                    text = m["message"]["text"]
                    #print text
                    to = m["message"]["from"]["id"]
                    reply_text = list()
                    #reply_text.append(text)
                    #print type(m["message"]["message_id"])
                    #print type(message_id_last)
                    if m["message"]["message_id"] > message_id_last:
                        if re.search(r"^/triggers", text):
                            triggers = zbxdb.triggers()
                            if triggers:
                                for t in triggers:
                                    reply_text.append("Severity: {0}, Host: {1}, Trigger: {2}".format(
                                        t["severity"], t["host"], t["trigger"]
                                    ))
                            else:
                                reply_text.append("There are no triggers, have a nice day!")

                        if not reply_text:
                            reply_text = ["I don't know what to do about it"]
                        if tg.send_message(to, reply_text):
                            with open(tmp_ts["message_id"], "w") as message_id_file:
                                message_id_file.write(str(m["message"]["message_id"]))
                            message_id_last = m["message"]["message_id"]
                file_write(tmp_ts["update_offset"], update_id_last)
    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == "__main__":
    main()