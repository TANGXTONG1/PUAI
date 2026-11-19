#!/usr/bin/env python3
"""Validate a private year-with-ai report and render a standalone public HTML."""

import argparse
import base64
import copy
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


THEMES = ("puai", "teach", "aicu", "all", "hush", "einstein", "edison", "support", "free")


class ReportError(ValueError):
    """A report violates the portable schema."""


def obj(value, keys, path, optional=()):
    if not isinstance(value, dict):
        raise ReportError(f"{path}: expected an object")
    missing = set(keys) - set(value)
    extra = set(value) - set(keys) - set(optional)
    if missing or extra:
        raise ReportError(f"{path}: missing {sorted(missing)}, unexpected {sorted(extra)}")
    return value


def string(value, limit, path, minimum=1):
    if not isinstance(value, str) or not minimum <= len(value) <= limit:
        raise ReportError(f"{path}: expected {minimum}–{limit} characters")
    if minimum and not value.strip():
        raise ReportError(f"{path}: must not be blank")
    if any(ord(char) < 32 for char in value):
        raise ReportError(f"{path}: control characters and line breaks are not supported")
    return value


def array(value, minimum, maximum, path):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ReportError(f"{path}: expected an array with {minimum}–{maximum} entries")
    return value


def iso_date(value, path):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ReportError(f"{path}: expected YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ReportError(f"{path}: invalid calendar date") from exc


def activity_timestamp(value, path):
    """Parse a timestamp only when the source supplies its UTC offset."""
    pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})"
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ReportError(f"{path}: expected an ISO timestamp with Z or an explicit UTC offset")
    if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ReportError(f"{path}: invalid UTC offset")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReportError(f"{path}: invalid timestamp") from exc


def select_active_months(month_counts):
    """Select up to three busiest visible months, preferring newer ties."""
    ranked = sorted(month_counts, key=lambda month: (month_counts[month], month), reverse=True)
    return sorted(ranked[:3])


def derive_rhythm(active_dates):
    """Describe observed rhythm without treating missing history as inactivity."""
    dates = sorted(set(active_dates))
    criteria = {"min_active_days": 14, "min_active_weeks": 3}
    month_dates = {}
    for day in dates:
        month_dates.setdefault(day.isoformat()[:7], []).append(day)
    history = []
    for month, days in sorted(month_dates.items()):
        weeks = len({(day.isocalendar().year, day.isocalendar().week) for day in days})
        history.append({
            "month": month,
            "active_days": len(days),
            "active_weeks": weeks,
            "is_dense": len(days) >= criteria["min_active_days"] and weeks >= criteria["min_active_weeks"],
        })
    dense_month = next((row["month"] for row in history if row["is_dense"]), None)
    first_seen = dates[0].isoformat() if dates else None
    last_seen = dates[-1].isoformat() if dates else None
    return {
        "first_seen": first_seen,
        "last_seen": last_seen,
        "dense_start_month": dense_month,
        "analysis_start": f"{dense_month}-01" if dense_month else first_seen,
        "analysis_end": last_seen,
        "analysis_months": [row["month"] for row in history if dense_month is None or row["month"] >= dense_month],
        "month_history": history,
        "criteria": criteria,
    }


