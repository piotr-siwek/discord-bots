"""Wowhead -> Discord webhook. Posts new WoW: Forever news. Stdlib only."""
import html, json, os, re, sys, time, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).parent
STATE = BASE / "seen.json"
MEDIA = "{http://search.yahoo.com/mrss/}content"


def load_env():
    f = BASE / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def fetch(url, data=None):
    req = urllib.request.Request(
        url, data=data, headers={"User-Agent": "Mozilla/5.0 (forever-news-bot)",
                                 **({"Content-Type": "application/json"} if data else {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def parse(feed_url):
    root = ET.fromstring(fetch(feed_url))
    for it in root.iter("item"):
        desc = re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description", "")))
        desc = re.sub(r"\s+", " ", desc).replace("Continue reading »", "").strip()
        media = it.find(MEDIA)
        yield {
            "id": it.findtext("guid") or it.findtext("link"),
            "title": it.findtext("title", ""),
            "link": it.findtext("link", ""),
            "desc": desc,
            "image": media.get("url") if media is not None else None,
            "date": it.findtext("pubDate", ""),
        }


def post(webhook, a):
    embed = {"title": a["title"][:256], "url": a["link"], "description": a["desc"][:400],
             "color": 0xE6B800, "footer": {"text": "Wowhead • WoW: Forever"}}
    if a["image"]:
        embed["image"] = {"url": a["image"]}
    body = json.dumps({"username": "Forever News", "embeds": [embed]}).encode()
    fetch(webhook, body)


def main():
    load_env()
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        sys.exit("Brak DISCORD_WEBHOOK_URL w .env")
    feed = os.environ.get("FEED_URL", "https://www.wowhead.com/news/rss/classic")
    keywords = [k.strip().lower() for k in os.environ.get("KEYWORDS", "forever").split(",") if k.strip()]
    interval = int(os.environ.get("INTERVAL_MINUTES", "0"))  # 0 = jednorazowo

    while True:
        first_run = not STATE.exists()
        seen = set(json.loads(STATE.read_text())) if not first_run else set()
        items = list(parse(feed))
        new = [a for a in items if a["id"] not in seen]
        # przy pierwszym uruchomieniu tylko zapamiętaj, nie spamuj starymi newsami
        if not first_run:
            for a in reversed(new):  # od najstarszych
                if any(k in (a["title"] + " " + a["desc"]).lower() for k in keywords):
                    post(webhook, a)
                    print("Wysłano:", a["title"])
                    time.sleep(1)
        seen |= {a["id"] for a in items}
        STATE.write_text(json.dumps(sorted(seen)))
        if not interval:
            break
        time.sleep(interval * 60)


if __name__ == "__main__":
    main()
