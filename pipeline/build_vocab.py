"""从 2027 考研英语红宝书 category_page_assign.json 构建 vocab.json。
数据来源: https://github.com/3056810551/2027-kaoyan-english-redbook-json
分类: 必考词 / 基础词 / 超纲词（排除简单基础词）
"""
import re
import json
import unicodedata
from pathlib import Path

BASE = Path(__file__).parent.parent
INPUT = BASE / "data" / "redbook_words.json"
OUTPUT = BASE / "data" / "vocab.json"

# NFKC 无法处理的 CJK Radicals Supplement 字符→标准汉字映射
RADICAL_TO_HAN = str.maketrans({
    "\u2E9F":  "\u6BCD",  # ⺟ → 母
    "\u2EA0":  "\u6C11",  # ⺠ → 民
    "\u2EC5":  "\u89C1",  # ⻅ → 见
    "\u2EC6":  "\u89D2",  # ⻆ → 角
    "\u2EC9":  "\u8D1D",  # ⻉ → 贝
    "\u2ECB":  "\u8F66",  # ⻋ → 车
    "\u2ED3":  "\u957F",  # ⻓ → 长
    "\u2ED4":  "\u95E8",  # ⻔ → 门
    "\u2ED8":  "\u9752",  # ⻘ → 青
    "\u2EDA":  "\u9875",  # ⻚ → 页
    "\u2EDB":  "\u98CE",  # ⻛ → 风
    "\u2EDC":  "\u98DE",  # ⻜ → 飞
    "\u2EDD":  "\u98DF",  # ⻝ → 食
    "\u2EE2":  "\u9A6C",  # ⻢ → 马
    "\u2EE3":  "\u9AA8",  # ⻣ → 骨
    "\u2EE4":  "\u9B3C",  # ⻤ → 鬼
    "\u2EE5":  "\u9C7C",  # ⻥ → 鱼
    "\u2EE6":  "\u9E1F",  # ⻦ → 鸟
    "\u2EE8":  "\u9EA6",  # ⻨ → 麦
    "\u2EE9":  "\u9EC4",  # ⻩ → 黄
    "\u2EEC":  "\u9F50",  # ⻬ → 齐
    "\u2EEE":  "\u9F7F",  # ⻮ → 齿
    "\u2EF0":  "\u9F99",  # ⻰ → 龙
})


def parse_meaning(meaning):
    meaning = re.sub(r"\([^)]*\)", "", meaning)
    meaning = re.sub(r"\[[^\]]*\]", "", meaning)
    meaning = re.sub(r"^\s*&\s*", "", meaning)
    meaning = re.sub(r"\s+", " ", meaning).strip()

    meanings = []
    for part in re.split(r"[;；]", meaning):
        for sub in re.split(r"[，,]", part):
            sub = sub.strip().rstrip(".")
            if sub and sub not in meanings:
                meanings.append(sub)
    return meanings


def main():
    raw = json.loads(INPUT.read_text(encoding="utf-8"))
    vocab = {}
    for item in raw:
        if (item.get("page", "") or "").startswith("简单基础词"):
            continue
        word = item["word"].lower().strip()
        meaning = unicodedata.normalize("NFKC", item["meaning"])
        meaning = meaning.translate(RADICAL_TO_HAN)
        meanings = parse_meaning(meaning)
        if not meanings:
            continue
        if word not in vocab:
            vocab[word] = meanings
        else:
            for m in meanings:
                if m not in vocab[word]:
                    vocab[word].append(m)
    OUTPUT.write_text(json.dumps(vocab, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done: {len(vocab)} words")
    for k in list(vocab.keys())[:5]:
        print(f"  {k}: {vocab[k]}")

if __name__ == "__main__":
    main()
