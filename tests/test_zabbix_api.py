# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from zbxtg_lib.zabbix_api import ZabbixApi, ZabbixApiError  # noqa: E402


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP {0}".format(self.status_code))


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


def test_login_with_token_skips_user_login_call():
    api = ZabbixApi("http://zabbix.example.com/zabbix", token="pre-issued-token")
    api.session = FakeSession({"result": []})
    api.login()
    assert api.token == "pre-issued-token"
    assert api.session.calls == []  # no HTTP call made


def test_login_with_credentials_calls_user_login_and_stores_token():
    api = ZabbixApi("http://zabbix.example.com/zabbix", username="api", password="secret")
    api.session = FakeSession({"jsonrpc": "2.0", "result": "issued-token", "id": 1})
    api.login()
    assert api.token == "issued-token"
    method_used = api.session.calls[0][1]["json"]["method"]
    assert method_used == "user.login"
    login_params = api.session.calls[0][1]["json"]["params"]
    assert login_params == {"username": "api", "password": "secret"}


def test_login_without_credentials_or_token_raises():
    api = ZabbixApi("http://zabbix.example.com/zabbix")
    with pytest.raises(ZabbixApiError):
        api.login()


def test_call_raises_on_api_error():
    api = ZabbixApi("http://zabbix.example.com/zabbix", token="tok")
    api.session = FakeSession({"jsonrpc": "2.0", "error": {"message": "Invalid params", "data": "bad itemid"}, "id": 1})
    with pytest.raises(ZabbixApiError):
        api.call("item.get", {"itemids": ["nope"]})


def test_bearer_header_used_when_token_present():
    api = ZabbixApi("http://zabbix.example.com/zabbix", token="tok")
    api.session = FakeSession({"jsonrpc": "2.0", "result": [], "id": 1})
    api.call("item.get", {})
    headers = api.session.calls[0][1]["headers"]
    assert headers["Authorization"] == "Bearer tok"


def test_item_exists_true_when_found():
    api = ZabbixApi("http://zabbix.example.com/zabbix", token="tok")
    api.session = FakeSession({"jsonrpc": "2.0", "result": [{"itemid": "111"}], "id": 1})
    assert api.item_exists("111") is True


def test_item_exists_false_when_empty_result():
    api = ZabbixApi("http://zabbix.example.com/zabbix", token="tok")
    api.session = FakeSession({"jsonrpc": "2.0", "result": [], "id": 1})
    assert api.item_exists("999") is False
