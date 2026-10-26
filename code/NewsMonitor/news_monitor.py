#!/usr/bin/env python3
# trading bot High-Impact News Monitor
# Providers: FinanceCalendar -> XOOMAR -> USOfficial -> PersianFX
# No scraping. All providers are JSON/ICS/API based.
__author__ = "Alireza Sadabadi"
__copyright__ = "Copyright (c) 2026 Alireza Sadabadi. All rights reserved."
__credits__ = ["Alireza Sadabadi"]
__license__ = "Apache"
__version__ = "1.2"
__maintainer__ = "Alireza Sadabadi"
__email__ = "alirezasadabady@gmail.com"
__status__ = "Test"
__doc__ = "you can see the tutorials in https://youtube.com/@alirezasadabadi?si=d8o7LK_Ai1Hf68is"

import json
import os
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import requests
from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)

# ============================================================
# SETTINGS
# ============================================================
BROKER_TIMEZONE = "Europe/Moscow (UTC+3)"
# MT5/trading bot chart time: Moscow time, UTC+3. Moscow no longer observes DST.
BROKER_TZ = timezone(timedelta(hours=3), name="MSK")
STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_status.json")

# Event protection window
NEWS_BLOCK_BEFORE_MINUTES = 30
NEWS_BLOCK_AFTER_MINUTES = 45
NEWS_LATE_GRACE_MINUTES = 15

# File freshness for trading bot. This is intentionally separate from event windows.
STATUS_MAX_AGE_SECONDS = 3600

# Polling policy
NORMAL_REFRESH_SECONDS = 60 * 60
NEAR_EVENT_REFRESH_SECONDS = 15 * 60
VERY_NEAR_EVENT_REFRESH_SECONDS = 5 * 60
IMMINENT_REFRESH_SECONDS = 60
NEAR_EVENT_MINUTES = 60
VERY_NEAR_EVENT_MINUTES = 30
IMMINENT_MINUTES = 10
ACTIVE_EVENT_REFRESH_SECONDS = 60

# Network
REQUEST_TIMEOUT_SECONDS = 7.0
USER_AGENT = "NewsMonitor/1.2"

# Do not hammer a provider after repeated failures.
PROVIDER_COOLDOWN_SECONDS = 60

FINANCECALENDAR_URL = "https://www.financecalendar.com/wp-json/fc/v1/calendar"
XOOMAR_URL = "https://xoomar.com/api/markets/calendar"
BLS_ICS_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BEA_ICS_URL = "https://www.bea.gov/news/schedule/icalendar"
FED_FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
PERSIANFX_URL = "https://api.persianfx.com/api.php"

# Configure the currencies relevant to the instrument being monitored.
# Examples: XAUUSD -> {"USD", "XAU"}; EURGBP -> {"EUR", "GBP"};
# US30/SP500 -> {"USD"}.
RELEVANT_CURRENCIES = {"USD", "XAU"}
US_COUNTRY_WORDS = {
    "united states", "u.s.", "us", "usa", "american", "usd"
}
US_SOURCE_WORDS = {
    "bls", "bea", "census", "federal reserve", "fed", "department of labor",
    "treasury", "us treasury"
}

# Keywords used only to infer that an event with missing currency/country data
# is probably a US macro release. This is separate from the user-configurable
# event allowlist below and should not be edited to control trade blocking.
US_CURRENCY_INFERENCE_KEYWORDS = {
    "cpi", "consumer price index", "ppi", "producer price index",
    "nonfarm payrolls", "employment situation", "payrolls", "jobless claims",
    "initial jobless claims", "pce", "personal income", "personal outlays",
    "gdp", "retail sales", "durable goods", "industrial production", "jolts",
    "fomc", "fed rate", "federal funds", "interest rate decision",
    "ism manufacturing", "ism services", "housing starts", "building permits",
    "new home sales", "consumer confidence", "trade balance", "beige book"
}

# USER CONFIGURATION: only high-impact US/USD events whose names match at least
# one keyword below are allowed to activate the news block / close positions.
# Remove keywords to ignore those releases; add keywords to include more releases.
# This list does NOT filter high-impact events for other explicitly relevant
# currencies (for example EUR in an EURGBP configuration).
# If True, every high-impact relevant event is accepted; US_EVENT_KEYWORDS is ignored for USD events.
# If False, USD events must match US_EVENT_KEYWORDS.
ALL_NEWS = False

