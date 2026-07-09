# -*- coding: utf-8 -*-
"""Fetches rendered graph images from the Zabbix web frontend.

Why scrape the frontend instead of using the JSON-RPC API: the Zabbix API
(``graph.get`` / ``item.get`` / etc.) only ever returns *configuration*
(graph ids, names, axis settings...); it does not render pixels. Rendering
is done exclusively by frontend PHP endpoints (``chart.php``,
``chart2.php``, ``chart3.php``, ``chart6.php`` for SVG widgets). This is
still true as of Zabbix 7.0 -- confirmed against the current Zabbix
frontend source (``ui/chart3.php``), which still accepts the same
``items[N][itemid|sortorder|drawtype|color]`` array parameters this module
has used since Zabbix 2.x. See:
https://git.zabbix.com/projects/ZBX/repos/zabbix/browse/ui/chart3.php

One behavioural change from older Zabbix versions: current ``chart3.php``
only accepts a ``from``/``to`` time range (no bare ``period`` field), so the
old "Zabbix 2.x style" URL branch has been dropped -- this module targets
Zabbix 4.0+ (Zabbix 7.0 as the primary target). If you are still running
Zabbix 2.x/3.x, pin to zbxtg <3.0.

Logging into the frontend itself needs no CSRF token: the login form
(``ui/include/views/general.login.php``) posts only ``name``/``password``/
``autologin``/``enter`` -- Zabbix's CSRF protection is keyed off an
authenticated session secret that doesn't exist yet at login time.
"""
from __future__ import annotations

import hashlib
import logging
import random
import string
from typing import Dict, List, Optional

import requests

GRAPH_COLORS = {
    0: "00CC00",
    1: "CC0000",
    2: "0000CC",
    3: "CCCC00",
    4: "00CCCC",
    5: "CC00CC",
}


class ZabbixWeb:
    def __init__(
        self,
        server: str,
        username: str,
        password: str,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.server = server.rstrip("/")
        self.username = username
        self.password = password
        self.logger = logger or logging.getLogger("zbxtg")
        self.session = requests.Session()
        self.proxies: Dict[str, str] = {}
        self.verify = True
        self.basic_auth_user: Optional[str] = None
        self.basic_auth_pass: Optional[str] = None
        self.tmp_dir: Optional[str] = None
        self.logged_in = False

    @property
    def _basic_auth(self) -> Optional[requests.auth.HTTPBasicAuth]:
        if self.basic_auth_user is not None:
            return requests.auth.HTTPBasicAuth(self.basic_auth_user, self.basic_auth_pass)
        return None

    def login(self) -> bool:
        if not self.verify:
            requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]

        data = {"name": self.username, "password": self.password, "enter": "Sign in"}
        answer = self.session.post(
            self.server + "/",
            data=data,
            proxies=self.proxies,
            verify=self.verify,
            auth=self._basic_auth,
        )
        if len(answer.history) > 1 and answer.history[0].status_code == 302:
            self.logger.warning(
                "The configured Zabbix server URL might be missing a path segment "
                "(e.g. '%s' instead of '%s')", self.server, self.server + "/zabbix"
            )
        if not self.session.cookies:
            self.logger.error("Zabbix login failed for url: %s/", self.server)
            self.logged_in = False
            return False
        self.logged_in = True
        return True

    def graph_get(
        self,
        itemids: List[str],
        period: Optional[int],
        title: Optional[str],
        width: int,
        height: int,
    ) -> Optional[str]:
        """Fetch a rendered graph PNG for one or more items and return its local path."""
        if not self.tmp_dir:
            raise RuntimeError("tmp_dir must be set before calling graph_get()")

        file_img = "{0}/{1}.png".format(
            self.tmp_dir, "".join(random.choice(string.ascii_letters) for _ in range(10))
        )

        drawtype = 5 if len(itemids) == 1 else 2

        item_params = []
        for i, itemid in enumerate(itemids):
            item_params.append(
                "&items[{0}][itemid]={1}&items[{0}][sortorder]={0}"
                "&items[{0}][drawtype]={2}&items[{0}][color]={3}".format(
                    i, itemid, drawtype, GRAPH_COLORS[i % len(GRAPH_COLORS)]
                )
            )

        url = "{0}/chart3.php?from=now-{1}&to=now".format(self.server, period or 3600)
        url += "&name={0}&width={1}&height={2}&graphtype=0&legend=1".format(
            requests.utils.quote(title or ""), width, height
        )
        url += "".join(item_params)

        self.logger.debug("Fetching graph: %s", url)
        answer = self.session.get(url, proxies=self.proxies, verify=self.verify, auth=self._basic_auth)
        if answer.status_code == 404:
            self.logger.error("Could not fetch graph image from '%s' (HTTP 404)", url)
            return None
        with open(file_img, "wb") as fd:
            fd.write(answer.content)
        return file_img

    def api_login_test(self) -> str:
        """Diagnostic helper: raw JSON-RPC user.login response, for troubleshooting credentials."""
        import json

        headers = {"Content-type": "application/json"}
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "user.login",
                "params": {"username": self.username, "password": self.password},
                "id": 1,
            }
        )
        answer = self.session.post(
            self.server + "/api_jsonrpc.php", data=payload, proxies=self.proxies, headers=headers
        )
        return answer.text


def external_image_get(url: str, tmp_dir: str, timeout: int = 6, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """Download an externally-hosted image for the `external_image` directive."""
    logger = logger or logging.getLogger("zbxtg")
    image_hash = hashlib.md5(url.encode()).hexdigest()
    file_img = "{0}/external_{1}.png".format(tmp_dir, image_hash)
    try:
        answer = requests.get(url, timeout=timeout, allow_redirects=True)
    except requests.exceptions.ReadTimeout:
        logger.error("Could not fetch external image from '%s': timeout", url)
        return None
    if answer.status_code == 404:
        logger.error("Could not fetch external image from '%s': HTTP 404", url)
        return None
    with open(file_img, "wb") as fd:
        fd.write(answer.content)
    return file_img
