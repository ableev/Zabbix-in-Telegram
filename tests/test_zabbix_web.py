# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zbxtg_lib.zabbix_web import ZabbixWeb  # noqa: E402


class FakeCookies(dict):
    pass


class FakeResponse:
    def __init__(self, content=b"", status_code=200, history=None, cookies=None):
        self.content = content
        self.status_code = status_code
        self.history = history or []
        self.cookies = cookies if cookies is not None else FakeCookies()


class FakeSession:
    def __init__(self):
        self.cookies = FakeCookies()
        self.get_calls = []
        self.post_calls = []
        self.login_should_succeed = True

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        if self.login_should_succeed:
            self.cookies["zbx_session"] = "abc123"
        return FakeResponse()

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return FakeResponse(content=b"fake-png-bytes")


def make_zbx():
    zbx = ZabbixWeb("http://zabbix.example.com/zabbix", "api", "secret")
    zbx.session = FakeSession()
    return zbx


def test_login_success_sets_logged_in_true():
    zbx = make_zbx()
    assert zbx.login() is True
    assert zbx.logged_in is True


def test_login_failure_when_no_cookie_returned():
    zbx = make_zbx()
    zbx.session.login_should_succeed = False
    assert zbx.login() is False
    assert zbx.logged_in is False


def test_graph_get_builds_from_to_url_not_legacy_period(tmp_path):
    zbx = make_zbx()
    zbx.tmp_dir = str(tmp_path)
    path = zbx.graph_get(["111"], period=10800, title="My Graph", width=900, height=200)
    assert path is not None
    assert os.path.exists(path)
    url = zbx.session.get_calls[0][0]
    assert "from=now-10800&to=now" in url
    assert "period=10800" not in url  # legacy Zabbix <4 style must not appear
    assert "chart3.php" in url


def test_graph_get_single_item_uses_drawtype_5():
    zbx = make_zbx()
    zbx.tmp_dir = "/tmp"
    zbx.graph_get(["111"], period=3600, title="t", width=900, height=200)
    url = zbx.session.get_calls[0][0]
    assert "items[0][drawtype]=5" in url


def test_graph_get_multiple_items_uses_drawtype_2_and_indexes():
    zbx = make_zbx()
    zbx.tmp_dir = "/tmp"
    zbx.graph_get(["111", "222"], period=3600, title="t", width=900, height=200)
    url = zbx.session.get_calls[0][0]
    assert "items[0][itemid]=111" in url
    assert "items[1][itemid]=222" in url
    assert "items[0][drawtype]=2" in url


def test_graph_get_returns_none_on_404():
    zbx = make_zbx()
    zbx.tmp_dir = "/tmp"

    class NotFoundSession(FakeSession):
        def get(self, url, **kwargs):
            self.get_calls.append((url, kwargs))
            return FakeResponse(status_code=404)

    zbx.session = NotFoundSession()
    result = zbx.graph_get(["111"], period=3600, title="t", width=900, height=200)
    assert result is None