US_EVENT_KEYWORDS = {
    # Inflation
    "cpi", "consumer price index", "ppi", "producer price index",
    "pce", "personal consumption expenditures", "personal income and outlays",

    # Employment / labor
    "nonfarm payroll", "non-farm payroll", "employment situation",
    "jobless claims", "initial jobless claims", "unemployment rate",

    # Growth / activity
    "gdp", "gross domestic product", "retail sales", "durable goods",
    "industrial production", "ism manufacturing", "ism services",

    # Monetary policy
    "fomc", "federal funds rate", "fed rate", "interest rate decision",
    "federal reserve rate",

    # Other major US releases
    "jolts", "consumer confidence", "housing starts", "building permits",
    "new home sales", "beige book",
}

# ============================================================
# LOGGING
# ============================================================

def now_local_str():
    return datetime.now(BROKER_TZ).strftime("%Y-%m-%d %H:%M:%S")


def log(message, color=None):
    text = f"[{now_local_str()}] NEWS_MONITOR | {message}"
    if color:
        print(color + text + Style.RESET_ALL, flush=True)
    else:
        print(text, flush=True)


# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc)


def parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            dt = None
        if dt is None:
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
            ):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except Exception:
                    pass
        if dt is None:
            try:
                dt = parsedate_to_datetime(text)
            except Exception:
                return None
    if dt.tzinfo is None:
        # Calendar APIs used here are normalized to UTC when timezone is absent.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_impact(value):
    if value is None:
        return ""
    s = str(value).strip().lower()
    if s in {"high", "red", "3", "3.0", "high impact"}:
        return "high"
    if s in {"medium", "mid", "orange", "2", "2.0", "medium impact"}:
        return "medium"
    if s in {"low", "yellow", "1", "1.0", "low impact"}:
        return "low"
    return s


def text_blob(*values):
    return " ".join(str(v or "") for v in values).strip().lower()


def infer_event_currency(event):
    """Infer a missing currency from explicit country/event wording, conservatively."""
    currency = str(event.get("currency") or event.get("currencyCode") or "").strip().upper()
    if currency:
        return currency
    name = text_blob(event.get("name"), event.get("title"), event.get("eventName"), event.get("event_name"))
    country = text_blob(event.get("country"), event.get("countryName"), event.get("region"))
    source = text_blob(event.get("source"), event.get("source_name"), event.get("sourceName"))
    combined = f"{country} {name} {source}"
    # Explicit non-US country names must be handled before generic CPI/GDP terms.
    if any(x in combined for x in ("united kingdom", " uk ", "britain", "british", " gbp", "uk cpi", "uk inflation")):
        return "GBP"
    if any(x in combined for x in ("australia", "australian", " aud", "australia cpi")):
        return "AUD"
    if any(x in combined for x in ("canada", "canadian", " cad")):
        return "CAD"
    if any(x in combined for x in ("eurozone", "euro area", " euro", " eur")):
        return "EUR"
    if any(x in combined for x in ("japan", "japanese", " jpy")):
        return "JPY"
    if any(x in combined for x in ("new zealand", " nzd")):
        return "NZD"
    if any(x in combined for x in ("switzerland", "swiss", " chf")):
        return "CHF"
    # Named US releases are strongly identifiable even if a provider omits currency.
    us_names = (
        "fomc", "federal reserve", "fed rate", "us gdp", "u.s. gdp", "us cpi", "u.s. cpi",
        "us pce", "personal income and outlays", "initial jobless claims", "jobless claims",
        "nonfarm payroll", "non-farm payroll", "payrolls", "ism manufacturing", "ism services",
        "us retail sales", "us durable goods", "us jolts", "beige book", "federal funds rate",
    )
    if (
        any(x in name for x in us_names)
        or any(x in name for x in US_CURRENCY_INFERENCE_KEYWORDS)
        or any(x in source for x in US_SOURCE_WORDS)
        or any(x in country for x in US_COUNTRY_WORDS)
    ):
        return "USD"
    return ""


