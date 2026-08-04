# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zbxtg_lib.telegram_api import TelegramAPI  # noqa: E402


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


def make_tg(payload):
    tg = TelegramAPI("123:ABC")
    tg.session = FakeSession(payload)
    return tg


def test_send_message_success_updates_ok_and_result():
    tg = make_tg({"ok": True, "result": {"message_id": 42}})
    result = tg.send_message("42", ["hello", "world"])
    assert tg.ok is True
    assert tg.error is None
    assert result["result"]["message_id"] == 42


def test_send_message_failure_sets_error():
    tg = make_tg({"ok": False, "description": "Bad Request: chat not found"})
    tg.send_message("42", ["hi"])
    assert tg.ok is False
    assert tg.error == "Bad Request: chat not found"


def test_send_message_uri_too_long_handled_without_json_parse():
    tg = TelegramAPI("123:ABC")

    class Session414:
        def post(self, url, **kwargs):
            return FakeResponse({}, status_code=414)

        def get(self, url, **kwargs):
            raise AssertionError("not expected")

    tg.session = Session414()
    tg.send_message("42", ["hi"])
    assert tg.ok is False
    assert tg.error == "414 URI Too Long"


def test_markdown_parse_mode_added_when_enabled():
    tg = make_tg({"ok": True, "result": {"message_id": 1}})
    tg.markdown = True
    tg.send_message("1", ["*bold*"])
    _, kwargs = tg.session.calls[-1]
    assert kwargs["params"]["parse_mode"] == "Markdown"


def test_html_parse_mode_added_when_enabled():
    tg = make_tg({"ok": True, "result": {"message_id": 1}})
    tg.html = True
    tg.send_message("1", ["<b>bold</b>"])
    _, kwargs = tg.session.calls[-1]
    assert kwargs["params"]["parse_mode"] == "HTML"


def test_find_chat_id_matches_private_username():
    payload = {
        "ok": True,
        "result": [
            {"message": {"chat": {"type": "private", "username": "someuser", "id": 555}}},
        ],
    }
    tg = make_tg(payload)
    tg.chat_type = "private"
    assert tg.find_chat_id("someuser") == "555"


def test_find_chat_id_matches_group_title():
    payload = {
        "ok": True,
        "result": [
            {"message": {"chat": {"type": "supergroup", "title": "Ops Room", "id": -100123}}},
        ],
    }
    tg = make_tg(payload)
    tg.chat_type = "group"
    assert tg.find_chat_id("Ops Room") == "-100123"


def test_find_chat_id_no_match_returns_none():
    payload = {"ok": True, "result": []}
    tg = make_tg(payload)
    assert tg.find_chat_id("nobody") is None


def test_send_message_includes_message_thread_id_when_set():
    tg = make_tg({"ok": True, "result": {"message_id": 1}})
    tg.message_thread_id = 2
    tg.send_message("-100123", ["hi"])
    _, kwargs = tg.session.calls[-1]
    assert kwargs["params"]["message_thread_id"] == 2


def test_send_message_omits_message_thread_id_by_default():
    tg = make_tg({"ok": True, "result": {"message_id": 1}})
    tg.send_message("-100123", ["hi"])
    _, kwargs = tg.session.calls[-1]
    assert "message_thread_id" not in kwargs["params"]


def test_send_photo_includes_message_thread_id_when_set(tmp_path):
    tg = make_tg({"ok": True, "result": {"message_id": 1}})
    tg.message_thread_id = 2
    image_path = tmp_path / "graph.png"
    image_path.write_bytes(b"fake-png")
    tg.send_photo("-100123", ["caption"], str(image_path))
    _, kwargs = tg.session.calls[-1]
    assert kwargs["params"]["message_thread_id"] == 2
