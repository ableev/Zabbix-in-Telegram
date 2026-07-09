# -*- coding: utf-8 -*-
"""Minimal Zabbix JSON-RPC API client.

Not required for the core alert-sending flow (graphs are fetched from the
web frontend -- see zabbix_web.py, images aren't exposed over the API).
This client exists for optional, future use: validating that an itemid
exists before trying to render its graph, or reuse by ZbxTgDaemon.py-style
tooling.

Auth handling follows the current Zabbix documentation
(https://www.zabbix.com/documentation/current/en/manual/api):

* Zabbix 6.4+: prefer an API token, sent as ``Authorization: Bearer <token>``.
  The ``auth`` request parameter is deprecated as of 7.0.
* Zabbix 7.2+: the deprecated ``auth`` parameter is removed entirely -- a
  token (or a fresh ``user.login`` + Bearer header) is mandatory.
* Older setups without a token: fall back to ``user.login`` with
  ``username``/``password`` (the ``user`` field name was replaced by
  ``username`` in Zabbix 5.4) and send the resulting token via the
  ``Authorization`` header too, since that also works on any version that
  accepts Bearer auth.
"""
from __future__ import annotations

import itertools
import logging
from typing import Any, Dict, Optional

import requests


class ZabbixApiError(Exception):
    pass


class ZabbixApi:
    def __init__(
        self,
        server: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        verify: bool = True,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.url = server.rstrip("/") + "/api_jsonrpc.php"
        self.username = username
        self.password = password
        self.token = token
        self.verify = verify
        self.logger = logger or logging.getLogger("zbxtg")
        self.session = requests.Session()
        self.proxies: Dict[str, str] = {}
        self._id_counter = itertools.count(1)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json-rpc"}
        if self.token:
            headers["Authorization"] = "Bearer {0}".format(self.token)
        return headers

    def login(self) -> None:
        if self.token:
            return  # nothing to do, Bearer header is used per-request
        if not (self.username and self.password):
            raise ZabbixApiError("Either an API token or username/password must be configured")
        result = self.call("user.login", {"username": self.username, "password": self.password}, _auth=False)
        self.token = result

    def call(self, method: str, params: Optional[Dict[str, Any]] = None, _auth: bool = True) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": next(self._id_counter),
        }
        self.logger.debug("Zabbix API call: %s(%s)", method, params)
        answer = self.session.post(
            self.url,
            json=payload,
            headers=self._headers() if _auth else {"Content-Type": "application/json-rpc"},
            proxies=self.proxies,
            verify=self.verify,
        )
        answer.raise_for_status()
        data = answer.json()
        if "error" in data:
            raise ZabbixApiError(
                "{0}: {1}".format(data["error"].get("message"), data["error"].get("data"))
            )
        return data["result"]

    def item_exists(self, itemid: str) -> bool:
        try:
            items = self.call("item.get", {"itemids": [itemid], "output": ["itemid"]})
        except ZabbixApiError as exc:
            self.logger.warning("Could not verify itemid %s via the Zabbix API: %s", itemid, exc)
            return True  # fail open: don't block graph rendering on a diagnostic check
        return bool(items)

    def logout(self) -> None:
        if self.token and not (self.username and self.password):
            return  # a caller-supplied static token isn't ours to invalidate
        try:
            self.call("user.logout", {})
        except ZabbixApiError:
            pass
        finally:
            self.token = None
