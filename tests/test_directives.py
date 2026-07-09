# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zbxtg_lib import directives  # noqa: E402


def test_parse_message_separates_text_and_directives():
    body = [
        "Last value: 42 (2026-07-08 10:00:00)",
        "zbxtg;graphs",
        "zbxtg;itemid:111,222",
        "zbxtg;title:My Host - My Trigger",
    ]
    settings, text_lines, unknown = directives.parse_message(body)
    assert text_lines == ["Last value: 42 (2026-07-08 10:00:00)"]
    assert unknown == []
    assert settings.graphs is True
    assert settings.itemid == ["111", "222"]
    assert settings.title == "My Host - My Trigger"


def test_parse_message_bool_directive_without_value():
    settings, _, _ = directives.parse_message(["zbxtg;debug"])
    assert settings.debug is True


def test_parse_message_int_directive():
    settings, _, _ = directives.parse_message(["zbxtg;graphs_period=10800"])
    assert settings.graphs_period == 10800
    assert isinstance(settings.graphs_period, int)


def test_parse_message_unknown_directive_is_reported_not_raised():
    settings, text_lines, unknown = directives.parse_message(["zbxtg;not_a_real_directive:1"])
    assert unknown == ["not_a_real_directive"]
    assert text_lines == []


def test_parse_message_custom_prefix():
    settings, text_lines, unknown = directives.parse_message(["myprefix;debug"], prefix="myprefix")
    assert settings.debug is True


def test_run_settings_defaults_match_expected_shape():
    settings = directives.RunSettings()
    d = settings.as_dict()
    assert d["itemid"] == ["0"]
    assert d["graphs"] is False
    assert d["forked"] is False


def test_features_help_text_lists_all_directives():
    text = directives.features_help_text()
    for key in directives.DIRECTIVES:
        assert key in text
