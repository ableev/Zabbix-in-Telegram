# -*- coding: utf-8 -*-
# DEPRECATED: new installations should copy zbxtg_settings.example.yaml to
# zbxtg_settings.yaml instead. This legacy .py format is still auto-detected
# as a fallback (see zbxtg_lib/config.py) but will be removed in a future
# release.

tg_key = "XYZ"  # telegram bot api key

zbx_tg_prefix = "zbxtg"  # variable for separating text from script info
zbx_tg_tmp_dir = "/var/tmp/" + zbx_tg_prefix  # directory for saving caches, uids, cookies, etc.
zbx_tg_signature = False

zbx_tg_update_messages = True
zbx_tg_matches = {
    "problem": "PROBLEM: ",
    "ok": "OK: "
}

zbx_server = "http://127.0.0.1/zabbix/"  # zabbix server full url
zbx_api_user = "api"
zbx_api_pass = "api"
zbx_api_verify = True  # True - do not ignore self signed certificates, False - ignore

#zbx_server_version = 2  # for Zabbix 2.x version
zbx_server_version = 3  # for Zabbix 3.x version, by default, not everyone updated to 4.x yet
#zbx_server_version = 4  # for Zabbix 4.x version, default will be changed in the future with this

zbx_basic_auth = False
zbx_basic_auth_user = "zabbix"
zbx_basic_auth_pass = "zabbix"

proxy_to_zbx = None
proxy_to_tg = None

# proxy_to_zbx = "http://proxy.local:3128"
# proxy_to_tg = "https://proxy.local:3128"

# proxy_to_tg = "socks5://user1:password2@hostname:port" # socks5 with username and password
# proxy_to_tg = "socks5://hostname:port" # socks5 without username and password
# proxy_to_tg = "socks5h://hostname:port" # hostname resolution on SOCKS proxy. 
                                          # This helps when internet provider alter DNS queries.
                                          # Found here: https://stackoverflow.com/a/43266186/957508

google_maps_api_key = None  # get your key, see https://developers.google.com/maps/documentation/geocoding/intro

zbx_tg_daemon_enabled = False
zbx_tg_daemon_enabled_ids = [6931850, ]
zbx_tg_daemon_enabled_users = ["ableev", ]
zbx_tg_daemon_enabled_chats = ["Zabbix in Telegram Script", ]

zbx_db_host = "localhost"
zbx_db_database = "zabbix"
zbx_db_user = "zbxtg"
zbx_db_password = "zbxtg"


emoji_map = {
    "Disaster": "🔥",
    "High": "🛑",
    "Average": "❗",
    "Warning": "⚠️",
    "Information": "ℹ️",
    "Not classified": "🔘",
    "OK": "✅",
    "PROBLEM": "❗",
    "info": "ℹ️",
    "WARNING": "⚠️",
    "DISASTER": "❌",
    "bomb": "💣",
    "fire": "🔥",
    "hankey": "💩",
}
