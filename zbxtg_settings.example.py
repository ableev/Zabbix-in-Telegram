tg_key = "XYZ"  # telegram bot api key

zbx_tg_prefix = "zbxtg"  # variable for separating text from script info
zbx_tg_tmp_dir = "/tmp/" + zbx_tg_prefix  # directory for saving caches, uids, cookies, etc.
zbx_tg_signature = False

zbx_server = "http://localhost"  # zabbix server full url
zbx_api_user = "api"
zbx_api_pass = "api"
zbx_api_verify = True  # True - do not ignore self signed certificates, False - ignore

proxy_to_zbx = None
proxy_to_tg = None

#proxy_to_zbx = "proxy.local:3128"
#proxy_to_tg = "proxy.local:3128"
