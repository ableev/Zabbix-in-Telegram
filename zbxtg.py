#!/usr/bin/env python3
# coding: utf-8
"""Zabbix AlertScriptsPath entry point -- sends Zabbix notifications to Telegram.

Zabbix calls this file directly by path (see README.md), so its name and
location must not change. All the actual logic lives in the zbxtg_lib
package next to this file; zbxtg_group.py is a symlink to this same file
and is handled by checking argv[0] in zbxtg_lib.cli.

Usage: zbxtg.py [TO] [SUBJECT] [BODY] [flags]
Run with --features for the list of supported `zbxtg;key:value` directives.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zbxtg_lib.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
