#!/usr/bin/env python3
"""ارسال لینک ریلیزهای ساخته‌شده به تلگرام، به ترتیب زمانی."""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ["GITHUB_REPOSITORY"]
BOT = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
PREFIX = os.environ["TAG_PREFIX"]
SYMBOL = os.environ.get("INSTRUMENT_UPPER", "")
TIMEFRAME = os.environ.get("TIMEFRAME", "tick")
CHUNKS = json.loads(os.environ.get("CHUNKS") or "[]")

if not BOT or not CHAT:
    print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID تنطیم نشده — ارسال رد شد.")
    sys.exit(0)


def gh_get(path):
    request = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Authorization": "Bearer " + GH_TOKEN,
            "Accept": "application/vnd.github+json",
            "User-Agent": "dukascopy-downloader",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def telegram_send(text, keyboard):
    payload = {
        "chat_id": CHAT,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(
            {"inline_keyboard": keyboard}, ensure_ascii=False
        )

    data = urllib.parse.urlencode(payload).encode()
    url = "https://api.telegram.org/bot{}"
    url = "https://api.telegram.org/bot" + BOT + "/sendMessage"

    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.load(response)
            if body.get("ok"):
                return True
            print("Telegram error:", body)
        except Exception as err:
            print("attempt {} failed: {}".format(attempt, err))
        time.sleep(3)

    return False


def megabytes(size):
    return "{:.2f}".format(size / 1024 / 1024)


missing = []
failed = []

for chunk in CHUNKS:
    tag = "{}{}-to-{}".format(PREFIX, chunk["from"], chunk["to"])

    try:
        release = gh_get(
            "/repos/{}/releases/tags/{}".format(REPO, urllib.parse.quote(tag))
        )
    except urllib.error.HTTPError as err:
        print("ریلیز پیدا نشد ({}): {}".format(err.code, tag))
        missing.append(tag)
        continue

    assets = sorted(release.get("assets", []), key=lambda item: item.get("name", ""))
    assets = [item for item in assets if ".zip" in item.get("name", "")]

    if not assets:
        print("ریلیز فایلی ندارد:", tag)
        missing.append(tag)
        continue

    total = sum(item.get("size", 0) for item in assets)

    if len(assets) == 1:
        keyboard = [[{"text": "⬇️ DOWNLOAD", "url": assets[0]["browser_download_url"]}]]
        parts_line = ""
    else:
        keyboard = [
            [{"text": "⬇️ PART {}".format(index), "url": item["browser_download_url"]}]
            for index, item in enumerate(assets, start=1)
        ][:8]
        parts_line = "\n🧩 قطعات: {}".format(len(assets))

    text = (
        "<b>📦 {} {} data</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "📅 {} → {}\n"
        "💾 حجم: {} MB{}"
    ).format(SYMBOL, TIMEFRAME, chunk["from"], chunk["to"], megabytes(total), parts_line)

    print("ارسال:", tag)
    if not telegram_send(text, keyboard):
        failed.append(tag)

    time.sleep(2)

sent = len(CHUNKS) - len(failed) - len(missing)
print("\nخلاصه: ارسال‌شده={} ناموفق={} بدون‌ریلیز={}".format(sent, len(failed), len(missing)))

if failed:
    sys.exit(1)
