"""OSINT search service — API wrapper + intel extraction."""
from __future__ import annotations

import re
import time
import requests
from collections import defaultdict
from flask import current_app


SOURCE_BADGES: dict[str, str] = {
    "microsoft": "🪟", "facebook": "👤", "instagram": "📸", "google": "🔍",
    "snapchat": "👻", "roblox": "🎮", "apple": "🍎", "discord": "💬",
    "nintendo": "🕹️", "spotify": "🎵", "twitter": "🐦", "amazon": "📦",
    "linkedin": "💼", "truecaller": "📞", "canva": "🎨", "opensea": "🌊",
    "adobe": "🎭", "airbnb": "🏠", "alibaba": "🛒", "github": "🐱",
    "netflix": "🎬", "twitch": "🟣", "steam": "♨️", "reddit": "🤖",
    "paypal": "💳", "uber": "🚗", "tiktok": "🎵", "telegram": "✈️",
    "whatsapp": "💚", "youtube": "▶️", "dropbox": "📦", "slack": "💼",
    "zoom": "📹", "ebay": "🛒", "pinterest": "📌", "soundcloud": "🎧",
    "vk": "🇷🇺", "line": "💚", "kakao": "💛", "badoo": "🔴", "bumble": "🐝",
    "tinder": "🔥", "okcupid": "💘", "onlyfans": "💙", "patreon": "🎨",
    "duolingo": "🦉", "coursera": "📚", "udemy": "🎓", "quora": "❓",
    "medium": "✍️", "notion": "📝", "trello": "📋", "hubspot": "🟠",
    "booking": "🏨", "expedia": "✈️", "tripadvisor": "🦉", "yelp": "⭐",
    "peopledatalabs": "📊",
}


def get_badge(title: str) -> str:
    tl = title.lower()
    for k, v in SOURCE_BADGES.items():
        if k in tl:
            return v
    return "🔍"


def detect_query_type(query: str) -> str:
    query = query.strip()
    if re.match(r"^\+?\d[\d\s\-\(\)]{7,}$", query):
        return "phone"
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", query):
        return "email"
    if re.match(r"^[\w\.\-]+\.[a-z]{2,}$", query, re.I):
        return "domain"
    if re.match(r"^[\w\.\-]{3,32}$", query):
        return "username"
    return "any"


def _clean_number(raw: str) -> str:
    return re.sub(r"[\s\+\-\(\)]", "", raw)


def _extract_phones(rec: dict) -> list[str]:
    out = []
    for i in range(1, 25):
        k = "Phone" if i == 1 else f"Phone{i}"
        v = rec.get(k)
        if v:
            out.append(str(v).strip())
    return list(dict.fromkeys(out))


def _extract_addresses(rec: dict) -> list[str]:
    out = []
    for i in range(1, 10):
        k = "Adres" if i == 1 else f"Adres{i}"
        v = rec.get(k)
        if v:
            out.append(v.strip())
    return list(dict.fromkeys(out))


def _process_record(rec: dict) -> dict:
    return {
        "full_name":         rec.get("FullName", ""),
        "father_name":       rec.get("FatherName", ""),
        "email":             rec.get("Email", ""),
        "document_number":   rec.get("DocumentNumber", ""),
        "ip":                rec.get("IP", ""),
        "country":           rec.get("Country", ""),
        "currency":          rec.get("Currency", ""),
        "region":            rec.get("Region", ""),
        "registration_date": rec.get("RegistrationDate", ""),
        "hash":              rec.get("EncryptedPassword", ""),
        "sum":               rec.get("Sum", ""),
        "phones":            _extract_phones(rec),
        "addresses":         _extract_addresses(rec),
    }


