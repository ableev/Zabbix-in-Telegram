# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zbxtg_lib.utils import (  # noqa: E402
    UidCache,
    age2sec,
    apply_emoji_map,
    list_cut,
    markdown_fix,
)


def test_age2sec_days_hours_minutes():
    assert age2sec("1d") == 86400
    assert age2sec("2h") == 7200
    assert age2sec("30m") == 1800
    assert age2sec("1d 2h 30m") == 86400 + 7200 + 1800


def test_age2sec_empty():
    assert age2sec("") == 0


def test_list_cut_under_limit():
    elements = ["a", "bb", "ccc"]
    result, was_cut = list_cut(elements, 100)
    assert result == elements
    assert was_cut is False


def test_list_cut_over_limit_truncates():
    elements = ["hello", "world", "this is long"]
    result, was_cut = list_cut(elements, 8)
    assert was_cut is True
    assert "".join(result) != "".join(elements)
    assert len("".join(result)) <= 8 + len(result)  # separators tolerance


def test_markdown_fix_removes_offending_byte():
    # "hello *world" -> index 6 is the stray '*' Telegram choked on.
    message = ["hello *world"]
    fixed = markdown_fix(message, offset=6, emoji=False)
    assert fixed == ["hello world"]


def test_markdown_fix_applies_emoji_offset_correction():
    message = ["hello **world"]
    fixed_no_emoji = markdown_fix(message, offset=8, emoji=False)
    fixed_emoji = markdown_fix(message, offset=8, emoji=True)
    # the emoji correction shifts which byte gets dropped
    assert fixed_no_emoji != fixed_emoji


def test_apply_emoji_map_replaces_and_reports_change():
    lines = ["Status: {{OK}}"]
    new_lines, changed = apply_emoji_map(lines, {"OK": "✅"})
    assert new_lines == ["Status: ✅"]
    assert changed is True


def test_apply_emoji_map_no_placeholder_no_change():
    lines = ["nothing to replace here"]
    new_lines, changed = apply_emoji_map(lines, {"OK": "✅"})
    assert new_lines == lines
    assert changed is False


def test_uid_cache_roundtrip(tmp_path):
    cache_path = str(tmp_path / "uids.txt")
    cache = UidCache(cache_path)
    cache.ensure_exists()
    assert cache.get("someuser", "private") == "0"

    cache.update("someuser", "private", "12345")
    assert cache.get("someuser", "private") == "12345"
    # a different chat type for the same name must not match
    assert cache.get("someuser", "group") == "0"


def test_uid_cache_missing_file_returns_zero(tmp_path):
    cache = UidCache(str(tmp_path / "does_not_exist.txt"))
    assert cache.get("anyone", "private") == "0"