def validate_token_usage(usage, active_dates, mode, evidence, refs):
    """Validate an audited usage aggregate, without estimating missing usage."""
    path = "activity.token_usage"
    obj(usage, ["start", "end", "input_tokens", "cached_input_tokens", "output_tokens",
                "total_tokens", "coverage", "scope", "evidence_ids"], path)
    usage_start = iso_date(usage["start"], f"{path}.start")
    usage_end = iso_date(usage["end"], f"{path}.end")
    rhythm = derive_rhythm(active_dates)
    if (usage_start.isoformat(), usage_end.isoformat()) != (rhythm["analysis_start"], rhythm["analysis_end"]):
        raise ReportError(f"{path}: start/end must match the nonempty activity analysis period")
    for key in ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens"):
        value = usage[key]
        if type(value) is not int or not 0 <= value <= 9_007_199_254_740_991:
            raise ReportError(f"{path}.{key}: expected a nonnegative JavaScript-safe integer")
    if usage["cached_input_tokens"] > usage["input_tokens"]:
        raise ReportError(f"{path}: cached_input_tokens must not exceed input_tokens")
    if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
        raise ReportError(f"{path}: total_tokens must equal input_tokens + output_tokens; do not add cached input twice")
    if not isinstance(usage["coverage"], str) or usage["coverage"] not in {"complete", "partial"}:
        raise ReportError(f"{path}.coverage: expected complete or partial")
    if not isinstance(usage["scope"], str) or usage["scope"] not in {"main_sessions", "provided_export"}:
        raise ReportError(f"{path}.scope: expected main_sessions or provided_export")
    array(usage["evidence_ids"], 1, 500, f"{path}.evidence_ids")
    ids = refs(usage["evidence_ids"], f"{path}.evidence_ids", required=True)
    allowed_types = {"provided", "demo"} if mode == "demo" else {"provided"}
    if not any(evidence[eid]["type"] in allowed_types for eid in ids):
        raise ReportError(f"{path}: token usage needs provided records, not memory or estimates")


def reviewed_message_ids(activity, field, messages_by_id):
    ids = set()
    for index, value in enumerate(array(activity[field], 0, 50_000, f"activity.{field}")):
        path = f"activity.{field}[{index}]"
        mid = string(value, 128, path)
        if mid not in messages_by_id:
            raise ReportError(f"{path}: unknown message ID {mid!r}")
        if mid in ids:
            raise ReportError(f"{path}: duplicate message ID")
        ids.add(mid)
    return ids


