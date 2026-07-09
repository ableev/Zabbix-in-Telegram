# -*- coding: utf-8 -*-
"""Configuration loading for zbxtg.

Configuration now lives in ``zbxtg_settings.yaml`` (see
``zbxtg_settings.example.yaml`` for the documented template). For
installations that haven't migrated yet, a legacy ``zbxtg_settings.py``
next to the script is still picked up automatically, with a deprecation
warning logged.
"""
from __future__ import annotations

import importlib.util
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger("zbxtg")


class ConfigError(Exception):
    """Raised when zbxtg_settings.yaml (or the legacy .py config) is missing or invalid."""


@dataclass
class TelegramConfig:
    bot_token: str = ""
    proxy: Optional[str] = None
    signature_enabled: bool = False
    signature_text: Optional[str] = None


@dataclass
class DirectivesConfig:
    prefix: str = "zbxtg"
    update_existing_messages: bool = True
    status_labels: Dict[str, str] = field(
        default_factory=lambda: {"problem": "PROBLEM: ", "ok": "OK: "}
    )


@dataclass
class ZabbixApiConfig:
    username: str = "api"
    password: str = "api"
    verify_tls: bool = True
    # Optional: Zabbix 6.4+ API token. When set, it's used as an
    # "Authorization: Bearer <token>" header for JSON-RPC calls instead of
    # calling user.login. Not required for graph fetching (see zabbix_web.py).
    token: Optional[str] = None


@dataclass
class ZabbixBasicAuthConfig:
    enabled: bool = False
    username: str = "zabbix"
    password: str = "zabbix"


@dataclass
class ZabbixDatabaseConfig:
    """Reserved for a future direct-DB integration. Unused today."""

    host: str = "localhost"
    name: str = "zabbix"
    user: str = "zbxtg"
    password: str = "zbxtg"


@dataclass
class ZabbixConfig:
    server: str = "http://127.0.0.1/zabbix/"
    version: int = 7
    api: ZabbixApiConfig = field(default_factory=ZabbixApiConfig)
    basic_auth: ZabbixBasicAuthConfig = field(default_factory=ZabbixBasicAuthConfig)
    proxy: Optional[str] = None
    database: ZabbixDatabaseConfig = field(default_factory=ZabbixDatabaseConfig)


@dataclass
class DaemonConfig:
    """Settings consumed by the experimental ZbxTgDaemon.py, kept for compatibility."""

    enabled: bool = False
    allowed_chat_ids: List[int] = field(default_factory=list)
    allowed_usernames: List[str] = field(default_factory=list)
    allowed_chat_titles: List[str] = field(default_factory=list)


@dataclass
class GoogleMapsConfig:
    api_key: Optional[str] = None


@dataclass
class RuntimeConfig:
    tmp_dir: str = "/var/tmp/zbxtg"


DEFAULT_EMOJI_MAP: Dict[str, str] = {
    "Disaster": "\U0001F525",
    "High": "\U0001F6D1",
    "Average": "❗",
    "Warning": "⚠️",
    "Information": "ℹ️",
    "Not classified": "\U0001F518",
    "OK": "✅",
    "PROBLEM": "❗",
    "info": "ℹ️",
    "WARNING": "⚠️",
    "DISASTER": "❌",
    "bomb": "\U0001F4A3",
    "fire": "\U0001F525",
    "hankey": "\U0001F4A9",
}


@dataclass
class Config:
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    directives: DirectivesConfig = field(default_factory=DirectivesConfig)
    zabbix: ZabbixConfig = field(default_factory=ZabbixConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    google_maps: GoogleMapsConfig = field(default_factory=GoogleMapsConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    emoji_map: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_EMOJI_MAP))

    def validate(self) -> None:
        if not self.telegram.bot_token or self.telegram.bot_token in ("XYZ", ""):
            raise ConfigError(
                "telegram.bot_token is not set. Copy zbxtg_settings.example.yaml to "
                "zbxtg_settings.yaml and fill in your bot token."
            )


