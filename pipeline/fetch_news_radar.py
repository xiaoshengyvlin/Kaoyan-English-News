import httpx
import yaml
import random
from pathlib import Path

CONFIG = yaml.safe_load(
    (Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8")
)


def fetch_candidates():
    url = CONFIG["news_radar"]["api_url"]
    english_sources = set(CONFIG["news_radar"]["english_sources"])

    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])
    candidates = []

    for item in items:
        site_id = item.get("site_id", "")
        if site_id not in english_sources:
            continue
        if not item.get("url"):
            continue

        title_en = item.get("title_en") or item.get("title_original", "")
        if not title_en or len(title_en) < 5:
            continue

        candidates.append({
            "title": title_en,
            "url": item["url"],
            "source_site": site_id,
            "source_name": item.get("site_name", ""),
            "summary": item.get("title_bilingual", ""),
            "origin": "radar",
        })

    random.shuffle(candidates)
    return candidates
