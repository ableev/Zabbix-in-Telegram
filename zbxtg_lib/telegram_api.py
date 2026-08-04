# -*- coding: utf-8 -*-
"""Thin wrapper around the Telegram Bot HTTP API.

Only the endpoints zbxtg actually needs are implemented (sendMessage,
sendPhoto, sendDocument, sendLocation, editMessageText, getUpdates,
answerCallbackQuery). See https://core.telegram.org/bots/api for the
upstream reference.
"""
from __future__ import annotations

import json
import logging
import os
import random
import string
from typing import Dict, List, Optional

import requests


class TelegramAPI:
    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, token: str, logger: Optional[logging.Logger] = None) -> None:
        self.token = token
        self.logger = logger or logging.getLogger("zbxtg")
        self.session = requests.Session()
        self.proxies: Dict[str, str] = {}
        self.chat_type = "private"  # "private" | "group" | "channel"
        self.markdown = False
        self.html = False
        self.disable_web_page_preview = False
        self.disable_notification = False
        self.reply_to_message_id = 0
        self.message_thread_id: Optional[int] = None
        self.tmp_dir: Optional[str] = None
        self.image_buttons = False
        self.update_offset = 0
        self.result: Optional[dict] = None
        self.ok: Optional[bool] = None
        self.error: Optional[str] = None

    # -- low level -----------------------------------------------------

    def _url(self, method: str) -> str:
        return "{0}{1}/{2}".format(self.BASE_URL, self.token, method)

    def _update_status(self) -> None:
        if self.result is None:
            self.ok = False
            self.error = "empty response"
            return
        self.ok = bool(self.result.get("ok"))
        if self.ok:
            self.error = None
        else:
            self.error = self.result.get("description")
            self.logger.error(self.error)

    # -- API calls -------------------------------------------------------

    def get_me(self) -> dict:
        answer = self.session.get(self._url("getMe"), proxies=self.proxies)
        self.result = answer.json()
        self._update_status()
        return self.result

    def get_updates(self) -> dict:
        params = {"offset": self.update_offset}
        self.logger.debug("GET getUpdates offset=%s", self.update_offset)
        answer = self.session.post(self._url("getUpdates"), params=params, proxies=self.proxies)
        self.result = answer.json()
        self.logger.debug("getUpdates response: %s", json.dumps(self.result))
        self._update_status()
        return self.result

    def send_message(self, chat_id, message: List[str]) -> dict:
        text = "\n".join(message)
        params = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": self.disable_web_page_preview,
            "disable_notification": self.disable_notification,
        }
        if self.reply_to_message_id:
            params["reply_to_message_id"] = self.reply_to_message_id
        if self.message_thread_id:
            params["message_thread_id"] = self.message_thread_id
        self._add_parse_mode(params)
        self.logger.debug("POST sendMessage params=%s", params)
        answer = self.session.post(self._url("sendMessage"), params=params, proxies=self.proxies)
        if answer.status_code == 414:
            self.result = {"ok": False, "description": "414 URI Too Long"}
        else:
            self.result = answer.json()
        self._update_status()
        return self.result

    def update_message(self, chat_id, message_id, message: List[str]) -> dict:
        text = "\n".join(message)
        params = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "disable_web_page_preview": self.disable_web_page_preview,
            "disable_notification": self.disable_notification,
        }
        self._add_parse_mode(params)
        self.logger.debug("POST editMessageText params=%s", params)
        answer = self.session.post(self._url("editMessageText"), params=params, proxies=self.proxies)
        self.result = answer.json()
        self._update_status()
        return self.result

    def send_photo(self, chat_id, caption: List[str], path: str) -> dict:
        text = "\n".join(caption)
        if self.image_buttons:
            reply_markup = json.dumps({"inline_keyboard": [[
                {"text": "R", "callback_data": "graph_refresh"},
                {"text": "1h", "callback_data": "graph_period_3600"},
                {"text": "3h", "callback_data": "graph_period_10800"},
                {"text": "6h", "callback_data": "graph_period_21600"},
                {"text": "12h", "callback_data": "graph_period_43200"},
                {"text": "24h", "callback_data": "graph_period_86400"},
            ]]})
        else:
            reply_markup = json.dumps({})
        params = {
            "chat_id": chat_id,
            "caption": text,
            "disable_notification": self.disable_notification,
            "reply_markup": reply_markup,
        }
        if self.reply_to_message_id:
            params["reply_to_message_id"] = self.reply_to_message_id
        if self.message_thread_id:
            params["message_thread_id"] = self.message_thread_id
        with open(path, "rb") as fd:
            files = {"photo": fd}
            self.logger.debug("POST sendPhoto params=%s file=%s", params, path)
            answer = self.session.post(self._url("sendPhoto"), params=params, files=files, proxies=self.proxies)
        self.result = answer.json()
        self._update_status()
        return self.result

    def send_document(self, chat_id, text: List[str], file_name: Optional[str] = None) -> dict:
        if not self.tmp_dir:
            raise RuntimeError("tmp_dir must be set before calling send_document()")
        path = os.path.join(self.tmp_dir, "zbxtg_txt_")
        if not file_name:
            path += "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
        else:
            path += file_name
        path += ".txt"
        with open(path, "w") as fd:
            fd.write("\n".join(text))
        params = {
            "chat_id": chat_id,
            "caption": os.path.basename(path),
            "disable_notification": self.disable_notification,
        }
        if self.reply_to_message_id:
            params["reply_to_message_id"] = self.reply_to_message_id
        if self.message_thread_id:
            params["message_thread_id"] = self.message_thread_id
        with open(path, "rb") as fd:
            files = {"document": fd}
            self.logger.debug("POST sendDocument params=%s file=%s", params, path)
            answer = self.session.post(self._url("sendDocument"), params=params, files=files, proxies=self.proxies)
        self.result = answer.json()
        self._update_status()
        return self.result

    def send_location(self, chat_id, latitude, longitude) -> dict:
        params = {
            "chat_id": chat_id,
            "disable_notification": self.disable_notification,
            "latitude": latitude,
            "longitude": longitude,
        }
        if self.reply_to_message_id:
            params["reply_to_message_id"] = self.reply_to_message_id
        if self.message_thread_id:
            params["message_thread_id"] = self.message_thread_id
        self.logger.debug("POST sendLocation params=%s", params)
        answer = self.session.post(self._url("sendLocation"), params=params, proxies=self.proxies)
        self.result = answer.json()
        self._update_status()
        return self.result

    def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> dict:
        params = {"callback_query_id": callback_query_id}
        if text:
            params["text"] = text
        answer = self.session.post(self._url("answerCallbackQuery"), params=params, proxies=self.proxies)
        self.result = answer.json()
        self._update_status()
        return self.result

    # -- chat id resolution ----------------------------------------------

    def find_chat_id(self, name: str) -> Optional[str]:
        """Scan recent updates for a chat matching `name` (username or group title)."""
        self.logger.debug("Resolving chat id for '%s' via getUpdates", name)
        updates = self.get_updates()
        for item in updates.get("result", []):
            message = item.get("message") or item.get("edited_message")
            if not message:
                continue
            chat = message["chat"]
            if chat["type"] == "private" and self.chat_type == "private":
                if chat.get("username") == name:
                    return str(chat["id"])
            if chat["type"] in ("group", "supergroup") and self.chat_type == "group":
                if chat.get("title") == name:
                    return str(chat["id"])
        return None

    def explain_contact_requirement(self, name: str) -> None:
        if self.chat_type == "private":
            self.logger.error("User '%s' needs to send the bot a message in private first (e.g. /start)", name)
        if self.chat_type == "group":
            bot_username = self.get_me().get("result", {}).get("username", "your_bot")
            self.logger.error(
                "Start a conversation with the bot in the '%s' group chat first: /start@%s", name, bot_username
            )

    def _add_parse_mode(self, params: dict) -> None:
        if self.markdown or self.html:
            params["parse_mode"] = "Markdown" if self.markdown else "HTML"