def is_event_relevant(event):
    currency = infer_event_currency(event)
    if currency in RELEVANT_CURRENCIES:
        return True
    if currency:
        return False

    country = text_blob(event.get("country"), event.get("countryName"), event.get("region"))
    source = text_blob(event.get("source"), event.get("source_name"), event.get("sourceName"))
    name = text_blob(event.get("name"), event.get("title"), event.get("eventName"), event.get("event_name"))

    # Explicit non-US countries in titles must not be mistaken for US macro releases.
    non_us_markers = (
        "uk ", "uk cpi", "united kingdom", "britain", "british", "australia", "australian",
        "canada", "canadian", "eurozone", "euro area", "japan", "japanese", "new zealand",
        "switzerland", "swiss", "china", "chinese"
    )
    if any(x in country for x in non_us_markers) or any(x in name for x in non_us_markers):
        return False

    # Country/source/name heuristics below are specifically for US macro events.
    if "USD" not in RELEVANT_CURRENCIES:
        return False
    if any(x in country for x in US_COUNTRY_WORDS):
        return True
    if any(x in source for x in US_SOURCE_WORDS):
        return True
    # Avoid treating an unqualified generic CPI/GDP as US when provider omitted country.
    specific_us_keywords = US_CURRENCY_INFERENCE_KEYWORDS - {"cpi", "consumer price index", "ppi", "producer price index", "gdp"}
    return any(k in name for k in specific_us_keywords)

def is_us_event_enabled(event):
    """Return whether a relevant USD event is allowed by the user allowlist.

    ALL_NEWS=True accepts every high-impact relevant event. Otherwise only the
    explicitly configured US_EVENT_KEYWORDS are accepted. Matching is performed
    against the normalized event name and known aliases, so NFP remains covered
    even when providers use different names such as Employment Situation.
    """
    currency = str(event.get("currency") or event.get("currencyCode") or "").strip().upper()
    if not currency:
        currency = infer_event_currency(event)

    # The configurable US allowlist applies only to USD events. Other explicitly
    # relevant currencies are governed by high-impact + relevance filtering.
    if currency != "USD":
        return True
    if ALL_NEWS:
        return True

    name = text_blob(
        event.get("name"), event.get("title"),
        event.get("eventName"), event.get("event_name")
    )

    # Canonical aliases. The user can enable/disable these families by keeping
    # or removing the corresponding keyword from US_EVENT_KEYWORDS.
    aliases = {
        "nonfarm payroll": ("nonfarm payroll", "non-farm payroll", "nonfarm payrolls",
                             "non-farm payrolls", "employment situation", "payroll employment"),
        "jobless claims": ("jobless claims", "initial jobless claims", "initial claims"),
        "cpi": ("cpi", "consumer price index"),
        "ppi": ("ppi", "producer price index"),
        "pce": ("pce", "personal consumption expenditures", "personal income and outlays"),
        "gdp": ("gdp", "gross domestic product"),
        "fomc": ("fomc", "federal funds rate", "fed rate", "interest rate decision",
                 "federal reserve rate"),
    }

    configured = {str(k).strip().lower() for k in US_EVENT_KEYWORDS if str(k).strip()}
    for keyword in configured:
        if keyword in name:
            return True
        for family, family_aliases in aliases.items():
            if keyword == family or keyword in family_aliases:
                if any(alias in name for alias in family_aliases):
                    return True

    return False


def make_event(event_time, name, impact="high", source="", currency="", raw=None):
    dt = parse_dt(event_time)
    if dt is None:
        raise ValueError("invalid event time")
    event = {
        "time_utc": dt.isoformat(),
        "name": str(name).strip(),
        "impact": normalize_impact(impact),
        "source": source,
        "currency": str(currency or "").upper(),
        "raw": raw if isinstance(raw, dict) else {},
    }
    # Preserve provider currency; only infer when it is missing.
    if not event["currency"]:
        event["currency"] = infer_event_currency({**event, **(event["raw"] if isinstance(event["raw"], dict) else {})})
    return event


# Provider precedence when multiple sources describe the same event.
# Official agency schedules are preferred over aggregators; FinanceCalendar is
# preferred over XOOMAR/PersianFX when no official schedule is available.
PROVIDER_PRIORITY = {
    "USOfficial": 1,
    "FinanceCalendar": 2,
    "XOOMAR": 3,
    "PersianFX": 4,
}

