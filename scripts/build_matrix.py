#!/usr/bin/env python3
"""ساخت لیست بازه‌های ماهانه/سالانه برای matrix و چاپ در قالب GITHUB_OUTPUT."""
import json
import os
import sys
from datetime import date

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

start = parse_date(os.environ["RAW_FROM"])
end = parse_date(os.environ["RAW_TO"])

if start >= end:
    sys.exit("ERROR: from باید کوچک‌تر از to باشد ({} >= {})".format(start, end))

chunks = []
cursor = start
while cursor < end:
    if mode == "year":
        upper = date(cursor.year + 1, 1, 1)
    else:
        upper = next_month(date(cursor.year, cursor.month, 1))
    if upper > end:
        upper = end
    chunks.append({"from": cursor.isoformat(), "to": upper.isoformat()})
    cursor = upper

if len(chunks) > MAX_JOBS:
    sys.exit(
        "ERROR: {} job لازم است ولی سقف matrix در گیت‌هاب {} است. "
        "بازه را کوتاه‌تر کنید یا chunk=year بگذارید.".format(len(chunks), MAX_JOBS)
    )

print("instrument=" + symbol)
print("instrument_upper=" + raw_symbol.upper())
print("tag_prefix={}-{}-".format(symbol, timeframe))
print("chunk_count={}".format(len(chunks)))
print("chunks=" + json.dumps(chunks, separators=(",", ":")))
