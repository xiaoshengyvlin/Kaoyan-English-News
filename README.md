# Zako烤盐英语新闻

每日自动抓取英文科技新闻，AI 翻译为中文，段落逐句对照展示，考研词汇高亮标注。

**线上地址**: [kaoyan.0721001.xyz](https://kaoyan.0721001.xyz)

## 功能

- 每日从 NewsRadar / BBC / Guardian 自动抓取 10 篇英文科技新闻
- DeepSeek 两阶段翻译：全文翻译 → 逐段中英句子对齐
- 前端段落+句子双语对照阅读
- 考研红宝书词汇（必考词 + 基础词 + 超纲词，5370 词）自动高亮，悬停显示释义
- 来源可点击跳转原文，日期选择器切换历史文章

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.12, FastAPI, uvicorn |
| 翻译 | DeepSeek V4 Flash API（OpenAI SDK） |
| 正文提取 | trafilatura + 正则 `<p>` 标签双重提取 |
| 前端 | 原生 JavaScript（无框架）, CSS |
| 定时任务 | Linux crontab（每天 8:00） |

## 项目结构

```
├── server.py                 # FastAPI 接口
├── config.yaml               # 配置文件（需自行创建，见下方说明）
├── config.example.yaml       # 配置文件模板
├── requirements.txt
├── pipeline/
│   ├── daily_job.py          # 每日任务编排（fetch / translate）
│   ├── fetch_news_radar.py   # NewsRadar 聚合源
│   ├── fetch_rss.py          # BBC / Guardian RSS
│   ├── extract_content.py    # 正文提取 + 段落清洗
│   ├── translate.py          # 翻译 + 逐段对齐
│   └── build_vocab.py        # 构建词汇库
├── web/
│   ├── index.html
│   ├── app.js                # 前端渲染逻辑
│   └── style.css
└── data/
    ├── vocab.json            # 考研词汇库（5370 词）
    ├── redbook_words.json    # 红宝书原始分类数据
    ├── raw/                  # 爬取原文中间产物（不入库）
    ├── articles/             # 最终文章（不入库）
    └── translate/            # 逐句对照数据（不入库）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建配置文件

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入你的 [DeepSeek API Key](https://platform.deepseek.com/)：

```yaml
deepseek:
  api_key: "sk-xxxxxxxxxxxxxxxx"
```

### 3. 爬取 + 翻译

```bash
# 第一步：爬取今日英文新闻（保存到 data/raw/）
python pipeline/daily_job.py fetch

# 第二步：翻译（读取 raw → 生成 data/translate/ + data/articles/）
python pipeline/daily_job.py translate

# 或一步完成
python pipeline/daily_job.py
```

### 4. 启动服务

```bash
python server.py
# 访问 http://localhost:8081
```

### 5. 定时任务（可选）

```bash
crontab -e
# 添加：每天 8:00 自动执行
0 8 * * * cd /path/to/project && /usr/bin/python3 pipeline/daily_job.py >> logs/daily_job.log 2>&1
```

## 词汇库

词汇数据来自 [2027 考研英语红宝书](https://github.com/3056810551/2027-kaoyan-english-redbook-json)，包含三类：

| 类别 | 词数 |
|---|---|
| 必考词 | ~1822 |
| 基础词 | ~2533 |
| 超纲词 | ~1015 |

已排除简单基础词（the, a, is 等 1177 个）。

如果需要重新构建词汇库：

```bash
python pipeline/build_vocab.py
```

## 翻译流程

```
英文原文（>>> 分段标记）
    ↓
第 1 次 API：全文翻译（with thinking）
    ↓
拆分为 N 个段落，并发逐段对齐（第 2-N 次 API，no thinking）
    ↓
合并 → data/translate/ 逐句对照 JSON
    ↓
前端直接渲染，无需前端做句子切分
```

## 数据源

| 来源 | 每日配额 | 类型 |
|---|---|---|
| NewsRadar（10 个英语源） | 6 篇 | API |
| BBC News | 2 篇 | RSS |
| The Guardian | 2 篇 | RSS |

## 配置说明

```yaml
allocation:
  total: 10        # 每日文章总数
  radar: 6         # NewsRadar 配额
  bbc: 2           # BBC 配额
  guardian: 2      # Guardian 配额

content:
  min_word_count: 300   # 最小词数
  max_word_count: 1500  # 最大词数
```
