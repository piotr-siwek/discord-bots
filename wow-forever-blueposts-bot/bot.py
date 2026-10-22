"""Wowhead Blue Tracker -> Discord webhook. Posts new Blizzard posts about WoW: Forever. Stdlib only."""
import html, json, os, re, sys, time, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).parent
STATE = BASE / "seen.json"
FEED = "https://www.wowhead.com/blue-tracker?rss"
TITLE_SUFFIX = re.compile(r"\s+\W?\s*World of Warcraft\s+\W?\s*Blizzard News$")


def load_env():
    f = BASE / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def fetch(url, data=None):
    req = urllib.request.Request(
        url, data=data, headers={"User-Agent": "Mozilla/5.0 (forever-bluepost-bot)",
                                 **({"Content-Type": "application/json"} if data else {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def parse(feed_url):
    """Zwraca posty bez duplikatów (feed ma osobne wpisy dla US/EU oraz news/topic)."""
    best = {}
    for it in ET.fromstring(fetch(feed_url)).iter("item"):
        title = TITLE_SUFFIX.sub("", it.findtext("title", "")).strip()
        raw = html.unescape(it.findtext("description", ""))
        author = re.search(r">([^<]+)</a>\s+on\s", raw)
        desc = re.sub(r"<[^>]+>", " ", raw.split("By<a")[0].split("<br>")[0])
        link = it.findtext("link", "")
        key = re.sub(r"[^a-z0-9]", "", title.lower())
        a = {"id": key, "title": title, "link": link, "desc": re.sub(r"\s+", " ", desc).strip(),
             "author": author.group(1) if author else "Blizzard", "date": it.findtext("pubDate", "")}
        # preferuj wersję US i stronę newsa nad EU/forum
        score = ("/us/" in link) + 2 * ("/news/" in link)
        if key not in best or score > best[key][0]:
            best[key] = (score, a)
    return [a for _, a in best.values()]


def post(webhook, a):
    embed = {"title": a["title"][:256], "url": a["link"], "description": a["desc"][:400],
             "color": 0x0070DD, "author": {"name": a["author"]},
             "footer": {"text": "Wowhead Blue Tracker • WoW: Forever"}}
    fetch(webhook, json.dumps({"username": "Forever Blue Posts", "embeds": [embed]}).encode())


def main():
    load_env()
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        sys.exit("Brak DISCORD_WEBHOOK_URL w .env")
    keywords = [k.strip().lower() for k in os.environ.get("KEYWORDS", "forever").split(",") if k.strip()]
    # domyślnie tylko tytuł: opisy bywają reklamowe (np. "Unlock a Year of WoW" wspomina Forever)
    match_desc = os.environ.get("MATCH_DESCRIPTION", "0") == "1"
    first_run = not STATE.exists()
    seen = set(json.loads(STATE.read_text())) if not first_run else set()
    items = parse(FEED)
    if not first_run:
        for a in reversed([a for a in items if a["id"] not in seen]):
            text = a["title"] + (" " + a["desc"] if match_desc else "")
            if any(k in text.lower() for k in keywords):
                post(webhook, a)
                print("Wysłano:", a["title"])
                time.sleep(1)
    seen |= {a["id"] for a in items}
    STATE.write_text(json.dumps(sorted(seen)))


if __name__ == "__main__":
    main()
