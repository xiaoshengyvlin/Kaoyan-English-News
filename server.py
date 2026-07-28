import re
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).parent
CONFIG = yaml.safe_load((BASE / "config.yaml").read_text(encoding="utf-8"))

app = FastAPI(title="Eng4KaoYan")


@app.middleware("http")
async def add_no_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.get("/api/vocab")
def get_vocab():
    vocab_path = BASE / CONFIG["storage"]["vocab_path"]
    if not vocab_path.exists():
        return {"error": "vocab not found"}
    return json.loads(vocab_path.read_text(encoding="utf-8"))


@app.get("/api/articles")
def get_articles(date: str = Query(default="")):
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return {"error": "invalid date format", "date": date, "articles": []}

    # 优先读取逐句对照数据
    translate_path = BASE / "data" / "translate" / f"{date}.json"
    if translate_path.exists():
        return json.loads(translate_path.read_text(encoding="utf-8"))

    # 回退到普通文章
    articles_dir = BASE / CONFIG["storage"]["articles_dir"]
    file_path = (articles_dir / f"{date}.json").resolve()
    if not str(file_path).startswith(str(articles_dir.resolve())):
        return {"error": "invalid date", "date": date, "articles": []}

    if not file_path.exists():
        return {"error": "no articles for this date", "date": date, "articles": []}

    return json.loads(file_path.read_text(encoding="utf-8"))


@app.get("/api/dates")
def get_dates():
    dates = set()
    for d in ("data/articles", "data/translate"):
        dir_path = BASE / d
        if dir_path.exists():
            dates.update(f.stem for f in dir_path.glob("*.json"))
    return {"dates": sorted(dates, reverse=True)}


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = BASE / "web" / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "<h1>index.html not found</h1>"


app.mount("/static", StaticFiles(directory=str(BASE / "web")), name="static")


if __name__ == "__main__":
    import uvicorn
    cfg = CONFIG["server"]
    uvicorn.run(app, host=cfg["host"], port=cfg["port"])
