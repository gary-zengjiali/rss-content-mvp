# RSS Content MVP

Python + SQLite 的 RSS 内容中台 MVP。

## 功能

- 可配置 RSS 源（YAML）
- 抓取 RSS 条目并写入 SQLite
- 基于链接/标题的轻量去重
- 网页正文抽取（可选 enrich）
- 生成当日 Markdown 简报
- 生成选题池（基于关键词和热度信号）
- 输出 JSON / Markdown 文件

## 目录结构

```txt
rss-content-mvp/
  config/
    sources.yaml
    topics.yaml
    sync.yaml
  data/
    rss_mvp.db
  output/
    daily/
    topics/
  src/rss_mvp/
    cli.py
    db.py
    models.py
    config.py
    fetcher.py
    scoring.py
    digest.py
```

## 快速开始

### 1. 创建虚拟环境并安装依赖

```bash
cd rss-content-mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置 RSS 源

编辑 `config/sources.yaml`，你可以自由增删 RSS 源。

### 3. 初始化数据库

```bash
python -m rss_mvp.cli init-db
```

### 4. 抓取 RSS

```bash
python -m rss_mvp.cli fetch
```

### 5. 生成日报

```bash
python -m rss_mvp.cli digest --date 2026-03-17
```

### 6. 生成选题池

```bash
python -m rss_mvp.cli topics --date 2026-03-17
```

## 常用命令

```bash
python -m rss_mvp.cli init-db
python -m rss_mvp.cli fetch
python -m rss_mvp.cli digest --date YYYY-MM-DD
python -m rss_mvp.cli enrich --date YYYY-MM-DD --limit 20
python -m rss_mvp.cli topics --date YYYY-MM-DD
python -m rss_mvp.cli sync --date YYYY-MM-DD --target all
python -m rss_mvp.cli run-daily --sync-target all
```

## 同步配置说明

编辑 `config/sync.yaml`：

- `github.enabled`: 是否启用 Git 同步
- `github.repo_path`: 本地 Git 仓库路径
- `github.branch`: 目标分支
- `github.remote`: 远端名，默认 `origin`
- `github.auto_push`: 是否在 commit 后自动 push
- `obsidian.enabled`: 是否启用 Obsidian 镜像
- `obsidian.vault_path`: 你的 Vault 根目录
- `obsidian.target_subdir`: 输出到 Vault 下的子目录

同步命令：

```bash
./run.sh sync --date YYYY-MM-DD --target github
./run.sh sync --date YYYY-MM-DD --target obsidian
./run.sh sync --date YYYY-MM-DD --target all
```

`run-daily` 也支持：

```bash
./run.sh run-daily --date YYYY-MM-DD --enrich-limit 20 --sync-target all
```

## RSS 源配置说明

`config/sources.yaml` 示例：

```yaml
sources:
  - id: openai_blog
    name: OpenAI Blog
    url: https://openai.com/blog/rss.xml
    category: ai-research
    enabled: true
    priority: 10
```

字段说明：

- `id`: 唯一标识
- `name`: 展示名称
- `url`: RSS 地址
- `category`: 分类
- `enabled`: 是否启用
- `priority`: 源优先级，越高越重要

## OpenClaw 定时任务建议

你后面可以把下面几步拆成 cron：

- 凌晨/清晨：`fetch`
- 早上：`enrich`
- 早上：`digest`
- 早上：`topics`

推荐串起来的执行方式：

```bash
./run.sh fetch
./run.sh enrich --date YYYY-MM-DD --limit 20
./run.sh digest --date YYYY-MM-DD
./run.sh topics --date YYYY-MM-DD

# 或一键
./run.sh run-daily --date YYYY-MM-DD --enrich-limit 20
```

## 后续扩展

- 接 LLM 摘要/改写
- GitHub 自动提交
- Obsidian 同步
- Web Dashboard