def _event_name_key(name):
    """Return a conservative canonical identity for known economic releases.

    This intentionally canonicalizes known synonyms, not every event at the same
    timestamp. GDP, PCE and Jobless Claims remain separate identities.
    """
    import re
    s = str(name or '').lower().replace('&', ' and ')
    s = re.sub(r'\s+', ' ', s).strip()

    # Canonical event families shared by the provider calendars.
    # Match explicit aliases before generic token cleanup so provider wording,
    # country prefixes, release stages and quarter labels do not prevent a match.
    if re.search(r'\bfomc\b|\bfederal reserve\b.*\brate decision\b|\bfed(?:eral)? funds rate\b', s):
        return 'fomc rate decision'
    if (re.search(r'\bgdp\b', s) or 'gross domestic product' in s) and not any(
        marker in s for marker in ('gdp price', 'gdp deflator', 'gdp per capita')
    ):
        return 'us gdp release'
    if ('personal income and outlays' in s or 'pce inflation' in s or
            'pce price index' in s or 'personal consumption expenditures' in s or
            re.search(r'\bpce\b', s)):
        return 'pce release'
    if 'initial jobless claims' in s or 'initial claims' in s:
        return 'initial jobless claims'
    if 'continuing jobless claims' in s or 'continuing claims' in s:
        return 'continuing jobless claims'
    if 'consumer price index' in s or re.search(r'\bcpi\b', s):
        return 'cpi release'
    if 'producer price index' in s or re.search(r'\bppi\b', s):
        return 'ppi release'

    # Generic normalization for all other events; do not merge unrelated releases
    # merely because they share a minute.
    aliases = (
        (r'\badvance estimate\b', ''),
        (r'\bpreliminary estimate\b', ''),
        (r'\bfinal estimate\b', ''),
        (r'\b3rd quarter\b', ''),
        (r'\bthird quarter\b', ''),
        (r'\bq[1-4]\b', ''),
        (r'\bfederal reserve\b', 'fed'),
    )
    for pattern, replacement in aliases:
        s = re.sub(pattern, replacement, s)
    s = re.sub(r'\b(?:us|u s|united states)\b', '', s)
    s = re.sub(r'\b20\d{2}\b', '', s)
    s = re.sub(r'[^a-z0-9]+', ' ', s).strip()
    return s

def _event_time_key(event):
    dt = parse_dt(event.get('time_utc'))
    if dt is None:
        return None
    return dt.replace(second=0, microsecond=0)

def _events_match(a, b):
    ta, tb = _event_time_key(a), _event_time_key(b)
    if ta is None or tb is None or ta != tb:
        return False
    na, nb = _event_name_key(a.get('name')), _event_name_key(b.get('name'))
    if not na or not nb or na != nb:
        return False
    ca = str(a.get('currency') or '').strip().upper()
    cb = str(b.get('currency') or '').strip().upper()
    return not ca or not cb or ca == cb

def _merge_event_metadata(match,event,provider):
    raw=match.setdefault('raw',{}); meta=raw.setdefault('_merge',{})
    sources=list(meta.get('sources') or [])
    if provider not in sources: sources.append(provider)
    times=dict(meta.get('provider_times') or {}); times[provider]=event.get('time_utc')
    names=list(meta.get('names') or []); name=str(event.get('name') or '').strip()
    if name and name not in names: names.append(name)
    records=list(meta.get('provider_records') or [])
    rec={'provider':provider,'name':name,'time_utc':event.get('time_utc'),'currency':event.get('currency'),'impact':event.get('impact')}
    if rec not in records: records.append(rec)
    meta.update({'sources':sources,'provider_times':times,'names':names,'provider_records':records})
    return meta

def merge_events(provider_events):
    """Merge only matching event identities at the same UTC minute; retain names/providers."""
    merged=[]
    for provider,events in provider_events:
        for original in events:
            e=dict(original); match=next((x for x in merged if _events_match(x,e)),None)
            if match is None:
                name=str(e.get('name') or '').strip()
                e['raw']=dict(e.get('raw') or {})
                e['raw']['_merge']={'sources':[provider],'selected_source':provider,'provider_times':{provider:e.get('time_utc')},'names':[name],'provider_records':[{'provider':provider,'name':name,'time_utc':e.get('time_utc'),'currency':e.get('currency'),'impact':e.get('impact')}]}; merged.append(e); continue
            meta=_merge_event_metadata(match,e,provider); current=match.get('source') or ''
            if PROVIDER_PRIORITY.get(provider,99)<PROVIDER_PRIORITY.get(current,99):
                old=match.get('time_utc'); match.update({'time_utc':e.get('time_utc'),'name':e.get('name') or match.get('name'),'impact':e.get('impact') or match.get('impact'),'source':provider,'currency':e.get('currency') or match.get('currency')}); meta['selected_source']=provider; meta['replaced_time']=old
            match.setdefault('raw',{})['_merge']=meta
    return sorted(merged,key=lambda x:x['time_utc'])