def validate_activity(activity, start, end, mode, evidence, refs, now, theme=None, has_story=False):
    obj(activity, ["timezone", "coverage", "messages", "highlights"], "activity",
        optional=["roast_message_ids", "theme_message_ids", "share_quotes", "token_usage"])
    zone = string(activity["timezone"], 100, "activity.timezone")
    try:
        target_zone = ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ReportError("activity.timezone: expected an available IANA time zone") from exc
    if not isinstance(activity["coverage"], str) or activity["coverage"] not in {"complete", "partial"}:
        raise ReportError("activity.coverage: expected complete or partial")
    messages_by_id = {}
    message_months = {}
    active_dates = set()
    for index, message in enumerate(array(activity["messages"], 0, 50_000, "activity.messages")):
        path = f"activity.messages[{index}]"
        obj(message, ["id", "timestamp", "evidence_ids"], path)
        mid = string(message["id"], 128, f"{path}.id")
        if mid in messages_by_id:
            raise ReportError(f"{path}.id: duplicate message ID")
        messages_by_id[mid] = message
        stamp = activity_timestamp(message["timestamp"], f"{path}.timestamp")
        try:
            local_date = stamp.astimezone(target_zone).date()
        except (ValueError, OverflowError) as exc:
            raise ReportError(f"{path}.timestamp: cannot convert timestamp to the target time zone") from exc
        if not start <= local_date <= end:
            raise ReportError(f"{path}.timestamp: local date must fall within report.period")
        if stamp > now:
            raise ReportError(f"{path}.timestamp: future messages are not allowed")
        ids = refs(message["evidence_ids"], f"{path}.evidence_ids", required=True)
        if mode == "self_report" and not any(evidence[eid]["type"] == "provided" for eid in ids):
            raise ReportError(f"{path}: precise activity needs provided records, not memory alone")
        message_months[mid] = local_date.isoformat()[:7]
        active_dates.add(local_date)
    if "token_usage" in activity:
        validate_token_usage(activity["token_usage"], active_dates, mode, evidence, refs)
    roast_ids = set()
    if "roast_message_ids" in activity:
        roast_ids = reviewed_message_ids(activity, "roast_message_ids", messages_by_id)
    if "theme_message_ids" in activity:
        if theme is None:
            raise ReportError("activity.theme_message_ids: specify report.theme for this reviewed subset")
        if theme == "puai":
            raise ReportError("activity.theme_message_ids: PUAI uses roast_message_ids for its reviewed subset")
        theme_ids = reviewed_message_ids(activity, "theme_message_ids", messages_by_id)
        if mode != "demo":
            for mid in theme_ids:
                if not any(evidence[eid]["type"] == "provided" for eid in messages_by_id[mid]["evidence_ids"]):
                    raise ReportError("activity.theme_message_ids: counted messages need provided records")
    if "share_quotes" in activity:
        analysis_months = set(derive_rhythm(active_dates)["analysis_months"])
        seen_quotes = set()
        for index, quote in enumerate(array(activity["share_quotes"], 0, 6, "activity.share_quotes")):
            path = f"activity.share_quotes[{index}]"
            obj(quote, ["message_id", "text"], path, optional=["emphasis", "repeat_message_ids", "rewrite"])
            if (theme or has_story) and "rewrite" in quote:
                raise ReportError(f"{path}.rewrite: use the user's original words in this report")
            if theme not in (None, "puai") and "repeat_message_ids" in quote:
                raise ReportError(f"{path}.repeat_message_ids: roast repeat counts belong to the PUAI theme")
            mid = string(quote["message_id"], 128, f"{path}.message_id")
            quote_text = string(quote["text"], 120, f"{path}.text")
            if "emphasis" in quote:
                emphasis = string(quote["emphasis"], 30, f"{path}.emphasis")
                if emphasis not in quote_text:
                    raise ReportError(f"{path}.emphasis: must be a contiguous substring of text")
            if "rewrite" in quote:
                rewrite_path = f"{path}.rewrite"
                rewrite = obj(quote["rewrite"], ["text"], rewrite_path, optional=["emphasis"])
                rewrite_text = string(rewrite["text"], 80, f"{rewrite_path}.text")
                if "emphasis" in rewrite:
                    emphasis = string(rewrite["emphasis"], 30, f"{rewrite_path}.emphasis")
                    if emphasis not in rewrite_text:
                        raise ReportError(f"{rewrite_path}.emphasis: must be a contiguous substring of text")
            if mid not in messages_by_id:
                raise ReportError(f"{path}.message_id: unknown message ID {mid!r}")
            if mid in seen_quotes:
                raise ReportError(f"{path}.message_id: duplicate shared quote message ID")
            seen_quotes.add(mid)
            if mode != "demo" and not any(quote_text in evidence[eid]["excerpt"]
                                           for eid in messages_by_id[mid]["evidence_ids"]):
                raise ReportError(f"{path}.text: quote must appear verbatim in that message's linked evidence")
            if "repeat_message_ids" in quote:
                repeat_path = f"{path}.repeat_message_ids"
                repeated = set()
                for repeat_index, value in enumerate(array(quote["repeat_message_ids"], 2, 50_000, repeat_path)):
                    item_path = f"{repeat_path}[{repeat_index}]"
                    repeat_id = string(value, 128, item_path)
                    if repeat_id not in messages_by_id:
                        raise ReportError(f"{item_path}: unknown message ID {repeat_id!r}")
                    if repeat_id in repeated:
                        raise ReportError(f"{item_path}: duplicate repeat message ID")
                    repeated.add(repeat_id)
                    if repeat_id not in roast_ids:
                        raise ReportError(f"{item_path}: repeat messages must belong to the reviewed roast subset")
                    if message_months[repeat_id] not in analysis_months:
                        raise ReportError(f"{item_path}: repeat messages must fall within the analysis period")
                    if mode != "demo" and not any(quote_text in evidence[eid]["excerpt"]
                                                   for eid in messages_by_id[repeat_id]["evidence_ids"]):
                        raise ReportError(f"{item_path}: full quote must appear verbatim in this message's linked evidence")
                if mid not in repeated:
                    raise ReportError(f"{repeat_path}: must include this quote's message_id")
    seen_highlights = set()
    for index, highlight in enumerate(array(activity["highlights"], 0, 12, "activity.highlights")):
        path = f"activity.highlights[{index}]"
        obj(highlight, ["date", "title", "text", "evidence_ids"], path)
        day = iso_date(highlight["date"], f"{path}.date")
        if day not in active_dates:
            raise ReportError(f"{path}.date: a highlight needs at least one supplied message on that date")
        if day in seen_highlights:
            raise ReportError(f"{path}.date: only one highlight per date is supported")
        seen_highlights.add(day)
        string(highlight["title"], 18, f"{path}.title")
        string(highlight["text"], 90, f"{path}.text")
        refs(highlight["evidence_ids"], f"{path}.evidence_ids", required=True)


