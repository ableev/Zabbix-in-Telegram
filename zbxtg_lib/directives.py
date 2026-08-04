# -*- coding: utf-8 -*-
"""Parsing of inline ``zbxtg;key:value`` directives out of a Zabbix message body.

The directive names, types and CLI flags here are a stable interface --
existing Zabbix actions already embed lines like ``zbxtg;graphs_period=10800``
in their message templates, so nothing here may be renamed without breaking
those installations. See README.md#annotations for the user-facing docs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional, Tuple

WIKI_BASE = "https://github.com/ableev/Zabbix-in-Telegram/wiki"


@dataclass
class Directive:
    attr: str
    type: str  # "str" | "int" | "bool" | "list"
    help: str
    wiki_page: str


# directive name (as used after the prefix, e.g. "zbxtg;graphs") -> Directive
DIRECTIVES: Dict[str, Directive] = {
    "itemid": Directive("itemid", "list", "attach a graph for this itemid (repeatable)", "Graphs"),
    "title": Directive("title", "str", "title for the attached graph", "Graphs"),
    "graphs_period": Directive("graphs_period", "int", "graph period, in seconds", "Graphs"),
    "graphs_age": Directive("graphs_age", "str", "graph period expressed as an age (e.g. 2h30m)", "Graphs"),
    "graphs_width": Directive("graphs_width", "int", "graph width in pixels", "Graphs"),
    "graphs_height": Directive("graphs_height", "int", "graph height in pixels", "Graphs"),
    "graphs": Directive("graphs", "bool", "enable graph attachment", "Graphs"),
    "chat": Directive("chat", "bool", "deprecated, use 'group' instead", "How-to-send-message-to-the-group-chat"),
    "group": Directive("group", "bool", "send message to a group chat", "How-to-send-message-to-the-group-chat"),
    "debug": Directive("debug", "bool", "enable debug logging", "How-to-test-script-in-command-line"),
    "channel": Directive("channel", "bool", "send message to a channel", "Channel-support"),
    "disable_web_page_preview": Directive(
        "disable_web_page_preview", "bool", "disable link previews", "Disable-web-page-preview"
    ),
    "location": Directive("location", "str", "address to resolve into a map location", "Location"),
    "lat": Directive("lat", "str", "latitude (use together with 'lon')", "Location"),
    "lon": Directive("lon", "str", "longitude (use together with 'lat')", "Location"),
    "single_message": Directive(
        "single_message", "bool", "send text and graph as a single message", "Why-am-I-getting-two-messages-instead-of-one"
    ),
    "markdown": Directive("markdown", "bool", "enable Markdown formatting", "Markdown-and-HTML"),
    "html": Directive("html", "bool", "enable HTML formatting", "Markdown-and-HTML"),
    "signature": Directive("signature", "str", "override the bot's signature text", "Bot-signature"),
    "signature_disable": Directive("signature_disable", "bool", "disable the bot's signature", "Bot-signature"),
    "graph_buttons": Directive(
        "graph_buttons", "bool", "show period buttons under the graph (used by ZbxTgDaemon)", "Interactive-bot"
    ),
    "external_image": Directive(
        "external_image", "str", "attach an external image (URL) instead of a Zabbix graph", "External-image-as-graph"
    ),
    "to": Directive("to", "str", "override the recipient(s), comma separated", "Custom-to-and-to_group"),
    "to_group": Directive("to_group", "str", "override the recipient group(s), comma separated", "Custom-to-and-to_group"),
    "topic": Directive("topic_id", "int", "send message to a forum topic thread in a supergroup", "Forum-topic"),
    "topic_id": Directive("topic_id", "int", "send message to a forum topic thread in a supergroup", "Forum-topic"),
    "forked": Directive("forked", "bool", "internal use only, do not set this", ""),
}


@dataclass
class RunSettings:
    """Effective settings for one invocation: CLI defaults overlaid with directives."""

    itemid: List[str] = field(default_factory=lambda: ["0"])
    title: Optional[str] = None
    graphs_period: Optional[int] = None
    graphs_age: str = "3600"
    graphs_width: int = 900
    graphs_height: int = 200
    graphs: bool = False
    chat: bool = False
    group: bool = False
    debug: bool = False
    channel: bool = False
    disable_web_page_preview: bool = False
    location: Optional[str] = None
    lat: float = 0
    lon: float = 0
    single_message: bool = False
    markdown: bool = False
    html: bool = False
    signature: Optional[str] = None
    topic_id: Optional[int] = None
    signature_disable: bool = False
    graph_buttons: bool = False
    external_image: Optional[str] = None
    to: Optional[str] = None
    to_group: Optional[str] = None
    forked: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


def _coerce(directive: Directive, raw_value: Optional[str], current: Any) -> Any:
    if directive.type == "list":
        return raw_value.split(",") if raw_value is not None else current
    if raw_value is None or raw_value == "":
        return True if directive.type == "bool" else current
    if directive.type == "int":
        return int(raw_value)
    if directive.type == "bool":
        return True
    return raw_value


def parse_message(
    body_lines: List[str], prefix: str = "zbxtg"
) -> Tuple[RunSettings, List[str], List[str]]:
    """Split a message body into (settings, plain-text lines, unknown directive keys)."""
    settings = RunSettings()
    text_lines: List[str] = []
    unknown: List[str] = []

    for line in body_lines:
        if line.find(prefix) == -1:
            text_lines.append(line)
            continue
        parts = re.split(r"[\s:=]+", line, maxsplit=1)
        key = parts[0].replace(prefix + ";", "")
        directive = DIRECTIVES.get(key)
        if directive is None:
            unknown.append(key)
            continue
        raw_value = parts[1] if len(parts) > 1 and len(parts[1]) > 0 else None
        current = getattr(settings, directive.attr)
        setattr(settings, directive.attr, _coerce(directive, raw_value, current))

    return settings, text_lines, unknown


def features_help_text() -> str:
    lines = ["List of available settings, see {0}/Settings".format(WIKI_BASE), "---"]
    for key, directive in DIRECTIVES.items():
        lines.append("{0}: {1}\ndoc: {2}/{3}\n--".format(key, directive.help, WIKI_BASE, directive.wiki_page))
    return "\n".join(lines)
