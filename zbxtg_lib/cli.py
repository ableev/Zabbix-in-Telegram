# -*- coding: utf-8 -*-
"""Entry-point logic for zbxtg.py / zbxtg_group.py.

This is a direct, module-based port of the original single-file script.
The external contract is unchanged on purpose: same CLI invocation
(`zbxtg.py TO SUBJECT BODY [flags]`), same `zbxtg;key:value` directives in
the message body, same `--forked`/multi-recipient behaviour, same uid
cache file format. Existing Zabbix Media types and Actions keep working
without changes.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
from typing import Dict, List, Optional

from . import directives
from .config import Config, ConfigError, load_config
from .maps import Maps
from .telegram_api import TelegramAPI
from .utils import UidCache, age2sec, apply_emoji_map, get_logger, list_cut, markdown_fix
from .zabbix_web import ZabbixWeb, external_image_get

GITHUB_URL = "https://github.com/ableev/Zabbix-in-Telegram"
WIKI_URL = GITHUB_URL + "/wiki"
TG_GROUP_URL = "https://t.me/ZbxTg"
TG_CHANNEL_URL = "https://t.me/Zabbix_in_Telegram"

USAGE = (
    "Hi. You should provide at least three arguments.\n"
    "zbxtg.py [TO] [SUBJECT] [BODY]\n\n"
    "1. Read the main page and/or the wiki: {0} + {1}\n"
    "2. Public Telegram discussion group: {2}\n"
    "3. Public Telegram channel: {3}\n"
    "4. Try the dev branch for testing new features: {0}/tree/dev"
).format(GITHUB_URL, WIKI_URL, TG_GROUP_URL, TG_CHANNEL_URL)

TO_TYPES = ("to", "to_group", "to_channel")
TO_TYPE_TO_CHAT_TYPE = {"to": "private", "to_group": "group", "to_channel": "channel"}


def _script_dir(script_path: str) -> str:
    return os.path.dirname(os.path.abspath(script_path))


def _split_recipients(settings: directives.RunSettings) -> Dict[str, List[str]]:
    multiple_to: Dict[str, List[str]] = {t: [] for t in TO_TYPES}
    if settings.forked:
        return multiple_to
    for attr in ("to", "to_group"):
        value = getattr(settings, attr)
        if value:
            multiple_to[attr] = re.split(",", value)
    return multiple_to


def _fork_for_recipients(args: List[str], multiple_to: Dict[str, List[str]], logger) -> None:
    for to_type, recipients in multiple_to.items():
        for recipient in recipients:
            new_args = list(args)
            new_args[1] = recipient
            if to_type == "to_group":
                new_args.append("--group")
            new_args.append("--forked")
            new_args.insert(0, sys.executable)
            logger.debug("Forking for recipient '%s' (%s): %s", recipient, TO_TYPE_TO_CHAT_TYPE[to_type], new_args)
            subprocess.call(new_args)


def main(argv: Optional[List[str]] = None) -> int:
    args = list(argv if argv is not None else sys.argv)

    if len(args) < 4:
        if "--features" in args:
            print(directives.features_help_text())
            return 0
        if "--show-settings" in args:
            print("Settings: {0}".format(directives.RunSettings().as_dict()))
            return 0
        print(USAGE)
        return 0

    try:
        config = load_config(_script_dir(args[0]))
    except ConfigError as exc:
        sys.stderr.write("zbxtg: configuration error: {0}\n".format(exc))
        return 1

    is_debug = "--debug" in args
    logger = get_logger(debug=is_debug)

    tmp_dir = config.runtime.tmp_dir
    if tmp_dir == "/tmp/" + config.directives.prefix:
        logger.warning("It is strongly recommended to change 'runtime.tmp_dir' in your config.")
        logger.warning("%s/Change-zbx_tg_tmp_dir-in-settings", WIKI_URL)

    if not os.path.isdir(tmp_dir):
        try:
            os.makedirs(tmp_dir)
            os.chmod(tmp_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except OSError:
            logger.warning("Could not create '%s', falling back to /tmp", tmp_dir)
            tmp_dir = "/tmp"

    tmp_uids_path = os.path.join(tmp_dir, "uids.txt")
    uid_cache = UidCache(tmp_uids_path, logger=logger)
    uid_cache.ensure_exists()

    zbx_to, zbx_subject, zbx_body = args[1], args[2], args[3]

    tg = TelegramAPI(config.telegram.bot_token, logger=logger)
    tg.tmp_dir = tmp_dir
    if "--tg-key" in args:
        tg.token = args[args.index("--tg-key") + 1]
    if config.telegram.proxy:
        proxy = config.telegram.proxy
        if not proxy.startswith(("http", "socks")):
            proxy = "https://" + proxy
        tg.proxies = {"https": proxy}

    zbx = ZabbixWeb(config.zabbix.server, config.zabbix.api.username, config.zabbix.api.password, logger=logger)
    zbx.tmp_dir = tmp_dir
    zbx.verify = config.zabbix.api.verify_tls
    if config.zabbix.basic_auth.enabled:
        zbx.basic_auth_user = config.zabbix.basic_auth.username
        zbx.basic_auth_pass = config.zabbix.basic_auth.password
    if config.zabbix.proxy:
        zbx.proxies = {
            "http": "http://{0}/".format(config.zabbix.proxy),
            "https": "https://{0}/".format(config.zabbix.proxy),
        }

    maps = Maps(api_key=config.google_maps.api_key, logger=logger)
    if config.telegram.proxy:
        maps.proxies = tg.proxies

    body_lines = (zbx_subject + "\n" + zbx_body).splitlines()
    settings, text_lines, unknown_keys = directives.parse_message(body_lines, prefix=config.directives.prefix)

    for key in unknown_keys:
        logger.error("There is no '%s' directive, use --features to list available ones", key)

    if args[0].split("/")[-1] == "zbxtg_group.py" or "--group" in args or settings.chat or settings.group:
        settings.group = True
        tg.chat_type = "group"

    if is_debug:
        settings.debug = True
        tg.logger.debug("Bot identity: %s", tg.get_me())
        tg.logger.debug("uid cache file: %s", tmp_uids_path)

    if "--markdown" in args or settings.markdown:
        tg.markdown = True
    if "--html" in args or settings.html:
        tg.html = True
    if "--channel" in args or settings.channel:
        tg.chat_type = "channel"
    if "--disable_web_page_preview" in args or settings.disable_web_page_preview:
        tg.disable_web_page_preview = True
    if "--graph_buttons" in args or settings.graph_buttons:
        tg.image_buttons = True
    if "--topic-id" in args:
        settings.topic_id = int(args[args.index("--topic-id") + 1])
    if "--topic" in args:
        settings.topic_id = int(args[args.index("--topic") + 1])
    if "--forked" in args:
        settings.forked = True

    location_coordinates = None
    if settings.lat and settings.lon:
        location_coordinates = (float(settings.lat), float(settings.lon))
    elif settings.location:
        location_coordinates = maps.get_coordinates_by_address(settings.location)

    # Multiple explicit recipients (`to`/`to_group`) are handled by forking one
    # subprocess per recipient, then exiting -- kept from the original design.
    multiple_to = _split_recipients(settings)
    total_recipients = sum(len(v) for v in multiple_to.values())
    if total_recipients == 1:
        for to_type, recipients in multiple_to.items():
            if recipients:
                zbx_to = recipients[0]
                tg.chat_type = TO_TYPE_TO_CHAT_TYPE[to_type]
    elif total_recipients > 1:
        _fork_for_recipients(args, multiple_to, logger)
        return 0

    uid: Optional[str] = None
    if tg.chat_type == "channel":
        uid = zbx_to
    if tg.chat_type == "private":
        zbx_to = zbx_to.replace("@", "")
    if zbx_to.isdigit():
        uid = zbx_to
    if not uid:
        cached = uid_cache.get(zbx_to, tg.chat_type)
        uid = cached if cached != "0" else None
    need_cache_update = False
    if not uid:
        uid = tg.find_chat_id(zbx_to)
        need_cache_update = uid is not None
    if not uid:
        tg.explain_contact_requirement(zbx_to)
        return 1
    if need_cache_update:
        uid_cache.update(zbx_to, tg.chat_type, uid)

    logger.debug("Telegram uid of %s '%s': %s", tg.chat_type, zbx_to, uid)

    if config.telegram.signature_enabled or "--signature" in args or settings.signature:
        if not settings.signature_disable and "--signature_disable" not in args:
            if "--signature" in args:
                settings.signature = args[args.index("--signature") + 1]
            signature_text = settings.signature or config.telegram.signature_text or config.zabbix.server
            text_lines.append("--")
            text_lines.append(signature_text)

    text_lines, used_emoji = apply_emoji_map(text_lines, config.emoji_map)

    if settings.topic_id is not None:
        tg.message_thread_id = settings.topic_id

    if not settings.single_message:
        tg.send_message(uid, text_lines)
        if not tg.ok:
            _retry_after_migration(tg, uid_cache, zbx_to, text_lines, logger)
            _retry_after_markdown_error(tg, text_lines, used_emoji, logger)

    message_id = 0
    if tg.ok and tg.result:
        message_id = tg.result.get("result", {}).get("message_id", 0)

    if settings.graphs_age:
        age_sec = age2sec(settings.graphs_age)
        if age_sec > 3600:
            settings.graphs_period = age_sec

    if settings.graphs:
        message_id = _send_graph(zbx, tg, uid, settings, text_lines, message_id, logger)

    if location_coordinates:
        tg.reply_to_message_id = message_id
        tg.disable_notification = True
        tg.send_location(uid, location_coordinates[0], location_coordinates[1])

    if "--show-settings" in args:
        print("Settings: {0}".format(settings.as_dict()))

    return 0


def _retry_after_migration(tg: TelegramAPI, uid_cache: UidCache, zbx_to: str, text_lines: List[str], logger) -> None:
    if not tg.error or "migrated" not in tg.error or "supergroup" not in tg.error:
        return
    migrate_to_chat_id = tg.result["parameters"]["migrate_to_chat_id"]
    uid_cache.update(zbx_to, tg.chat_type, migrate_to_chat_id, message="Group migrated to supergroup, updating cache")
    tg.send_message(migrate_to_chat_id, text_lines)


def _retry_after_markdown_error(tg: TelegramAPI, text_lines: List[str], used_emoji: bool, logger) -> None:
    if not (tg.markdown and tg.error and "Can't find end of the entity starting at byte offset" in tg.error):
        return
    warning = (
        "Original message has been fixed because of a Markdown parsing error. "
        "Please fix the Markdown -- it slows down message delivery. "
        "{0}/Markdown-and-HTML".format(WIKI_URL)
    )
    attempts = 0
    uid = tg.result.get("parameters", {}).get("chat_id") if tg.result else None
    while not tg.ok and attempts < 3:
        match = re.search(r"Can't find end of the entity starting at byte offset ([0-9]+)", tg.error or "")
        if not match:
            break
        text_lines = markdown_fix(text_lines, match.group(1), emoji=used_emoji) + ["\n", warning]
        tg.disable_web_page_preview = True
        tg.send_message(uid, text_lines)
        attempts += 1
    if tg.ok:
        logger.warning(warning)


def _send_graph(zbx: ZabbixWeb, tg: TelegramAPI, uid: str, settings: directives.RunSettings,
                 text_lines: List[str], message_id: int, logger) -> int:
    if settings.external_image:
        # An external image doesn't need a Zabbix session at all -- skip the
        # frontend login entirely so this path works even without valid
        # Zabbix credentials configured.
        file_img = external_image_get(settings.external_image, zbx.tmp_dir, logger=logger)
    else:
        if not zbx.login():
            warning = "Login to the Zabbix web UI failed (check server URL, user or password); sending graphs manually is required."
            tg.send_message(uid, [warning])
            logger.error(warning)
            return message_id
        file_img = zbx.graph_get(settings.itemid, settings.graphs_period, settings.title,
                                  settings.graphs_width, settings.graphs_height)

    caption, was_cut = list_cut(text_lines, 200)
    if tg.ok and tg.result:
        message_id = tg.result.get("result", {}).get("message_id", message_id)
    tg.reply_to_message_id = message_id

    if not file_img:
        warning = "Could not fetch the graph image; check the script logs, or disable graphs."
        tg.send_message(uid, [warning])
        logger.error(warning)
        return message_id

    if not settings.single_message:
        caption = []
        tg.disable_notification = True
    elif was_cut:
        logger.warning(
            "Message was cut to 200 symbols to avoid MEDIA_CAPTION_TOO_LONG: "
            "%s/Settings#markdown-and-html", WIKI_URL
        )

    tg.send_photo(uid, caption, file_img)
    if tg.ok:
        os.remove(file_img)
        if tg.result:
            message_id = tg.result.get("result", {}).get("message_id", message_id)
    elif tg.error and "PHOTO_INVALID_DIMENSIONS" in tg.error:
        tg.disable_web_page_preview = True
        warning = (
            "The Zabbix user likely lacks permission to read this host's data; "
            "check manually. {0}/Graphs".format(WIKI_URL)
        )
        tg.send_message(uid, [warning])
        logger.error(warning)

    return message_id


if __name__ == "__main__":
    sys.exit(main())