def summarize_activity(activity):
    """Derive display data from user-message timestamps; never estimate duration."""
    target_zone = ZoneInfo(activity["timezone"])
    stamps = [activity_timestamp(message["timestamp"], "activity timestamp").astimezone(target_zone)
              for message in activity["messages"]]
    counts = Counter(stamp.date() for stamp in stamps)
    roast_counts = None
    if "roast_message_ids" in activity:
        roast_ids = set(activity["roast_message_ids"])
        roast_counts = Counter(stamp.date() for message, stamp in zip(activity["messages"], stamps)
                               if message["id"] in roast_ids)
    hours = [0] * 24
    for stamp in stamps:
        hours[stamp.hour] += 1
    highlights = {item["date"]: {key: item[key] for key in ("title", "text")}
                  for item in activity["highlights"]}
    days = []
    longest = current = 0
    previous = None
    for day in sorted(counts):
        current = current + 1 if previous is not None and day == previous + timedelta(days=1) else 1
        longest = max(longest, current)
        previous = day
        row = {"date": day.isoformat(), "count": counts[day]}
        if roast_counts is not None:
            row["roast_count"] = roast_counts[day]
        if row["date"] in highlights:
            row["highlight"] = highlights[row["date"]]
        days.append(row)
    peak = min(counts, key=lambda day: (-counts[day], day)) if counts else None
    latest = max(stamps, key=lambda stamp: (stamp.hour, stamp.minute, stamp.date())) if stamps else None
    peak_hour = hours.index(max(hours)) if stamps else None
    result = {
        "timezone": activity["timezone"],
        "coverage": activity["coverage"],
        "days": days,
        "summary": {
            "messages": len(stamps),
            "active_days": len(days),
            "longest_streak": longest,
            "peak_day": {"date": peak.isoformat(), "count": counts[peak]} if peak else None,
            "latest_message": {"date": latest.date().isoformat(), "time": latest.strftime("%H:%M")} if latest else None,
            "peak_hour": peak_hour,
        },
        "hours": hours,
    }
    if roast_counts is not None:
        result["summary"]["roast_days"] = len(roast_counts)
        result["summary"]["roast_messages"] = sum(roast_counts.values())
    return result


