---
name: github-hot
description: 管理 GitHub 热度周榜：采集 Trending 数据、输出榜单、查看任务历史、启动 Web 仪表盘。当用户询问"本周 GitHub 涨星/热门项目"、"跑一次采集"、"看看榜单/任务"时使用。
---

# GitHub 热度周榜操作技能

你可以使用 `github-hot-cli` 管理并分析 GitHub 热度周榜（项目位于 `~/code/AI/github-hot`，已全局安装）。

## 可用命令

```bash
# 采集一次数据（每次采集登记为一个任务；--no-ai 在未配置 AI Key 时使用）
github-hot-cli collect [--no-ai] [--languages python,go] [--since daily|weekly|monthly] \
  [--ai-only] [--with-search] [--api-top N]

# 输出榜单；--json 返回 {"report": {items, meta}, "tasks": [...]}
github-hot-cli report [--limit N] [--ai-only] [--json]

# 查看 / 删除任务历史
github-hot-cli tasks [--delete ID]

# 启动 Web 仪表盘
github-hot-cli serve [--port 8787]
```

## 数据字段

- `items[].full_name` / `stars` / `weekly_stars` / `weekly_growth`（百分比数值）
- `items[].language` / `is_ai` / `ai_summary`（中文一句话简介）/ `url`
- `tasks[].summary`（该次采集的 AI 中文总结）/ `repo_count` / `ai_count`

## 常用做法

1. 用户问数据相关问题且数据可能过旧时：先 `collect`（带进度输出，等待完成）
2. 用 `report --json --limit N` 获取结构化结果，解析后用中文回答
3. 用户要历史总结时：读 `tasks[0].summary`（最新）或遍历 `tasks`
4. stdout 只有纯 JSON（进度与提示走 stderr），可直接管道给解析器

## 回答示例

用户："本周涨星最快的 3 个项目是什么？"
→ `github-hot-cli report --json --limit 3` → 按 `weekly_stars` 取前三，用 `ai_summary` 说明每个项目是做什么的。