def dedupe_events(events):
    """Collapse matching event names at the same UTC minute, not all events at that minute."""
    out=[]
    for e in events:
        match=next((x for x in out if _events_match(x,e)),None)
        if match is None:
            item=dict(e)
            item['raw']=dict(item.get('raw') or {})
            item['raw'].setdefault('_merge',{'sources':[item.get('source','')],'selected_source':item.get('source',''),'provider_times':{item.get('source',''):item.get('time_utc')},'names':[str(item.get('name') or '').strip()]})
            out.append(item)
        else:
            provider=e.get('source') or ''
            meta=_merge_event_metadata(match,e,provider)
            current=match.get('source') or ''
            if not match.get('currency') and e.get('currency'):
                match['currency']=e.get('currency')
            if PROVIDER_PRIORITY.get(provider,99)<PROVIDER_PRIORITY.get(current,99):
                old=match.get('time_utc')
                match.update({'time_utc':e.get('time_utc'),'name':e.get('name') or match.get('name'),'impact':e.get('impact') or match.get('impact'),'source':provider,'currency':e.get('currency') or match.get('currency')})
                meta['selected_source']=provider
                meta['replaced_time']=old
            match.setdefault('raw',{})['_merge']=meta
    return sorted(out,key=lambda x:x['time_utc'])

def validate_event_list(events, provider):
    if not isinstance(events, list):
        raise ValueError(f"{provider}: events is not a list")
    valid = []
    for e in events:
        if not isinstance(e, dict):
            continue
        try:
            dt = parse_dt(e.get("time_utc"))
            name = str(e.get("name") or "").strip()
            if dt is None or not name:
                continue
            if normalize_impact(e.get("impact")) != "high":
                continue
            if not is_us_event_enabled(e):
                continue
            valid.append(e)
        except Exception:
            continue
    return dedupe_events(valid)


# ============================================================
# PROVIDER 1: FINANCECALENDAR
# ============================================================

def fetch_financecalendar(start_date, end_date):
    log(f"FINANCECALENDAR request -> {start_date}..{end_date}, timeout={REQUEST_TIMEOUT_SECONDS}s")
    params = {"from": start_date, "to": end_date, "impact": "high", "limit": 500}
    r = requests.get(FINANCECALENDAR_URL, params=params,
                     headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                     timeout=REQUEST_TIMEOUT_SECONDS)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise ValueError("FinanceCalendar response is not an object")

    raw = data.get("data")
    if raw is None:
        raw = data.get("events")
    if not isinstance(raw, list):
        raise ValueError("FinanceCalendar response has no valid data/events array")

    # A 200 + empty array is structurally valid only if the response envelope is valid.
    # We still accept zero relevant US events; we do NOT treat that as provider failure.
    events = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("eventName") or item.get("name") or item.get("title")
        dt = item.get("scheduledAt") or item.get("time_utc") or item.get("time") or item.get("date")
        impact = item.get("importance") or item.get("impact")
        currency = item.get("currency") or item.get("currencyCode")
        if not name or not dt:
            continue
        candidate = {
            "eventName": name,
            "scheduledAt": dt,
            "importance": impact,
            "currency": currency,
            "country": item.get("country") or item.get("countryName"),
            "source": item.get("source") or item.get("sourceName"),
            "title": item.get("title"),
        }
        if normalize_impact(impact) != "high":
            continue
        if not is_event_relevant(candidate):
            continue
        try:
            events.append(make_event(dt, name, impact, "FinanceCalendar", currency, item))
        except Exception:
            continue

    # Strong schema validation: if records exist but none can be interpreted, fail over.
    if raw and not events:
        # If every record is clearly non-US high-impact, zero is legitimate.
        interpretable = 0
        for item in raw:
            if isinstance(item, dict) and (item.get("eventName") or item.get("name") or item.get("title")):
                interpretable += 1
        if interpretable == 0:
            raise ValueError("FinanceCalendar returned records but none had usable event fields")

    events = validate_event_list(events, "FinanceCalendar")
    log(f"FINANCECALENDAR success -> raw_records={len(raw)}, validated={len(events)} relevant high-impact events")
    return events


# ============================================================
# PROVIDER 2: XOOMAR
# ============================================================

