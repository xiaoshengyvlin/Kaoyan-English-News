import json
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.fetch_news_radar import fetch_candidates as fetch_radar
from pipeline.fetch_rss import fetch_bbc, fetch_guardian
from pipeline.extract_content import extract_article
from pipeline.translate import translate, translate_title

BASE = Path(__file__).parent.parent
CONFIG = yaml.safe_load((BASE / "config.yaml").read_text(encoding="utf-8"))


def extract_candidates(candidates, max_attempts=20):
    result = []
    for c in candidates[:max_attempts]:
        text = extract_article(c["url"])
        if not text:
            continue
        wc = len(text.split())
        if wc < CONFIG["content"]["min_word_count"] or wc > CONFIG["content"]["max_word_count"]:
            continue
        c["content_en"] = text
        c["word_count"] = len(text.split())
        result.append(c)
    return result


def collect_from_source(source_name, fetch_fn, target_count):
    raw = fetch_fn()
    print(f"  [{source_name}] 候选 {len(raw)} 篇")
    extracted = extract_candidates(raw)
    print(f"  [{source_name}] 提取成功 {len(extracted)} 篇")
    return extracted[:target_count]


def translate_one(idx, total, article):
    title = article["title"]
    print(f"  [{idx+1}/{total}] 翻译: {title[:60]}...")
    try:
        bilingual, full_zh, align_raws = translate(article["content_en"])
        article["_bilingual"] = bilingual
        article["_full_zh"] = full_zh
        article["_align_raws"] = align_raws
        article["title_zh"] = translate_title(title)
        article["content_zh"] = "\n\n".join(
            "\n".join(p["zh"] for p in para)
            for para in bilingual
        )
        return article
    except Exception as e:
        print(f"    [{idx+1}/{total}] 失败: {e}")
        return None


def fill_remaining(sources, pool_candidates, total):
    current = sum(len(s) for s in sources)
    if current >= total:
        return
    seen_urls = set()
    for s in sources:
        seen_urls.update(a["url"] for a in s)
    needed = total - current
    for a in pool_candidates:
        if a["url"] in seen_urls:
            continue
        sources.append([a])
        seen_urls.add(a["url"])
        needed -= 1
        if needed <= 0:
            break


def do_fetch(date_str):
    cfg = CONFIG["allocation"]
    raw_dir = BASE / CONFIG["storage"]["raw_dir"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{date_str}.json"

    if raw_path.exists():
        print(f"[{date_str}] 原始文件已存在，跳过爬取: {raw_path}")
        return

    print(f"[{date_str}] 开始爬取...")
    print(f"  分配: Radar={cfg['radar']}, BBC={cfg['bbc']}, Guardian={cfg['guardian']}")

    radar_articles = collect_from_source("Radar", fetch_radar, cfg['radar'])
    bbc_articles = collect_from_source("BBC", fetch_bbc, cfg['bbc'])
    guardian_articles = collect_from_source("Guardian", fetch_guardian, cfg['guardian'])

    all_by_source = [radar_articles, bbc_articles, guardian_articles]
    all_flat = [a for group in all_by_source for a in group]

    if len(all_flat) < cfg["total"]:
        remaining = extract_candidates(fetch_radar(), max_attempts=50)
        fill_remaining(all_by_source, remaining, cfg["total"])
        all_flat = [a for group in all_by_source for a in group]

    raw_path.write_text(json.dumps(all_flat, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  已保存 {len(all_flat)} 篇 -> {raw_path}")


def do_translate(date_str):
    raw_path = BASE / CONFIG["storage"]["raw_dir"] / f"{date_str}.json"
    if not raw_path.exists():
        print(f"[{date_str}] 未找到原始文件: {raw_path}")
        print(f"  请先运行: python pipeline/daily_job.py fetch")
        return

    all_flat = json.loads(raw_path.read_text(encoding="utf-8"))
    print(f"[{date_str}] 读取原始文章 {len(all_flat)} 篇，开始翻译...")

    articles = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(translate_one, i, len(all_flat), a): i for i, a in enumerate(all_flat)}
        for f in as_completed(futures):
            result = f.result()
            if result:
                articles.append((futures[f], result))

    articles.sort(key=lambda x: x[0])
    articles = [a for _, a in articles]

    print(f"\n  成功翻译 {len(articles)}/{len(all_flat)} 篇")

    articles_dir = BASE / CONFIG["storage"]["articles_dir"]
    articles_dir.mkdir(parents=True, exist_ok=True)
    output_path = articles_dir / f"{date_str}.json"

    output = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(articles),
        "articles": articles,
    }

    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  已保存 {len(articles)} 篇 -> {output_path}")

    # Save bilingual structured data to data/translate/
    if articles and "_bilingual" in articles[0]:
        translate_dir = BASE / "data" / "translate"
        translate_dir.mkdir(parents=True, exist_ok=True)

        # 最终合并结果
        tl_data = {
            "date": date_str,
            "articles": [
                {
                    "title": a.get("title", ""),
                    "title_zh": a.get("title_zh", ""),
                    "source_name": a.get("source_name", ""),
                    "url": a.get("url", ""),
                    "word_count": a.get("word_count", 0),
                    "paragraphs": a["_bilingual"],
                }
                for a in articles if "_bilingual" in a
            ],
        }
        (translate_dir / f"{date_str}.json").write_text(
            json.dumps(tl_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  逐句对照已保存 -> {translate_dir}/{date_str}.json")

        # Step 1 中间文件：全文翻译
        dir1 = translate_dir / "1"
        dir1.mkdir(parents=True, exist_ok=True)
        for a in articles:
            if a.get("_full_zh"):
                safe_title = "".join(c if c.isalnum() or c in "_-" else "_" for c in a.get("title", "unknown")[:40])
                (dir1 / f"{safe_title}.txt").write_text(a["_full_zh"], encoding="utf-8")
        print(f"  全文翻译已保存 -> {dir1}/")

        # Step 2 中间文件：逐段对齐原始输出
        dir2 = translate_dir / "2"
        dir2.mkdir(parents=True, exist_ok=True)
        for a in articles:
            if a.get("_align_raws"):
                safe_title = "".join(c if c.isalnum() or c in "_-" else "_" for c in a.get("title", "unknown")[:40])
                content = "\n\n<<<段落分隔>>>\n\n".join(
                    f"--- 段落 {i+1} ---\n{raw}"
                    for i, raw in enumerate(a["_align_raws"])
                )
                (dir2 / f"{safe_title}.txt").write_text(content, encoding="utf-8")
        print(f"  逐段对齐已保存 -> {dir2}/")


def run():
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    do_fetch(date_str)
    do_translate(date_str)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        do_fetch(date_str)
    elif len(sys.argv) > 1 and sys.argv[1] == "translate":
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        do_translate(date_str)
    else:
        run()