def _build_config(raw: Dict[str, Any]) -> Config:
    telegram_raw = raw.get("telegram", {}) or {}
    telegram = TelegramConfig(
        bot_token=telegram_raw.get("bot_token", ""),
        proxy=telegram_raw.get("proxy"),
        signature_enabled=bool((telegram_raw.get("signature") or {}).get("enabled", False)),
        signature_text=(telegram_raw.get("signature") or {}).get("text"),
    )

    directives_raw = raw.get("directives", {}) or {}
    directives = DirectivesConfig(
        prefix=directives_raw.get("prefix", "zbxtg"),
        update_existing_messages=directives_raw.get("update_existing_messages", True),
        status_labels=directives_raw.get(
            "status_labels", {"problem": "PROBLEM: ", "ok": "OK: "}
        ),
    )

    zabbix_raw = raw.get("zabbix", {}) or {}
    api_raw = zabbix_raw.get("api", {}) or {}
    basic_auth_raw = zabbix_raw.get("basic_auth", {}) or {}
    database_raw = zabbix_raw.get("database", {}) or {}
    zabbix = ZabbixConfig(
        server=zabbix_raw.get("server", "http://127.0.0.1/zabbix/"),
        version=int(zabbix_raw.get("version", 7)),
        api=ZabbixApiConfig(
            username=api_raw.get("username", "api"),
            password=api_raw.get("password", "api"),
            verify_tls=api_raw.get("verify_tls", True),
            token=api_raw.get("token"),
        ),
        basic_auth=ZabbixBasicAuthConfig(
            enabled=basic_auth_raw.get("enabled", False),
            username=basic_auth_raw.get("username", "zabbix"),
            password=basic_auth_raw.get("password", "zabbix"),
        ),
        proxy=zabbix_raw.get("proxy"),
        database=ZabbixDatabaseConfig(
            host=database_raw.get("host", "localhost"),
            name=database_raw.get("name", "zabbix"),
            user=database_raw.get("user", "zbxtg"),
            password=database_raw.get("password", "zbxtg"),
        ),
    )

    daemon_raw = raw.get("daemon", {}) or {}
    daemon = DaemonConfig(
        enabled=daemon_raw.get("enabled", False),
        allowed_chat_ids=daemon_raw.get("allowed_chat_ids", []),
        allowed_usernames=daemon_raw.get("allowed_usernames", []),
        allowed_chat_titles=daemon_raw.get("allowed_chat_titles", []),
    )

    google_maps_raw = raw.get("google_maps", {}) or {}
    google_maps = GoogleMapsConfig(api_key=google_maps_raw.get("api_key"))

    runtime_raw = raw.get("runtime", {}) or {}
    runtime = RuntimeConfig(tmp_dir=runtime_raw.get("tmp_dir", "/var/tmp/zbxtg"))

    emoji_map = raw.get("emoji_map") or dict(DEFAULT_EMOJI_MAP)

    return Config(
        telegram=telegram,
        directives=directives,
        zabbix=zabbix,
        daemon=daemon,
        google_maps=google_maps,
        runtime=runtime,
        emoji_map=emoji_map,
    )


def load_from_yaml(path: str) -> Config:
    with open(path, "r") as fd:
        raw = yaml.safe_load(fd) or {}
    if not isinstance(raw, dict):
        raise ConfigError("{0} does not contain a YAML mapping at the top level".format(path))
    return _build_config(raw)