def _extract_intel(sources: list[dict]) -> dict[str, list]:
    intel: dict[str, set] = defaultdict(set)
    for src in sources:
        for rec in src.get("records", []):
            if rec.get("full_name"):    intel["names"].add(rec["full_name"])
            if rec.get("father_name"):  intel["fathers"].add(rec["father_name"])
            if rec.get("email"):        intel["emails"].add(rec["email"].lower())
            if rec.get("document_number"): intel["documents"].add(rec["document_number"])
            if rec.get("ip"):           intel["ips"].add(rec["ip"])
            if rec.get("country"):      intel["countries"].add(rec["country"])
            if rec.get("region"):       intel["regions"].add(rec["region"])
            if rec.get("hash"):         intel["hashes"].add(rec["hash"])
            if rec.get("registration_date"): intel["dates"].add(rec["registration_date"])
            for p in rec.get("phones", []):
                intel["phones"].add(p)
            for a in rec.get("addresses", []):
                intel["addresses"].add(a)
    return {k: sorted(v) for k, v in intel.items()}


def search(query: str) -> dict:
    """Execute OSINT search. Never exposes API key in error messages."""
    cfg = current_app.config
    api_url: str = cfg["API_URL"]
    api_key: str = cfg["API_KEY"]
    timeout: int = cfg.get("API_TIMEOUT", 25)

    number = _clean_number(query)
    query_type = detect_query_type(query)
    t0 = time.perf_counter()

    try:
        resp = requests.get(
            api_url,
            params={"key": api_key, "number": number},
            timeout=timeout,
        )
        # Handle HTTP errors cleanly — never expose URL or key
        if resp.status_code == 403:
            return _error_result("Access denied by data provider.", query, query_type)
        if resp.status_code == 429:
            return _error_result("Rate limit reached. Please wait a moment.", query, query_type)
        if resp.status_code == 404:
            return _error_result("Data provider endpoint not found.", query, query_type)
        if resp.status_code >= 500:
            return _error_result("Data provider is temporarily unavailable.", query, query_type)
        if not resp.ok:
            return _error_result(f"Data provider returned an error (HTTP {resp.status_code}).", query, query_type)

        raw = resp.json()

    except requests.exceptions.Timeout:
        return _error_result("Request timed out. Try again.", query, query_type)
    except requests.exceptions.ConnectionError:
        return _error_result("Unable to reach data provider. Check your connection.", query, query_type)
    except Exception:
        # Generic catch — never expose internals
        return _error_result("An unexpected error occurred. Please try again.", query, query_type)

    elapsed = round(time.perf_counter() - t0, 3)

    if not raw.get("status"):
        return {
            "ok": False,
            "query": query,
            "query_type": query_type,
            "number": number,
            "sources": [],
            "intel": {},
            "total_records": 0,
            "total_sources": 0,
            "response_time": elapsed,
            "sources_hidden": 0,
            "error": None,
        }

    api_data: dict = raw.get("data", {})
    sources: list[dict] = []

    for src_key, src_val in api_data.items():
        if not isinstance(src_val, dict):
            continue
        title   = src_val.get("title", src_key)
        desc    = src_val.get("description", "")
        recs_raw = src_val.get("records", [])
        if not recs_raw:
            continue
        records = [_process_record(r) for r in recs_raw]
        sources.append({
            "key":     src_key,
            "title":   title,
            "badge":   get_badge(title),
            "desc":    desc,
            "records": records,
            "count":   len(records),
        })

    intel = _extract_intel(sources)
    total_records = sum(s["count"] for s in sources)

    return {
        "ok": True,
        "query": query,
        "query_type": query_type,
        "number": number,
        "sources": sources,
        "intel": intel,
        "total_records": total_records,
        "total_sources": len(sources),
        "response_time": elapsed,
        "sources_hidden": 0,
        "error": None,
    }


def _error_result(msg: str, query: str, query_type: str) -> dict:
    return {
        "ok": False,
        "query": query,
        "query_type": query_type,
        "number": "",
        "sources": [],
        "intel": {},
        "total_records": 0,
        "total_sources": 0,
        "response_time": 0,
        "sources_hidden": 0,
        "error": msg,
    }
