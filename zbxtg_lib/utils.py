# -*- coding: utf-8 -*-
"""Small stateless helpers shared across zbxtg_lib.

The on-disk uid cache is intentionally kept as a plain ``name;type;id``
text file (see :class:`UidCache`) -- migrating it to sqlite3 is a separate,
future task.
"""
from __future__ import annotations

import logging
import os
import re
import sys
from typing import Dict, List, Tuple

LOG_FORMAT = "%(prog)s: %(message)s"


class _ProgFormatter(logging.Formatter):
    """Formats messages the same way the original script did: '<argv[0]>: message'."""

    def __init__(self) -> None:
        super().__init__(LOG_FORMAT)
        self.prog = os.path.basename(sys.argv[0]) if sys.argv else "zbxtg"

    def format(self, record: logging.LogRecord) -> str:
        record.prog = self.prog
        return super().format(record)


def get_logger(debug: bool = False, name: str = "zbxtg") -> logging.Logger:
    """Return a logger that writes to stderr, matching the historical output format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_ProgFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False
    return logger


def list_cut(elements: List[str], symbols_limit: int) -> Tuple[List[str], bool]:
    """Cut a list of text lines down to a total character budget.

    Returns the (possibly truncated) list and whether truncation happened.
    Used to stay under Telegram's photo-caption limit.
    """
    symbols_count = symbols_count_now = 0
    elements_new: List[str] = []
    element_last_list: List[str] = []
    for e in elements:
        symbols_count_now = symbols_count + len(e)
        if symbols_count_now > symbols_limit:
            limit_idx = symbols_limit - symbols_count
            for idx, ee in enumerate(e):
                if idx < limit_idx:
                    element_last_list.append(ee)
                else:
                    break
            break
        symbols_count = symbols_count_now + 1
        elements_new.append(e)
    if symbols_count_now < symbols_limit:
        return elements, False
    element_last = "".join(element_last_list)
    elements_new.append(element_last)
    return elements_new, True


def markdown_fix(message: List[str], offset, emoji: bool = False) -> List[str]:
    """Drop the single byte Telegram complained about, so Markdown parsing can retry.

    See https://github.com/ableev/Zabbix-in-Telegram/issues/152 for why the emoji
    offset needs an extra correction.
    """
    offset = int(offset)
    if emoji:
        offset -= 2
    joined = "\n".join(message)
    joined = joined[:offset] + joined[offset + 1:]
    return joined.split("\n")


_AGE_PATTERN = re.compile(r"([0-9]+d)?\s?([0-9]+h)?\s?([0-9]+m)?")


def age2sec(age_str: str) -> int:
    """Parse an age string like '1d 2h 30m' into seconds."""
    age_sec = 0
    match = _AGE_PATTERN.match(age_str)
    if not match:
        return 0
    for interval in match.groups():
        if not interval:
            continue
        metric = interval[-1]
        value = int(interval[:-1])
        if metric == "d":
            age_sec += value * 86400
        elif metric == "h":
            age_sec += value * 3600
        elif metric == "m":
            age_sec += value * 60
    return age_sec


def file_write(filename: str, text: str) -> None:
    with open(filename, "w") as fd:
        fd.write(str(text))


def file_bwrite(filename: str, data: bytes) -> None:
    with open(filename, "wb") as fd:
        fd.write(data)


def file_read(filename: str) -> List[str]:
    with open(filename, "r") as fd:
        return fd.readlines()


class UidCache:
    """Flat-file cache mapping (name, chat type) -> Telegram chat id.

    Kept as plain text on purpose (``name;type;id`` per line) -- moving this
    to sqlite3 is tracked as a separate follow-up task, not part of this
    rewrite.
    """

    def __init__(self, path: str, logger: logging.Logger | None = None) -> None:
        self.path = path
        self.logger = logger or logging.getLogger("zbxtg")

    def ensure_exists(self) -> None:
        if not os.path.isfile(self.path):
            open(self.path, "a").close()

    def get(self, name: str, chat_type: str) -> str:
        self.logger.debug("Trying to read cached uid for %s, %s, from %s", name, chat_type, self.path)
        if not os.path.isfile(self.path):
            return "0"
        with open(self.path, "r") as fd:
            lines = fd.readlines()
        for line in lines:
            parts = line.split(";")
            if len(parts) >= 3 and parts[0] == name and parts[1] == chat_type:
                return parts[2].rstrip()
        return "0"

    def update(self, name: str, chat_type: str, uid: str, message: str = "Add new string to cache file") -> None:
        cache_string = "{0};{1};{2}\n".format(name, chat_type, str(uid).rstrip())
        self.logger.debug("%s: %s", message, cache_string)
        with open(self.path, "a") as fd:
            fd.write(cache_string)


def apply_emoji_map(lines: List[str], emoji_map: Dict[str, str]) -> Tuple[List[str], bool]:
    """Replace ``{{key}}`` placeholders with emoji, per the configured map.

    Returns the transformed lines and whether any replacement actually changed
    the text (Telegram Markdown offsets need to know this, see issue #152).
    """
    new_lines = []
    for line in lines:
        new_line = line
        for key, value in emoji_map.items():
            new_line = new_line.replace("{{" + key + "}}", value)
        new_lines.append(new_line)
    changed = len("".join(lines)) != len("".join(new_lines))
    return new_lines, changed