def load_from_legacy_py(path: str) -> Config:
    """Load the old flat-variable zbxtg_settings.py, for backward compatibility."""
    logger.warning(
        "Loading legacy %s. Please migrate to zbxtg_settings.yaml "
        "(see zbxtg_settings.example.yaml) -- .py config support will be removed "
        "in a future release.",
        path,
    )
    spec = importlib.util.spec_from_file_location("zbxtg_settings_legacy", path)
    if spec is None or spec.loader is None:
        raise ConfigError("Could not load legacy config from {0}".format(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    raw: Dict[str, Any] = {
        "telegram": {
            "bot_token": getattr(module, "tg_key", ""),
            "proxy": getattr(module, "proxy_to_tg", None),
            "signature": {
                "enabled": getattr(module, "zbx_tg_signature", False),
                "text": None,
            },
        },
        "directives": {
            "prefix": getattr(module, "zbx_tg_prefix", "zbxtg"),
            "update_existing_messages": getattr(module, "zbx_tg_update_messages", True),
            "status_labels": getattr(
                module, "zbx_tg_matches", {"problem": "PROBLEM: ", "ok": "OK: "}
            ),
        },
        "zabbix": {
            "server": getattr(module, "zbx_server", "http://127.0.0.1/zabbix/"),
            "version": getattr(module, "zbx_server_version", 7),
            "api": {
                "username": getattr(module, "zbx_api_user", "api"),
                "password": getattr(module, "zbx_api_pass", "api"),
                "verify_tls": getattr(module, "zbx_api_verify", True),
            },
            "basic_auth": {
                "enabled": getattr(module, "zbx_basic_auth", False),
                "username": getattr(module, "zbx_basic_auth_user", "zabbix"),
                "password": getattr(module, "zbx_basic_auth_pass", "zabbix"),
            },
            "proxy": getattr(module, "proxy_to_zbx", None),
            "database": {
                "host": getattr(module, "zbx_db_host", "localhost"),
                "name": getattr(module, "zbx_db_database", "zabbix"),
                "user": getattr(module, "zbx_db_user", "zbxtg"),
                "password": getattr(module, "zbx_db_password", "zbxtg"),
            },
        },
        "daemon": {
            "enabled": getattr(module, "zbx_tg_daemon_enabled", False),
            "allowed_chat_ids": getattr(module, "zbx_tg_daemon_enabled_ids", []),
            "allowed_usernames": getattr(module, "zbx_tg_daemon_enabled_users", []),
            "allowed_chat_titles": getattr(module, "zbx_tg_daemon_enabled_chats", []),
        },
        "google_maps": {"api_key": getattr(module, "google_maps_api_key", None)},
        "runtime": {"tmp_dir": getattr(module, "zbx_tg_tmp_dir", "/var/tmp/zbxtg")},
        "emoji_map": getattr(module, "emoji_map", dict(DEFAULT_EMOJI_MAP)),
    }
    return _build_config(raw)


def find_config_path(base_dir: str) -> Optional[str]:
    """Return the first config file found, preferring YAML over the legacy .py format."""
    env_path = os.environ.get("ZBXTG_CONFIG")
    if env_path and os.path.isfile(env_path):
        return env_path
    yaml_path = os.path.join(base_dir, "zbxtg_settings.yaml")
    if os.path.isfile(yaml_path):
        return yaml_path
    yml_path = os.path.join(base_dir, "zbxtg_settings.yml")
    if os.path.isfile(yml_path):
        return yml_path
    legacy_path = os.path.join(base_dir, "zbxtg_settings.py")
    if os.path.isfile(legacy_path):
        return legacy_path
    return None


def load_config(base_dir: Optional[str] = None) -> Config:
    """Locate and load zbxtg_settings.(yaml|py) from base_dir (defaults to this file's directory's parent)."""
    base_dir = base_dir or os.getcwd()
    path = find_config_path(base_dir)
    if path is None:
        raise ConfigError(
            "No configuration found. Copy zbxtg_settings.example.yaml to "
            "zbxtg_settings.yaml in {0} and fill in your settings.".format(base_dir)
        )
    if path.endswith(".py"):
        config = load_from_legacy_py(path)
    else:
        config = load_from_yaml(path)
    config.validate()
    return config
