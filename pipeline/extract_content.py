import trafilatura
import httpx
import re


MIN_PARA_CHARS = 8      # 少于该字符数的段落视为片段，合并到上一段
TAG_RE = re.compile(r"<[^>]+>")
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)


def _extract_paragraphs_raw(html):
    """从原始 HTML 用正则提取 <p> 段落"""
    return [re.sub(TAG_RE, "", p).strip() for p in P_RE.findall(html) if p.strip()]


def _extract_paragraphs_trafilatura(html):
    """trafilatura XML → 正则提取 <p>"""
    xml = trafilatura.extract(
        html,
        include_links=False,
        include_images=False,
        include_formatting=False,
        output_format="xml",
    )
    if not xml:
        return []
    return [re.sub(TAG_RE, "", p).strip() for p in P_RE.findall(xml) if p.strip()]


def _clean_paragraphs(paragraphs):
    """清洗段落：去重、合并短段、规整空白"""
    cleaned = []
    for p in paragraphs:
        p = re.sub(r"\s+", " ", p).strip()
        if not p:
            continue
        # 跳过与上一段完全相同的重复段落
        if cleaned and p == cleaned[-1]:
            continue
        if cleaned and len(p) < MIN_PARA_CHARS:
            cleaned[-1] = cleaned[-1] + " " + p
        else:
            cleaned.append(p)
    return cleaned


def extract_article(url, timeout=15):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text

        # 第一重: trafilatura XML → <p> 提取
        paragraphs = _extract_paragraphs_trafilatura(html)

        # 第二重: 原始 HTML → <p> 提取（兜底）
        if len(paragraphs) < 2:
            paragraphs = _extract_paragraphs_raw(html)

        if not paragraphs:
            return None

        paragraphs = _clean_paragraphs(paragraphs)

        text = "\n\n>>>\n\n".join(paragraphs)

        cjk = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
        if cjk > len(text) * 0.3:
            return None

        return text
    except Exception as e:
        print(f"[extract_article] 失败: {url} -> {e}")
        return None


def filter_by_length(text, min_words=300):
    if not text:
        return False
    clean = text.replace("\n", " ").replace(">>>", "")
    return len(clean.split()) >= min_words