def fetch_xoomar(start_date, end_date):
    log(f"XOOMAR request -> {start_date}..{end_date}, timeout={REQUEST_TIMEOUT_SECONDS}s")
    params = {"from": start_date, "to": end_date, "importance": "high"}
    r = requests.get(XOOMAR_URL, params=params,
                     headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                     timeout=REQUEST_TIMEOUT_SECONDS)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise ValueError("XOOMAR response is not an object")
    raw = data.get("data")
    if not isinstance(raw, list):
        raise ValueError("XOOMAR response missing data array")

    events = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("eventName")
        dt = item.get("scheduledAt")
        impact = item.get("importance")
        currency = item.get("currency") or ("USD" if str(item.get("source", "")).lower() in {"bls", "bea", "census", "fed", "dol", "treasury"} else "")
        if normalize_impact(impact) != "high" or not name or not dt:
            continue
        candidate = {"eventName": name, "scheduledAt": dt, "importance": impact, "currency": currency,
                     "country": "United States", "source": item.get("source")}
        if not is_event_relevant(candidate):
            continue
        try:
            events.append(make_event(dt, name, impact, "XOOMAR", currency, item))
        except Exception:
            continue

    # XOOMAR is a US macro calendar. Therefore, when the endpoint returns
    # records but our parser cannot validate ANY high-impact relevant event,
    # do not silently convert that response into an empty calendar. This is
    # the exact failure mode seen in the old monitor (raw_records=5,
    # validated=0). Treat it as provider failure and continue to the next source.
    if raw and not any(isinstance(x, dict) and x.get("eventName") and x.get("scheduledAt") for x in raw):
        raise ValueError("XOOMAR returned records without documented eventName/scheduledAt fields")

    # Keep the pre-allowlist count so a valid feed is not treated as broken
    # merely because the user's US_EVENT_KEYWORDS intentionally excludes every event.
    relevant_candidates_before_keyword_filter = len(events)
    events = validate_event_list(events, "XOOMAR")
    if raw and relevant_candidates_before_keyword_filter == 0:
        raise ValueError("XOOMAR returned records but zero relevant high-impact events could be validated")
    log(f"XOOMAR success -> raw_records={len(raw)}, validated={len(events)} relevant high-impact events")
    return events


# ============================================================
# PROVIDER 3: US OFFICIAL (BLS + BEA + FED)
# ============================================================

