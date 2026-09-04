#!/usr/bin/env python3
"""ساخت لیست بازه‌های هفتگی/ماهانه/سالانه برای matrix و چاپ در قالب GITHUB_OUTPUT."""
import json
import os
import sys
from datetime import date, timedelta

MAX_JOBS = 256


def parse_date(raw):
    txt = raw.strip().split("T")[0].split(" ")[0]
    year, month, day = (int(part) for part in txt.split("-"))
    return date(year, month, day)


def next_month(day):
    year = day.year + day.month // 12
    month = day.month % 12 + 1
    return date(year, month, 1)


raw_symbol = os.environ["RAW_INSTRUMENT"].strip().replace(" ", "")
symbol = raw_symbol.lower()
timeframe = (os.environ.get("TIMEFRAME") or "tick").strip()
mode = (os.environ.get("CHUNK") or "month").strip()

if mode not in ("week", "month", "year"):
    sys.exit("ERROR: chunk باید week یا month یا year باشد (مقدار داده‌شده: {})".format(mode))

start = parse_date(os.environ["RAW_FROM"])
end = parse_date(os.environ["RAW_TO"])

if start >= end:
    sys.exit("ERROR: from باید کوچک‌تر از to باشد ({} >= {})".format(start, end))

chunks = []
cursor = start
while cursor < end:
    if mode == "year":
        upper = date(cursor.year + 1, 1, 1)
    elif mode == "week":
        upper = cursor + timedelta(days=7)
    else:
        upper = next_month(date(cursor.year, cursor.month, 1))

    if upper > end:
        upper = end

    chunks.append({"from": cursor.isoformat(), "to": upper.isoformat()})
    cursor = upper

if len(chunks) > MAX_JOBS:
    sys.exit(
        "ERROR: {} job لازم است ولی سقف matrix در گیت‌هاب {} است. "
        "بازه را کوتاه‌تر کنید یا chunk بزرگ‌تری انتخاب کنید.".format(len(chunks), MAX_JOBS)
    )

if len(chunks) > 24 and timeframe == "tick":
    print(
        "::warning::{} بازه تیک‌دیتا به‌صورت ترتیبی اجرا می‌شود؛ "
        "ممکن است چند ساعت طول بکشد.".format(len(chunks)),
        file=sys.stderr,
    )

print("instrument=" + symbol)
print("instrument_upper=" + raw_symbol.upper())
print("tag_prefix={}-{}-".format(symbol, timeframe))
print("chunk_count={}".format(len(chunks)))
print("chunks=" + json.dumps(chunks, separators=(",", ":")))
