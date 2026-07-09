# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from zbxtg_lib.config import ConfigError, load_config, load_from_yaml  # noqa: E402

MINIMAL_YAML = """
telegram:
  bot_token: "123:ABC"
zabbix:
  server: "http://zabbix.example.com/zabbix"
"""

LEGACY_PY = '''# -*- coding: utf-8 -*-
tg_key = "123:ABC"
zbx_server = "http://zabbix.example.com/zabbix"
zbx_api_user = "api"
zbx_api_pass = "secret"
zbx_tg_tmp_dir = "/var/tmp/zbxtg"
'''


def test_load_from_yaml_applies_defaults(tmp_path):
    config_path = tmp_path / "zbxtg_settings.yaml"
    config_path.write_text(MINIMAL_YAML)
    config = load_from_yaml(str(config_path))
    assert config.telegram.bot_token == "123:ABC"
    assert config.zabbix.server == "http://zabbix.example.com/zabbix"
    # untouched sections fall back to dataclass defaults
    assert config.zabbix.api.username == "api"
    assert config.runtime.tmp_dir == "/var/tmp/zbxtg"
    assert "Disaster" in config.emoji_map


def test_load_config_prefers_yaml_over_legacy_py(tmp_path):
    (tmp_path / "zbxtg_settings.yaml").write_text(MINIMAL_YAML)
    (tmp_path / "zbxtg_settings.py").write_text(LEGACY_PY.replace("123:ABC", "999:SHOULD_NOT_LOAD"))
    config = load_config(str(tmp_path))
    assert config.telegram.bot_token == "123:ABC"


def test_load_config_falls_back_to_legacy_py(tmp_path):
    (tmp_path / "zbxtg_settings.py").write_text(LEGACY_PY)
    config = load_config(str(tmp_path))
    assert config.telegram.bot_token == "123:ABC"
    assert config.zabbix.api.password == "secret"


def test_load_config_missing_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(str(tmp_path))


def test_validate_rejects_placeholder_token(tmp_path):
    config_path = tmp_path / "zbxtg_settings.yaml"
    config_path.write_text("telegram:\n  bot_token: \"XYZ\"\n")
    with pytest.raises(ConfigError):
        load_config(str(tmp_path))
