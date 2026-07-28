import yaml
from pathlib import Path
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

CONFIG = yaml.safe_load(Path(__file__).parent.parent.joinpath("config.yaml").read_text(encoding="utf-8"))

TRANSLATE_PROMPT = """你是资深科技翻译，将英文科技新闻译为地道流畅的中文。最高优先级：译文读起来像中文母语者写的，不生硬、不翻译腔。

【翻译规范】
- 直译优先，但中文不通时必须意译，以流畅度为重
- 长句断成短句，英文被动式转中文主动式，插入语用破折号处理
- 人名、公司名、产品名保留原文不译
- 专业术语首次出现时括号标注英文，如：大语言模型(LLM)
- 数字、日期、百分比、引号格式与原文一致

【禁止】
- 不得添加讲解、评论或原文没有的信息
- 不得省略或概括任何段落

【输出格式】
原文以 >>> 分隔段落，译文同样以 >>> 独占一行分隔段落。段落内只输出中文。

示例输入:
The new chip, which was unveiled at CES, delivers a 40% performance boost compared to its predecessor.
>>>
Analysts caution that mass production remains at least two years away.

示例输出:
这款在CES上发布的新芯片性能比前代提升了40%。
>>>
分析人士警告称，大规模量产至少还需两年。

只输出译文。"""

TITLE_PROMPT = """将以下英文新闻标题翻译为中文。

要求：
1. 人名、公司名、产品名不翻译，直接保留英文原文
2. 控制在30字以内，突出核心信息
3. 保持新闻标题的语感和吸引力

只输出译文，不要任何解释。"""

ALIGN_PROMPT = """将一段英文及其对应中文译文逐句中英对照输出。

要求：
- 每句英文以 EN: 开头，中文以 ZH: 开头，严格交替排列
- 句数一致，不得缺漏、合并或拆分句子
- 去除完全相同的重复句子对

示例输入：
EN段落: The new chip is faster. Analysts remain cautious.
ZH段落: 新芯片速度更快。分析人士仍持谨慎态度。

示例输出：
EN: The new chip is faster.
ZH: 新芯片速度更快。
EN: Analysts remain cautious.
ZH: 分析人士仍持谨慎态度。"""


def _get_client():
    cfg = CONFIG["deepseek"]
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def _call(client, system, user, max_tokens=4096, thinking=False):
    cfg = CONFIG["deepseek"]
    kwargs = dict(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
    )
    if not thinking:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    resp = client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content
    if content is None:
        raise ValueError("DeepSeek API returned empty content")
    return content.strip()


def _parse_pairs(raw):
    pairs = []
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    for i in range(len(lines)):
        if lines[i].startswith("EN:") and i + 1 < len(lines) and lines[i + 1].startswith("ZH:"):
            pairs.append({"en": lines[i][3:].strip(), "zh": lines[i + 1][3:].strip()})
    return pairs


def translate(text):
    """全文翻译 → 逐段对齐 → 返回(结构化输出, 全文译文, 对齐原始输出列表)"""
    client = _get_client()

    # Step 1: 全文翻译（保持段落）
    full_zh = _call(client, TRANSLATE_PROMPT, text, max_tokens=16384, thinking=True)

    # 拆分英文和中文段落
    en_paras = [p.strip() for p in text.split("\n\n>>>\n\n") if p.strip()]
    zh_paras = [p.strip() for p in full_zh.split(">>>") if p.strip()]

    if not en_paras:
        return [], full_zh, []

    # Step 2: 逐段对齐（并发）
    results = [None] * len(en_paras)
    align_raws = [None] * len(en_paras)

    def _align(i, en_p, zh_p):
        if i >= len(zh_paras):
            return i, [], ""
        user = f"EN段落: {en_p}\n\nZH段落: {zh_p}"
        raw = _call(client, ALIGN_PROMPT, user, max_tokens=2048, thinking=False)
        return i, _parse_pairs(raw), raw

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_align, i, en_paras[i], zh_paras[i] if i < len(zh_paras) else ""): i for i in range(len(en_paras))}
        for f in as_completed(futures):
            i, pairs, raw = f.result()
            results[i] = pairs
            align_raws[i] = raw

    paragraphs = [r for r in results if r]
    return paragraphs, full_zh, [r for r in align_raws if r]


def translate_title(title):
    client = _get_client()
    return _call(client, TITLE_PROMPT, title, max_tokens=512, thinking=False)