def validate_report(report, today=None, now=None):
    """Validate shape and provenance links; semantic truth still needs review."""
    today = today or date.today()
    obj(report, ["schema_version", "year", "mode", "period", "person", "identity",
                 "phrase", "keywords", "metrics", "moments", "closing", "evidence"], "report",
        optional=["activity", "theme", "share_story"])
    if "theme" in report and report["theme"] not in THEMES:
        raise ReportError(f"report.theme: expected one of {', '.join(THEMES)}")
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ReportError("schema_version: expected integer 1")
    year = report["year"]
    if type(year) is not int or not 2000 <= year <= 2100:
        raise ReportError("year: expected an integer from 2000 to 2100")
    mode = report["mode"]
    if not isinstance(mode, str) or mode not in {"demo", "excerpt", "self_report", "full"}:
        raise ReportError("mode: expected demo, excerpt, self_report or full")
    obj(report["period"], ["start", "end"], "period")
    start = iso_date(report["period"]["start"], "period.start")
    end = iso_date(report["period"]["end"], "period.end")
    if start.year != year or end.year != year or start > end or end > today:
        raise ReportError("period: dates must be ordered, within year and no later than today")
    if mode == "full" and (start != date(year, 1, 1) or end != date(year, 12, 31) or end >= today):
        raise ReportError("mode=full: requires January 1–December 31 of an already completed year")

    obj(report["person"], ["name"], "person")
    string(report["person"]["name"], 16, "person.name")
    obj(report["identity"], ["title", "subtitle"], "identity")
    string(report["identity"]["title"], 12, "identity.title")
    string(report["identity"]["subtitle"], 60, "identity.subtitle")

    evidence = {}
    for index, item in enumerate(array(report["evidence"], 0 if mode == "demo" else 1, 500, "evidence")):
        path = f"evidence[{index}]"
        obj(item, ["id", "source", "excerpt", "type"], path)
        eid = string(item["id"], 64, f"{path}.id")
        string(item["source"], 300, f"{path}.source")
        # Evidence excerpts may retain original line breaks; they never enter HTML.
        excerpt = item["excerpt"]
        if not isinstance(excerpt, str) or not 1 <= len(excerpt) <= 3000 or not excerpt.strip():
            raise ReportError(f"{path}.excerpt: expected 1–3000 characters")
        if not isinstance(item["type"], str) or item["type"] not in {"provided", "self_report", "demo"}:
            raise ReportError(f"{path}.type: expected provided, self_report or demo")
        if mode != "demo" and item["type"] == "demo":
            raise ReportError(f"{path}: a real report cannot contain demo evidence")
        if eid in evidence:
            raise ReportError(f"{path}.id: duplicate evidence ID")
        evidence[eid] = item

    def refs(value, path, required=False):
        ids = array(value, 1 if required and mode != "demo" else 0, 500, path)
        for eid in ids:
            string(eid, 64, path)
            if eid not in evidence:
                raise ReportError(f"{path}: unknown evidence ID {eid!r}")
        if len(set(ids)) != len(ids):
            raise ReportError(f"{path}: duplicate evidence IDs")
        return ids

    phrase = obj(report["phrase"], ["text", "note", "kind", "evidence_ids"], "phrase")
    string(phrase["text"], 50, "phrase.text")
    string(phrase["note"], 60, "phrase.note")
    if not isinstance(phrase["kind"], str) or phrase["kind"] not in {"quote", "paraphrase"}:
        raise ReportError("phrase.kind: expected quote or paraphrase")
    ids = refs(phrase["evidence_ids"], "phrase.evidence_ids", required=True)
    if phrase["kind"] == "quote" and mode != "demo":
        if not any(phrase["text"] in evidence[eid]["excerpt"] for eid in ids):
            raise ReportError("phrase.text: a quote must appear verbatim in a linked evidence excerpt")

    for index, keyword in enumerate(array(report["keywords"], 0, 3, "keywords")):
        string(keyword, 6, f"keywords[{index}]")
    for index, metric in enumerate(array(report["metrics"], 0, 3, "metrics")):
        path = f"metrics[{index}]"
        obj(metric, ["label", "value", "unit", "evidence_ids"], path)
        string(metric["label"], 12, f"{path}.label")
        string(metric["value"], 12, f"{path}.value")
        string(metric["unit"], 6, f"{path}.unit", minimum=0)
        refs(metric["evidence_ids"], f"{path}.evidence_ids", required=True)
    has_share_story = "share_story" in report
    for index, moment in enumerate(array(report["moments"], 0 if has_share_story else 1, 4, "moments")):
        path = f"moments[{index}]"
        if has_share_story:
            obj(moment, ["text", "evidence_ids"], path, optional=["title"])
        else:
            obj(moment, ["title", "text", "evidence_ids"], path)
        if "title" in moment:
            string(moment["title"], 18, f"{path}.title")
        string(moment["text"], 90, f"{path}.text")
        refs(moment["evidence_ids"], f"{path}.evidence_ids", required=True)
    if "share_story" in report:
        story = obj(report["share_story"], ["persona_evidence_ids", "moment_indices"], "share_story")
        refs(story["persona_evidence_ids"], "share_story.persona_evidence_ids", required=True)
        selected = array(story["moment_indices"], 0, 3, "share_story.moment_indices")
        for pos, index in enumerate(selected):
            if type(index) is not int or not 0 <= index < len(report["moments"]):
                raise ReportError(f"share_story.moment_indices[{pos}]: expected a valid zero-based moment index")
        if len(set(selected)) != len(selected):
            raise ReportError("share_story.moment_indices: duplicate moment indices")
    closing = obj(report["closing"], ["text", "evidence_ids"], "closing")
    string(closing["text"], 80, "closing.text")
    refs(closing["evidence_ids"], "closing.evidence_ids")
    if "activity" in report:
        validate_activity(report["activity"], start, end, mode, evidence, refs,
                          now or datetime.now(timezone.utc), theme=report.get("theme"),
                          has_story="share_story" in report)
    return report


