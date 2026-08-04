# -*- coding: utf-8 -*-
"""End-to-end smoke tests for zbxtg_lib.cli.main(), with TelegramAPI/ZabbixWeb
network calls replaced by fakes -- no real HTTP is made.
"""
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zbxtg_lib import cli  # noqa: E402


def test_split_thread_id_parses_trailing_numeric_suffix():
    assert cli._split_thread_id("Supergroup:2") == ("Supergroup", 2)
    assert cli._split_thread_id("-100123456:2") == ("-100123456", 2)


def test_split_thread_id_leaves_plain_names_untouched():
    assert cli._split_thread_id("Supergroup") == ("Supergroup", None)
    assert cli._split_thread_id("12345") == ("12345", None)
    assert cli._split_thread_id("some:name") == ("some:name", None)


def write_config(tmp_path):
    (tmp_path / "zbxtg_settings.yaml").write_text(
        'telegram:\n  bot_token: "123:ABC"\n'
        'zabbix:\n  server: "http://zabbix.example.com/zabbix"\n'
    )


class FakeTelegramAPI:
    instances = []

    def __init__(self, token, logger=None):
        self.token = token
        self.logger = logger
        self.chat_type = "private"
        self.markdown = False
        self.html = False
        self.disable_web_page_preview = False
        self.disable_notification = False
        self.reply_to_message_id = 0
        self.message_thread_id = None
        self.tmp_dir = None
        self.image_buttons = False
        self.proxies = {}
        self.ok = True
        self.error = None
        self.result = {"ok": True, "result": {"message_id": 7}}
        self.sent_messages = []
        self.sent_photos = []
        FakeTelegramAPI.instances.append(self)

    def send_message(self, chat_id, text_lines):
        self.sent_messages.append((chat_id, list(text_lines)))
        self.ok = True
        self.result = {"ok": True, "result": {"message_id": 7}}
        return self.result

    def send_photo(self, chat_id, caption, path):
        self.sent_photos.append((chat_id, list(caption), path))
        self.ok = True
        self.result = {"ok": True, "result": {"message_id": 8}}
        return self.result

    def send_location(self, chat_id, lat, lon):
        return {"ok": True}

    def get_me(self):
        return {"ok": True, "result": {"username": "test_bot"}}

    def find_chat_id(self, name):
        return None

    def explain_contact_requirement(self, name):
        pass


class FakeZabbixWeb:
    instances = []

    def __init__(self, server, username, password, logger=None):
        self.server = server
        self.tmp_dir = None
        self.verify = True
        self.basic_auth_user = None
        self.basic_auth_pass = None
        self.proxies = {}
        self.login_called = False
        FakeZabbixWeb.instances.append(self)

    def login(self):
        self.login_called = True
        return True

    def graph_get(self, itemids, period, title, width, height):
        path = os.path.join(self.tmp_dir, "fake_graph.png")
        with open(path, "wb") as fd:
            fd.write(b"fake-png")
        return path


def run_main(tmp_path, monkeypatch, argv):
    write_config(tmp_path)
    FakeTelegramAPI.instances.clear()
    FakeZabbixWeb.instances.clear()
    monkeypatch.setattr(cli, "TelegramAPI", FakeTelegramAPI)
    monkeypatch.setattr(cli, "ZabbixWeb", FakeZabbixWeb)
    monkeypatch.chdir(tmp_path)
    argv = ["zbxtg.py"] + argv
    return cli.main(argv)


def test_main_sends_plain_message(tmp_path, monkeypatch):
    rc = run_main(tmp_path, monkeypatch, ["12345", "PROBLEM: high load", "some body text"])
    assert rc == 0
    tg = FakeTelegramAPI.instances[-1]
    assert tg.sent_messages
    chat_id, lines = tg.sent_messages[0]
    assert chat_id == "12345"
    assert "PROBLEM: high load" in lines


def test_main_to_with_thread_id_sends_to_topic(tmp_path, monkeypatch):
    """'ChatId:N' addresses topic N of a forum supergroup (message_thread_id)."""
    rc = run_main(tmp_path, monkeypatch, ["12345:2", "PROBLEM", "some body text", "--group"])
    assert rc == 0
    tg = FakeTelegramAPI.instances[-1]
    assert tg.message_thread_id == 2
    chat_id, lines = tg.sent_messages[0]
    assert chat_id == "12345"


def test_main_to_without_thread_id_leaves_message_thread_id_unset(tmp_path, monkeypatch):
    rc = run_main(tmp_path, monkeypatch, ["12345", "PROBLEM", "some body text"])
    assert rc == 0
    tg = FakeTelegramAPI.instances[-1]
    assert tg.message_thread_id is None


def test_main_with_graphs_directive_fetches_and_sends_photo(tmp_path, monkeypatch):
    rc = run_main(
        tmp_path,
        monkeypatch,
        ["12345", "PROBLEM", "value is high\nzbxtg;graphs\nzbxtg;itemid:111"],
    )
    assert rc == 0
    zbx = FakeZabbixWeb.instances[-1]
    assert zbx.login_called is True
    tg = FakeTelegramAPI.instances[-1]
    assert tg.sent_photos


def test_main_external_image_skips_zabbix_login(tmp_path, monkeypatch):
    """Regression test: sending an external_image must not require a working
    Zabbix login -- found while manually testing the picture-sending flow."""
    fake_image_path = str(tmp_path / "fake_external.png")

    def fake_external_image_get(url, tmp_dir, logger=None):
        with open(fake_image_path, "wb") as fd:
            fd.write(b"fake-bytes")
        return fake_image_path

    monkeypatch.setattr(cli, "external_image_get", fake_external_image_get)
    rc = run_main(
        tmp_path,
        monkeypatch,
        ["12345", "PROBLEM", "pic\nzbxtg;graphs\nzbxtg;external_image:https://example.com/pic.jpg"],
    )
    assert rc == 0
    zbx = FakeZabbixWeb.instances[-1]
    assert zbx.login_called is False
    tg = FakeTelegramAPI.instances[-1]
    assert tg.sent_photos
    assert tg.sent_photos[0][2] == fake_image_path


def test_main_no_args_returns_zero_and_prints_usage(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["zbxtg.py"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "zbxtg.py [TO] [SUBJECT] [BODY]" in captured.out


def test_main_features_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["zbxtg.py", "--features"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "graphs_period" in captured.out