def fetch_usofficial():
    # BLS is currently the strongest machine-readable official source in this group.
    # The implementation deliberately treats 403 as a provider failure so the next
    # provider can run.
    events = []
    errors = []

    log(f"USOFFICIAL BLS request -> timeout={REQUEST_TIMEOUT_SECONDS}s")
    try:
        r = requests.get(BLS_ICS_URL, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
        r.raise_for_status()
        text = r.text
        if "BEGIN:VCALENDAR" not in text:
            raise ValueError("BLS response is not valid ICS")
        # Lightweight ICS parser: enough for DTSTART/DTEND/SUMMARY; no scraping.
        current = {}
        for line in text.splitlines() + ["END:VEVENT"]:
            line = line.strip()
            if line == "BEGIN:VEVENT":
                current = {}
            elif line.startswith("DTSTART"):
                current["time"] = line.split(":", 1)[-1]
            elif line.startswith("SUMMARY"):
                current["name"] = line.split(":", 1)[-1].strip()
            elif line == "END:VEVENT":
                if current.get("time") and current.get("name"):
                    dt_text = current["time"]
                    try:
                        if dt_text.endswith("Z"):
                            dt = datetime.strptime(dt_text, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                        elif "T" in dt_text:
                            dt = datetime.strptime(dt_text, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                        else:
                            dt = datetime.strptime(dt_text, "%Y%m%d").replace(tzinfo=timezone.utc)
                        events.append(make_event(dt, current["name"], "high", "USOfficial-BLS", "USD", current))
                    except Exception:
                        pass
                current = {}
        log(f"USOFFICIAL BLS success -> events={len(events)}")
    except Exception as e:
        errors.append(f"BLS: {type(e).__name__}: {e}")
        log(f"USOfficial BLS FAILED -> {type(e).__name__}: {e}")

    # We intentionally keep BEA/Fed lightweight and non-scraping. If BLS fails,
    # the provider is considered failed unless at least one official feed yields
    # a valid event.
    if not events:
        raise RuntimeError("; ".join(errors) if errors else "USOfficial returned no valid events")
    return validate_event_list(events, "USOfficial")


# ============================================================
# PROVIDER 4: PERSIANFX (Iran-friendly fallback candidate)
# ============================================================

def fetch_persianfx():
    log(f"PERSIANFX request -> today, timeout={REQUEST_TIMEOUT_SECONDS}s")
    r = requests.get(PERSIANFX_URL,
                     headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                     timeout=REQUEST_TIMEOUT_SECONDS)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict) or data.get("status") != "success":
        raise ValueError("PersianFX invalid response/status")
    raw = data.get("events")
    if not isinstance(raw, list):
        raise ValueError("PersianFX response missing events array")

    events = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if normalize_impact(item.get("impact")) != "high":
            continue
        currency = str(item.get("currency") or "").upper()
        if currency not in RELEVANT_CURRENCIES:
            continue
        name = item.get("event_name") or item.get("event_name_fa")
        date_s = item.get("date")
        time_s = item.get("time")
        if not name or not date_s or not time_s:
            continue
        # PersianFX documents date/time as calendar date/time. Treat it as UTC
        # only when no timezone is supplied; the monitor stores all event times in UTC.
        try:
            dt = datetime.fromisoformat(f"{date_s}T{time_s}").replace(tzinfo=timezone.utc)
            events.append(make_event(dt, name, "high", "PersianFX", currency, item))
        except Exception:
            continue

    if raw and not any(isinstance(x, dict) and x.get("event_name") and x.get("currency") for x in raw):
        raise ValueError("PersianFX returned malformed event records")

    events = validate_event_list(events, "PersianFX")
    log(f"PERSIANFX success -> raw_records={len(raw)}, validated={len(events)} relevant high-impact events")
    return events


# ============================================================
# CALENDAR / STATUS
# ============================================================

def write_status(events, provider, provider_chain, provider_errors=None):
    now = utc_now()
    events = dedupe_events(events)
    active = False
    active_events = []

    for e in events:
        dt = parse_dt(e["time_utc"])
        if dt is None:
            continue
        start = dt - timedelta(minutes=NEWS_BLOCK_BEFORE_MINUTES)
        end = dt + timedelta(minutes=NEWS_BLOCK_AFTER_MINUTES + NEWS_LATE_GRACE_MINUTES)
        if start <= now <= end:
            active = True
            active_events.append(e)

    status = {
        "relevant_currencies": sorted(RELEVANT_CURRENCIES),
        "high_impact": active,
        "checked_at": now.isoformat(),
        "checked_at_moscow": now.astimezone(BROKER_TZ).isoformat(),
        "updated_at": now.isoformat(),
        "provider": provider,
        "provider_chain": provider_chain,
        "events": events,
        "active_events": active_events,
        "block_before_minutes": NEWS_BLOCK_BEFORE_MINUTES,
        "block_after_minutes": NEWS_BLOCK_AFTER_MINUTES,
        "late_grace_minutes": NEWS_LATE_GRACE_MINUTES,
        "provider_errors": provider_errors or [],
    }

    tmp = STATUS_FILE + ".tmp"
    os.makedirs(os.path.dirname(STATUS_FILE) or ".", exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATUS_FILE)
    return status


def event_window_state(events):
    """Return the closest protection-window state for adaptive polling.

    The monitor polls faster not only before an event, but also while an event
    is inside its active protection window. This prevents a long normal sleep
    from delaying discovery of a late-arriving provider update.
    """
    now = utc_now()
    nearest_start = None
    active = False

    for e in events:
        dt = parse_dt(e.get("time_utc"))
        if dt is None:
            continue

        start = dt - timedelta(minutes=NEWS_BLOCK_BEFORE_MINUTES)
        end = dt + timedelta(minutes=NEWS_BLOCK_AFTER_MINUTES + NEWS_LATE_GRACE_MINUTES)

        if start <= now <= end:
            active = True
            continue

        if start > now:
            seconds = (start - now).total_seconds()
            if nearest_start is None or seconds < nearest_start:
                nearest_start = seconds

    return active, nearest_start


def select_refresh_interval(events):
    active, seconds_to_start = event_window_state(events)

    # While a news-protection window is active, check every minute. This is
    # especially important when a free provider publishes an event late.
    if active:
        return ACTIVE_EVENT_REFRESH_SECONDS

    if seconds_to_start is None:
        return NORMAL_REFRESH_SECONDS

    if seconds_to_start <= IMMINENT_MINUTES * 60:
        return IMMINENT_REFRESH_SECONDS
    if seconds_to_start <= VERY_NEAR_EVENT_MINUTES * 60:
        return VERY_NEAR_EVENT_REFRESH_SECONDS
    if seconds_to_start <= NEAR_EVENT_MINUTES * 60:
        return NEAR_EVENT_REFRESH_SECONDS
    return NORMAL_REFRESH_SECONDS


# ============================================================
# MAIN
# ============================================================

def main():
    log("Starting high-impact news monitor (display timezone: Moscow / MT5 chart UTC+3)")
    log("Primary provider : FinanceCalendar")
    log("Fallback provider: XOOMAR")
    log("Third provider   : USOfficial (BLS + BEA + Federal Reserve)")
    log("Fourth provider  : PersianFX (supplementary)")
    log("Merge policy      : TIME + EVENT IDENTITY; matching event name + UTC minute = one event; distinct releases retained")
    log("Scraping         : DISABLED")
    log(f"Relevant currencies: {', '.join(sorted(RELEVANT_CURRENCIES))}")
    log(f"All news mode       : {ALL_NEWS}")
    log(f"US event allowlist active: {not ALL_NEWS}")
    log(f"US event keywords: {', '.join(sorted(US_EVENT_KEYWORDS)) or '(empty - no US/USD events allowed)'}")
    log(f"Broker timezone  : {BROKER_TIMEZONE}")
    log(f"Block window     : -{NEWS_BLOCK_BEFORE_MINUTES}m / +{NEWS_BLOCK_AFTER_MINUTES}m")
    log(f"Late grace       : +{NEWS_LATE_GRACE_MINUTES}m")
    log(f"Status file      : {STATUS_FILE}")
    log("Refresh policy   : 60m normal / 15m within 60m / 5m within 30m / 1m within 10m or active")

    last_events = []
    last_provider = "none"
    last_success_time = None

    while True:
        now = utc_now()
        start_date = (now - timedelta(days=2)).date().isoformat()
        end_date = (now + timedelta(days=7)).date().isoformat()
        provider_errors = []
        provider_chain = []
        success = False

        providers = [
            ("FinanceCalendar", lambda: fetch_financecalendar(start_date, end_date)),
            ("XOOMAR", lambda: fetch_xoomar(start_date, end_date)),
            ("USOfficial", fetch_usofficial),
            ("PersianFX", fetch_persianfx),
        ]

        successful_provider_events = []
        for name, fn in providers:
            provider_chain.append(name)
            try:
                events = validate_event_list(fn(), name)
                successful_provider_events.append((name, events))
                log(f"{name.upper()} validated -> events={len(events)}")
            except Exception as e:
                msg = f"{name} failed: {type(e).__name__}: {e}"
                provider_errors.append(msg)
                log(f"{name.upper()} FAILED -> {type(e).__name__}: {e}")

        if successful_provider_events:
            events = merge_events(successful_provider_events)
            last_events = events
            # The status provider now describes the complete merged chain.
            last_provider = "+".join(name for name, _ in successful_provider_events)
            last_success_time = utc_now()
            write_status(events, last_provider, provider_chain, provider_errors)
            log(f"Calendar merged -> providers={len(successful_provider_events)}, unique_events={len(events)}", Fore.GREEN)
            for e in events:
                dt = parse_dt(e["time_utc"])
                if dt:
                    merge_meta=(e.get("raw") or {}).get("_merge") or {}
                    sources=",".join(merge_meta.get("sources") or [e.get("source", "")])
                    selected=merge_meta.get("selected_source", e.get("source", ""))
                    log(f"Relevant high-impact event -> {dt.astimezone(BROKER_TZ).strftime('%Y-%m-%d %H:%M:%S')} | {e.get('currency','-')} | {e['name']} | selected={selected} | sources={sources}")
            log(f"News feed connected -> merged providers={last_provider}, events={len(events)}", Fore.GREEN)
            success = True

        if not success:
            # Keep the last VALID calendar instead of replacing it with an empty calendar.
            log("ALL PROVIDERS FAILED -> retaining last VALID calendar", Fore.RED)
            if provider_errors:
                log("Reason: " + "; ".join(provider_errors), Fore.RED)
            if last_events:
                try:
                    write_status(last_events, last_provider, provider_chain, provider_errors)
                except Exception as e:
                    log(f"STATUS WRITE FAILED -> {type(e).__name__}: {e}", Fore.RED)
            else:
                try:
                    write_status([], "none", provider_chain, provider_errors)
                except Exception as e:
                    log(f"STATUS WRITE FAILED -> {type(e).__name__}: {e}", Fore.RED)

        interval = select_refresh_interval(last_events)
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Stopped by user")