def count_theme_messages(activity, analysis_months, target_zone):
    reviewed = set(activity["theme_message_ids"])
    days = Counter()
    months = {month: 0 for month in sorted(analysis_months)}
    for message in activity["messages"]:
        if message["id"] not in reviewed:
            continue
        day = activity_timestamp(message["timestamp"], "theme message timestamp").astimezone(target_zone).date()
        month = day.isoformat()[:7]
        if month in months:
            months[month] += 1
            days[day.isoformat()] += 1
    return {"messages": sum(months.values()), "months": months, "days": dict(sorted(days.items()))}


def compact_activity(activity):
    """Summarize the observed analysis period and select up to three calendars."""
    aggregate = summarize_activity(activity)
    rhythm = derive_rhythm(date.fromisoformat(day["date"]) for day in aggregate["days"])
    analysis_months = set(rhythm["analysis_months"])
    reviewed = "roast_message_ids" in activity
    months = {}
    for day in aggregate["days"]:
        month = day["date"][:7]
        if month not in months:
            months[month] = {"month": month, "active_days": 0, "messages": 0}
            if reviewed:
                months[month].update(roast_days=0, roast_messages=0)
        row = months[month]
        row["active_days"] += 1
        row["messages"] += day["count"]
        if reviewed:
            row["roast_days"] += int(day["roast_count"] > 0)
            row["roast_messages"] += day["roast_count"]
    selected = select_active_months({month: row["active_days"] for month, row in months.items()
                                     if month in analysis_months})
    summary_keys = ["active_days", "messages"]
    if reviewed:
        summary_keys.extend(["roast_days", "roast_messages"])
    result = {
        "timezone": aggregate["timezone"],
        "coverage": aggregate["coverage"],
        "rhythm": rhythm,
        "selected_months": selected,
        "months": [months[month] for month in selected],
        "summary": {key: sum(months[month][key] for month in analysis_months) for key in summary_keys},
        "days": [
            {key: day[key] for key in ("date", "count", "roast_count") if key in day}
            for day in aggregate["days"] if day["date"][:7] in analysis_months
        ],
    }
    if "token_usage" in activity:
        result["token_usage"] = {key: activity["token_usage"][key] for key in (
            "total_tokens", "cached_input_tokens", "coverage", "scope")}
    target_zone = ZoneInfo(activity["timezone"])
    if "theme_message_ids" in activity:
        result["theme_stats"] = count_theme_messages(activity, analysis_months, target_zone)
    if "share_quotes" in activity:
        messages_by_id = {message["id"]: message for message in activity["messages"]}
        quotes = []
        for quote in activity["share_quotes"]:
            message = messages_by_id[quote["message_id"]]
            day = activity_timestamp(message["timestamp"], "shared quote timestamp").astimezone(target_zone).date().isoformat()
            if day[:7] in analysis_months:
                display_quote = quote.get("rewrite", quote)
                public_quote = {"date": day, "text": display_quote["text"]}
                if "rewrite" in quote:
                    public_quote["kind"] = "rewrite"
                if "emphasis" in display_quote:
                    public_quote["emphasis"] = display_quote["emphasis"]
                if "repeat_message_ids" in quote:
                    public_quote["repeat_count"] = len(quote["repeat_message_ids"])
                quotes.append(public_quote)
        result["share_quotes"] = quotes
    return result


