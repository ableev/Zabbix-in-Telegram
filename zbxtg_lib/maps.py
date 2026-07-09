# -*- coding: utf-8 -*-
"""Address -> coordinates lookup via the Google Geocoding API.

Used for the `zbxtg;location:` directive.
https://developers.google.com/maps/documentation/geocoding/intro
"""
from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import requests


class Maps:
    GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self, api_key: Optional[str] = None, logger: Optional[logging.Logger] = None) -> None:
        self.api_key = api_key
        self.logger = logger or logging.getLogger("zbxtg")
        self.proxies: Dict[str, str] = {}

    def get_coordinates_by_address(self, address: str) -> Optional[Tuple[float, float]]:
        if not self.api_key:
            self.logger.warning("google_maps.api_key is not configured; cannot resolve '%s'", address)
            return None
        params = {"key": self.api_key, "address": address}
        answer = requests.get(self.GEOCODE_URL, params=params, proxies=self.proxies)
        result = answer.json()
        results = result.get("results") or []
        if not results:
            if "error_message" in result:
                self.logger.error("[%s]: %s", result.get("status"), result["error_message"])
            return None
        location = results[0]["geometry"]["location"]
        return location["lat"], location["lng"]
