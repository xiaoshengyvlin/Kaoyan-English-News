import feedparser
import yaml
from pathlib import Path

CONFIG = yaml.safe_load(
    (Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8")
)


def fetch_rss(url, origin_label):
    feed = feedparser.parse(url)
    if feed.bozo:
        print(f"[fetch_rss] 警告: RSS 解析异常 {url} -> {feed.bozo_exception}")
    candidates = []

    for entry in feed.entries[:10]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        if not title or not link:
            continue
        summary = entry.get("summary", "")
        candidates.append({
            "title": title,
            "url": link,
            "source_site": origin_label,
            "source_name": origin_label,
            "summary": summary,
            "origin": origin_label,
        })

    return candidates


def fetch_bbc():
    url = CONFIG["rss"]["bbc"]
    return fetch_rss(url, "bbc")


def fetch_guardian():
    url = CONFIG["rss"]["guardian"]
    return fetch_rss(url, "guardian")