def public_report(report, compact=False, include_story=True):
    """Whitelist display fields; never put private provenance in the HTML."""
    if not compact and "share_story" in report:
        raise ReportError("share_story: select compact mode to preserve the sharing selection")
    if compact:
        public = {key: copy.deepcopy(report[key]) for key in ("year", "mode", "period", "keywords")}
        public["person"] = {"name": report["person"]["name"]}
        if "theme" in report:
            public["theme"] = report["theme"]
        if include_story and "share_story" in report:
            selected = report["share_story"]["moment_indices"]
            scene_lines = [report["moments"][index]["text"] for index in selected]
            public["story"] = {
                "persona": report["identity"]["subtitle"],
                "scenes": [{"text": line} for line in scene_lines if len(line) <= 24][:2],
            }
        if "activity" in report:
            public["activity"] = compact_activity(report["activity"])
        return public
    public = {key: copy.deepcopy(report[key]) for key in (
        "schema_version", "year", "mode", "period", "person", "identity", "keywords")}
    public["phrase"] = {key: report["phrase"][key] for key in ("text", "note", "kind")}
    public["metrics"] = [{key: item[key] for key in ("label", "value", "unit")} for item in report["metrics"]]
    public["moments"] = [{key: item[key] for key in ("title", "text")} for item in report["moments"]]
    public["closing"] = {"text": report["closing"]["text"]}
    if "activity" in report:
        public["activity"] = summarize_activity(report["activity"])
    return public


def embed_template_assets(template):
    """Inline the local assets used by both the downloadable report and the web renderer."""
    assets = Path(__file__).resolve().parents[1] / "assets"
    font_marker = "__DISPLAY_FONT_BASE64__"
    prompt_marker = "__PORTABLE_PROMPT_JS__"
    try:
        if font_marker in template:
            font_bytes = (assets / "SmileySans-Oblique.woff2").read_bytes()
            template = template.replace(font_marker, base64.b64encode(font_bytes).decode("ascii"))
        if prompt_marker in template:
            prompt_js = (assets / "portable-prompt.js").read_text(encoding="utf-8")
            template = template.replace(prompt_marker, prompt_js)
    except OSError as exc:
        raise ReportError(f"could not read template asset: {exc.filename}") from exc
    return template


def render_report(report, template, compact=False, style=None):
    validate_report(report)
    if style == "print" and any("rewrite" in quote for quote in report.get("activity", {}).get("share_quotes", [])):
        raise ReportError("print reports require approved verbatim share_quotes; reselect the original lines to share")
    marker = "__REPORT_JSON__"
    if template.count(marker) != 1:
        raise ReportError("template: expected exactly one __REPORT_JSON__ marker")
    template = embed_template_assets(template)
    public = public_report(report, compact=compact, include_story=style in ("comic", "print"))
    payload = json.dumps(public, ensure_ascii=False, separators=(",", ":"))
    for char, escaped in [("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                          ("\u2028", "\\u2028"), ("\u2029", "\\u2029")]:
        payload = payload.replace(char, escaped)
    return template.replace(marker, payload)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="private report JSON path")
    source.add_argument("--demo", action="store_true", help="use the bundled fictional example")
    parser.add_argument("--output", type=Path, required=True, help="standalone HTML output path")
    parser.add_argument("--compact", action="store_true", help="use the compact template and minimal public fields")
    parser.add_argument("--style", choices=("classic", "comic", "print", "poster", "ticket"),
                        help="compact visual style; choosing any style implies --compact")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    input_path = root / "assets" / "demo-report.json" if args.demo else args.input
    try:
        if input_path.resolve() == args.output.resolve():
            raise ReportError("input and output must be different files")
        if input_path.stat().st_size > 32_000_000:
            raise ReportError("input exceeds 32 MB; keep only evidence and timestamps needed for this report")
        report = json.loads(input_path.read_text(encoding="utf-8"))
        style = args.style
        if isinstance(report, dict) and ("theme" in report or "share_story" in report):
            style = style or "comic"
            if "theme" in report and report["theme"] != "puai" and style not in {"print", "comic"}:
                raise ReportError("report.theme: themed posters require --style print or comic")
        compact = args.compact or style is not None
        if style == "print":
            template_name = "comic-template.html"
        elif style in {"comic", "poster", "ticket"}:
            template_name = f"{style}-template.html"
        else:
            template_name = "compact-template.html" if compact else "report-template.html"
        template = (root / "assets" / template_name).read_text(encoding="utf-8")
        html = render_report(report, template, compact=compact, style=style)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, ReportError) as exc:
        print(f"Could not build report: {exc}", file=sys.stderr)
        return 1
    print(f"Created {args.output.resolve()}")
    print("Private evidence was excluded. Open the HTML in a browser to review and save PNG.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
