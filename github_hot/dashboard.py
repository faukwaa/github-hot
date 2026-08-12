from __future__ import annotations

import json
from typing import Any


def render_dashboard(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return DASHBOARD_HTML.replace("__PAGE_JSON__", encoded)


# 应用式双栏布局（推翻上下堆叠）：
# 左栏 = 采集任务（sticky 独立滚动，任务再多也不挤压榜单，可展开全部）
# 右栏 = 任务榜单（默认选中左栏第一个任务，点击任务切换历史快照）
# 延续 DESIGN.md：暖纸画布、近黑 ink、单一 Notion Blue、发丝线。
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitHub 热度周榜</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23141413'/%3E%3Cpolyline points='6,23 11,18 16,20 21,13' fill='none' stroke='%23cc785c' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3Cpath d='M22 4 L23.2 8.8 L28 10 L23.2 11.2 L22 16 L20.8 11.2 L16 10 L20.8 8.8 Z' fill='%23faf9f5'/%3E%3C/svg%3E">
<style>
:root{
  --canvas:#f6f5f4;
  --surface:#ffffff;
  --ink:#1a1a1a;
  --ink-2:#31302e;
  --ink-3:#615d59;
  --ink-4:#a39e98;
  --hairline:#e6e6e6;
  --primary:#0075de;
  --primary-active:#005bab;
  --green:#1aae39;
  --orange:#dd5b00;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
}
*{box-sizing:border-box}
body{
  margin:0;
  background:var(--canvas);
  color:var(--ink);
  font:15px/1.55 var(--font);
  -webkit-font-smoothing:antialiased;
}
a{color:inherit;text-decoration:none}
a:hover{color:var(--primary)}
.container{max-width:1180px;margin:0 auto;padding:0 24px}

/* Nav */
.nav{
  position:sticky;top:0;z-index:50;
  background:rgba(255,255,255,.92);
  backdrop-filter:blur(12px);
  border-bottom:1px solid var(--hairline);
}
.nav-inner{display:flex;align-items:center;gap:16px;height:60px}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:14.5px;letter-spacing:-.2px}
.brand-mark{
  width:24px;height:24px;flex:none;display:grid;place-items:center;
}
.brand-mark svg{width:22px;height:22px}
.nav-spacer{flex:1}
.nav-meta{font-size:12px;color:var(--ink-4);font-variant-numeric:tabular-nums}
.btn{
  display:inline-flex;align-items:center;gap:8px;
  border:1px solid transparent;cursor:pointer;
  font:500 14px/1.5 var(--font);
  border-radius:9999px;padding:8px 18px;
  background:var(--primary);color:#fff;
  transition:background .15s,transform .12s;
}
.btn:hover{background:var(--primary-active)}
.btn:active{transform:scale(.97)}
.btn:disabled{opacity:.6;cursor:wait}

/* App shell：左任务栏 + 右榜单 */
.app{
  display:grid;
  grid-template-columns:300px minmax(0,1fr);
  gap:24px;
  align-items:start;
  padding:24px 24px 8px;
  max-width:1180px;margin:0 auto;
}

/* ── 左栏：采集任务（sticky + 独立滚动，任务多了不挤占榜单） ── */
.task-panel{
  position:sticky;top:84px;
  max-height:calc(100vh - 108px);
  display:flex;flex-direction:column;
  background:var(--surface);
  border:1px solid var(--hairline);
  border-radius:12px;
  padding:18px 16px 14px;
}
.tp-head{display:flex;align-items:baseline;gap:8px;padding:0 4px 12px;border-bottom:1px solid var(--hairline)}
.tp-title{font-size:15px;font-weight:700;letter-spacing:-.25px;margin:0}
.tp-count{font-size:11.5px;color:var(--ink-4);font-variant-numeric:tabular-nums}
.tp-scroll{overflow-y:auto;flex:1;min-height:0;margin:0 -2px;padding:10px 2px 2px}
.tp-scroll::-webkit-scrollbar{width:5px}
.tp-scroll::-webkit-scrollbar-thumb{background:#dedcd8;border-radius:99px}
.tp-more{
  margin-top:10px;padding:9px 0 2px;border:0;border-top:1px solid var(--hairline);
  background:none;font:600 12.5px var(--font);color:var(--primary);cursor:pointer;
  transition:color .15s;
}
.tp-more:hover{color:var(--primary-active)}
.tp-more:disabled{color:var(--ink-4);cursor:default}

.task-card{
  border:1px solid transparent;border-radius:10px;
  padding:11px 12px;margin-bottom:8px;cursor:pointer;
  transition:background .15s,border-color .15s;
}
.task-card:hover{background:#faf9f8}
.task-card.open{background:var(--canvas);border-color:var(--hairline)}
.task-card.open .tc-no{color:var(--primary)}
.tc-head{display:flex;align-items:center;gap:8px}
.tc-dot{width:7px;height:7px;border-radius:50%;background:var(--green);flex:none}
.tc-dot.error{background:var(--orange)}
.tc-no{font-size:13px;font-weight:700;letter-spacing:-.1px}
.tc-range{margin-left:auto;font-size:11px;color:var(--ink-4);font-variant-numeric:tabular-nums;white-space:nowrap}
.tc-summary{
  margin:7px 0 0;font-size:12.5px;line-height:1.5;color:var(--ink-3);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}
.task-card.open .tc-summary{-webkit-line-clamp:unset}
.tc-detail{display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--hairline);font-size:12px;color:var(--ink-4)}
.task-card.open .tc-detail{display:block}
.tc-error{color:var(--orange);font-size:12px;margin-top:6px}
.task-empty{padding:26px 10px;text-align:center;color:var(--ink-3);font-size:13px}

/* ── 右栏：榜单 ── */
.panel{
  background:var(--surface);border:1px solid var(--hairline);
  border-radius:12px;padding:20px 22px;
}
.panel-head{display:flex;align-items:baseline;justify-content:space-between;gap:14px;margin-bottom:14px}
.panel-title{margin:0;font-size:17px;font-weight:700;letter-spacing:-.3px}
.panel-note{font-size:12px;color:var(--ink-4)}
.toolbar{display:flex;gap:10px;align-items:center;margin-bottom:14px}
.search-box{
  flex:1;min-width:180px;display:flex;align-items:center;gap:8px;
  border:1px solid #dddddd;background:var(--surface);
  border-radius:5px;padding:0 11px;color:var(--ink-4);
  transition:border-color .15s,box-shadow .15s;
}
.search-box:focus-within{border-color:var(--primary);box-shadow:0 0 0 3px rgba(0,117,222,.12)}
.search-box input{border:0;outline:0;background:transparent;width:100%;padding:8px 0;font:inherit;font-size:13.5px;color:var(--ink)}
.search-box input::placeholder{color:var(--ink-4)}
.ai-toggle{
  display:inline-flex;align-items:center;gap:7px;
  border:1px solid #dddddd;background:var(--surface);border-radius:9999px;
  padding:6px 13px;cursor:pointer;font-size:13px;color:var(--ink);user-select:none;
}
.ai-toggle input{accent-color:var(--primary);margin:0}
select{
  border:1px solid #dddddd;background:var(--surface);border-radius:5px;
  padding:8px 10px;font:inherit;font-size:13.5px;color:var(--ink);
  transition:border-color .15s,box-shadow .15s;
}
select:focus{outline:0;border-color:var(--primary);box-shadow:0 0 0 3px rgba(0,117,222,.12)}
.count{color:var(--ink-4);font-size:12px;white-space:nowrap}

/* ── 仓库详情（README，GitHub 风格渲染） ── */
.back-btn{
  display:inline-flex;align-items:center;gap:6px;
  border:1px solid var(--hairline);background:var(--surface);color:var(--ink);
  border-radius:8px;padding:6px 13px;cursor:pointer;
  font:500 13px var(--font);
  transition:border-color .15s,background .15s;
}
.back-btn:hover{border-color:#cfcfcf;background:#fbfbfb}
.repo-tabs{display:flex;gap:4px;border-bottom:1px solid var(--hairline);margin-bottom:18px}
.tab{
  border:0;background:none;cursor:pointer;
  padding:8px 14px;font:500 13.5px var(--font);color:var(--ink-3);
  border-bottom:2px solid transparent;margin-bottom:-1px;
  transition:color .15s,border-color .15s;
}
.tab:hover{color:var(--ink)}
.tab.active{color:var(--primary);border-bottom-color:var(--primary)}
.readme{
  font-size:15px;line-height:1.65;color:var(--ink);
  overflow-wrap:break-word;
}
.readme h1,.readme h2,.readme h3,.readme h4,.readme h5,.readme h6{
  font-weight:600;letter-spacing:-.2px;color:var(--ink);
  margin:22px 0 12px;line-height:1.3;
}
.readme h1{font-size:1.8em;padding-bottom:8px;border-bottom:1px solid var(--hairline)}
.readme h2{font-size:1.4em;padding-bottom:6px;border-bottom:1px solid var(--hairline)}
.readme h3{font-size:1.15em}
.readme h4{font-size:1em}
.readme p{margin:0 0 14px}
.readme a{color:var(--primary)}
.readme ul,.readme ol{margin:0 0 14px;padding-left:26px}
.readme li{margin:4px 0}
.readme li input[type="checkbox"]{margin-right:6px;vertical-align:-1px}
.readme code{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:.86em;background:#f0efed;border-radius:5px;padding:2px 5px;
}
.readme pre{
  background:#f6f8fa;border:1px solid var(--hairline);border-radius:6px;
  padding:14px 16px;overflow-x:auto;margin:0 0 14px;line-height:1.55;
}
.readme pre code{background:none;padding:0;font-size:12.5px}
.readme blockquote{
  margin:0 0 14px;padding:2px 16px;color:var(--ink-3);
  border-left:4px solid #d0d7de;
}
.readme blockquote p{margin:6px 0}
.readme hr{border:0;border-top:1px solid var(--hairline);margin:22px 0}
.readme img{max-width:100%;border-radius:6px}
.readme table{border-collapse:collapse;margin:0 0 14px;font-size:13.5px;display:block;overflow-x:auto;max-width:100%}
.readme th,.readme td{border:1px solid var(--hairline);padding:6px 13px;text-align:left}
.readme th{background:var(--canvas);font-weight:600}
.readme-empty{color:var(--ink-4);padding:20px 0}
.repo-error{color:var(--orange);font-size:13.5px;padding:14px 0}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{
  font-size:11px;text-transform:uppercase;letter-spacing:.1px;font-weight:600;
  color:var(--ink-4);text-align:left;padding:7px 10px;
  border-bottom:1px solid var(--hairline);white-space:nowrap;
}
td{padding:12px 10px;border-bottom:1px solid var(--hairline);vertical-align:top}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover td{background:#faf9f8}
tbody tr{cursor:pointer}
.rank{color:var(--ink-4);font-weight:600;width:36px;font-variant-numeric:tabular-nums}
.repo-name{font-weight:650;display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.ai-badge{
  background:var(--surface);color:var(--primary);
  border:1px solid #d8e8f8;border-radius:9999px;
  padding:0 7px;font-size:10px;font-weight:650;letter-spacing:.1px;
}
.repo-desc{color:var(--ink-3);font-size:12.5px;line-height:1.5;margin-top:4px;max-width:420px}
.lang{white-space:nowrap;color:var(--ink-2);font-size:13px}
.lang-dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px;vertical-align:1px}
.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
.weekly{font-weight:600}
.growth{font-weight:600;color:#c64545}
.growth.flat{color:var(--ink-4)}

/* 移动端列表卡片 */
.repo-list{display:none}
.repo-row{padding:15px 2px;border-bottom:1px solid var(--hairline);cursor:pointer}
.repo-row:last-child{border-bottom:0}
.rr-top{display:flex;align-items:baseline;gap:9px}
.rr-rank{color:var(--ink-4);font-weight:600;font-size:12.5px;font-variant-numeric:tabular-nums}
.rr-name{font-weight:650;font-size:14.5px;letter-spacing:-.1px}
.rr-blurb{color:var(--ink-3);font-size:12.5px;line-height:1.55;margin-top:5px}
.rr-blurb::before{
  content:"";display:inline-block;width:5px;height:5px;border-radius:50%;
  background:var(--green);margin-right:7px;vertical-align:2px;
}
.rr-meta{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;color:var(--ink-4);font-size:12px;font-variant-numeric:tabular-nums}
.rr-meta b{color:var(--ink-2);font-weight:600}
.rr-meta .rr-growth{color:#c64545}
@media (max-width:640px){
  .repo-list{display:block}
  #repoTable{display:none}
}

/* Skeleton */
.sk{height:11px;border-radius:5px;background:linear-gradient(90deg,#f0efed 25%,#f8f7f5 50%,#f0efed 75%);background-size:200% 100%;animation:shimmer 1.4s infinite}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
@media (prefers-reduced-motion:reduce){.sk{animation:none}}

/* Banner / empty */
.banner{
  display:none;margin-bottom:16px;padding:10px 14px;border-radius:8px;
  background:#fff;border:1px solid var(--hairline);color:var(--ink-2);
  font-size:13px;border-left:3px solid var(--primary);
}
.banner.error{border-left-color:var(--orange)}
.empty{padding:36px 16px;text-align:center;color:var(--ink-3);font-size:13.5px}

/* 回到顶部 */
.back-top{
  position:fixed;right:28px;bottom:28px;z-index:60;
  width:42px;height:42px;border-radius:50%;
  background:var(--surface);border:1px solid var(--hairline);color:var(--ink-2);
  cursor:pointer;display:grid;place-items:center;
  box-shadow:0 2px 12px rgba(0,0,0,.08);
  transition:opacity .2s,transform .2s,border-color .2s,color .2s;
}
.back-top:hover{border-color:#cfcfcf;color:var(--primary)}
.back-top:active{transform:scale(.95)}
.back-top[hidden]{display:none}
@media (max-width:640px){
  .back-top{right:16px;bottom:16px;width:40px;height:40px}
}

/* ── 响应式：<1024px 单列，任务栏限高滚动，不挤占榜单 ── */
@media (max-width:1023px){
  .app{grid-template-columns:minmax(0,1fr);gap:18px;padding-top:18px}
  .task-panel{position:static;max-height:none}
  .tp-scroll{max-height:34vh}
  .nav-meta{display:none}
}
@media (max-width:640px){
  .container{padding:0 16px}
  .app{padding:16px 16px 4px}
  .panel{padding:16px}
  .toolbar .count{display:none}
  .tp-scroll{max-height:38vh}
}
</style>
</head>
<body>

<nav class="nav">
  <div class="container nav-inner">
    <div class="brand">
      <span class="brand-mark"><svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#141413"/><polyline points="6,23 11,18 16,20 21,13" fill="none" stroke="#cc785c" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 4 L23.2 8.8 L28 10 L23.2 11.2 L22 16 L20.8 11.2 L16 10 L20.8 8.8 Z" fill="#faf9f5"/></svg></span>
      GitHub 热度周榜
    </div>
    <div class="nav-spacer"></div>
    <span class="nav-meta" id="navUpdated">尚无数据</span>
    <button class="btn" id="refreshBtn" type="button">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 2v6h-6"/><path d="M21 8a9 9 0 1 0-2.1 5.9"/></svg>
      <span class="btn-label">立即采集</span>
    </button>
  </div>
</nav>

<div class="container">
  <div class="banner" id="banner"></div>
</div>

<div class="app">

  <!-- 左栏：采集任务（独立滚动，任务多了也不影响榜单） -->
  <aside class="task-panel" aria-label="采集任务">
    <div class="tp-head">
      <h2 class="tp-title">采集任务</h2>
      <span class="tp-count" id="taskCount"></span>
    </div>
    <div class="tp-scroll" id="taskList"></div>
    <button class="tp-more" id="taskMore" type="button" hidden>展开全部</button>
  </aside>

  <!-- 右栏：任务榜单（默认选中第一个任务，点击左栏任务切换） -->
  <main class="panel" id="rankingPanel">
    <div class="panel-head">
      <div>
        <h2 class="panel-title" id="mainTitle">任务榜单</h2>
        <div class="panel-note" id="tableNote"></div>
      </div>
    </div>
    <div class="toolbar">
      <div class="search-box">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <input id="searchInput" type="search" placeholder="搜索项目或简介" aria-label="搜索项目">
      </div>
      <label class="ai-toggle">
        <input type="checkbox" id="aiOnly">
        <span>只看 AI</span>
      </label>
      <select id="langSelect" aria-label="按语言筛选">
        <option value="">全部语言</option>
      </select>
      <span class="count" id="countLabel"></span>
    </div>
    <div class="table-wrap">
      <table id="repoTable">
        <thead>
          <tr>
            <th>#</th>
            <th>项目</th>
            <th>语言</th>
            <th class="num">本周 Star</th>
            <th class="num">总 Star</th>
            <th class="num">周增长</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
      <!-- 移动端：列表卡片（替代横向滚动表格） -->
      <div class="repo-list" id="repoList"></div>
      <div class="empty" id="emptyState" style="display:none">当前筛选条件下没有项目</div>
    </div>
  </main>

  <!-- 右栏：仓库详情（README 原文/中文版） -->
  <main class="panel" id="repoPanel" hidden>
    <div class="panel-head">
      <div>
        <h2 class="panel-title" id="repoTitle"></h2>
        <div class="panel-note" id="repoNote"></div>
      </div>
      <button class="back-btn" id="repoBackBtn" type="button">返回榜单</button>
    </div>
    <div class="repo-tabs" id="repoTabs" hidden>
      <button class="tab active" type="button" data-tab="raw">原文</button>
      <button class="tab" type="button" data-tab="zh">中文版</button>
    </div>
    <div class="readme" id="readmeContent"></div>
  </main>

</div>

<button class="back-top" id="backTopBtn" type="button" hidden aria-label="回到顶部">
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m18 15-6-6-6 6"/></svg>
</button>

<script src="/static/marked.min.js"></script>
<script>
const PAGE = __PAGE_JSON__;
const LANG_COLORS = {
  Python:"#3776ab", TypeScript:"#3178c6", JavaScript:"#c2a53a", Go:"#00a2b8",
  Rust:"#d97706", "C++":"#db4d69", "Jupyter Notebook":"#da5b0b", C:"#5a6b7b",
  Shell:"#4e9a51", Java:"#c1440e", Swift:"#e05e2f", Kotlin:"#a95c9a",
  Dart:"#0175c2", PHP:"#7a4fd3", Ruby:"#c4283c", Unknown:"#8b93a3"
};
const fmt = new Intl.NumberFormat("en-US");
// Star 数格式化：>=1000 用 k 为单位（8,182 -> 8.2k）
function fmtK(value){
  if(value == null || value === "") return "-";
  const n = Number(value);
  if(!isFinite(n)) return String(value);
  if(n < 1000) return String(n);
  return (Math.round((n / 1000) * 10) / 10).toString() + "k";
}
const state = { query:"", lang:"", aiOnly:false, showAllTasks:false, view:{type:"task", taskId:null} };
const openTasks = new Set(); // 当前选中的任务 id（单选）
const TASK_CACHE = {}; // 任务榜单缓存：taskId -> {items, meta}
const RANGE_DAYS = {daily:1, weekly:7, monthly:30}; // since -> 增长天数

function esc(value){
  return String(value == null ? "" : value).replace(/[&<>"']/g, (c) => (
    {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]
  ));
}
function langColor(lang){
  return LANG_COLORS[lang || "Unknown"] || LANG_COLORS.Unknown;
}
function formatWhen(iso){
  if(!iso) return "";
  const d = new Date(iso);
  if(isNaN(d.getTime())) return iso;
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
function visibleItems(){
  const q = state.query.trim().toLowerCase();
  const data = currentData();
  let items = data.items.filter((item) => {
    const matchLang = !state.lang || item.language === state.lang;
    const matchAi = !state.aiOnly || !!item.is_ai;
    const haystack = `${item.full_name} ${item.description || ""} ${item.ai_summary || ""}`.toLowerCase();
    return matchLang && matchAi && (!q || haystack.includes(q));
  });
  return items.sort((a,b) => (b.weekly_stars||0) - (a.weekly_stars||0));
}

/* 语言下拉选项跟随当前视图数据重建，保持选中值 */
function renderLangOptions(){
  const langs = [...new Set(currentData().items.map((i) => i.language || "Unknown"))].sort();
  const select = document.getElementById("langSelect");
  const current = state.lang;
  select.innerHTML = '<option value="">全部语言</option>' + langs.map((l) => `<option value="${esc(l)}">${esc(l)}</option>`).join("");
  if(current && !langs.includes(current)) state.lang = "";
  select.value = state.lang;
}

/* 当前榜单数据源：最新采集 或 某次任务的历史快照（详情页沿用来源任务数据） */
function currentData(){
  if(state.view.type === "repo" && state.view.from && state.view.from.type === "task"){
    return TASK_CACHE[state.view.from.taskId] || PAGE.data;
  }
  if(state.view.type === "task"){
    return TASK_CACHE[state.view.taskId] || {items:[], meta:{}};
  }
  return PAGE.data;
}

/* ── 任务栏 ── */
function renderTasks(){
  const list = document.getElementById("taskList");
  const tasks = PAGE.tasks || [];
  document.getElementById("taskCount").textContent = tasks.length ? `${tasks.length} 次` : "";
  const moreBtn = document.getElementById("taskMore");
  if(!tasks.length){
    list.innerHTML = '<div class="task-empty">还没有采集任务。点击右上角「立即采集」，每次拉取会登记为一个任务并生成 AI 总结。</div>';
    moreBtn.hidden = true;
    return;
  }
  // 任务多了默认折叠：桌面 6 条 / 移动 3 条，其余点「展开全部」
  const isMobile = window.matchMedia("(max-width: 640px)").matches;
  const previewLimit = state.showAllTasks ? tasks.length : (isMobile ? 3 : 6);
  const visible = tasks.slice(0, previewLimit);
  list.innerHTML = visible.map((task) => {
    const dot = task.status === "done" ? "tc-dot" : "tc-dot error";
    const active = state.view.type === "task" && state.view.taskId === task.id;
    const activeCls = active ? " open" : "";
    const summary = task.summary
      ? `<p class="tc-summary">${esc(task.summary)}</p>`
      : '<p class="tc-summary">该任务未生成 AI 总结（未配置 AI_API_KEY / DEEPSEEK_API_KEY）。</p>';
    const error = task.error ? `<p class="tc-error">${esc(task.error)}</p>` : '';
    const detail = `<div class="tc-detail">采集于 ${esc(formatWhen(task.collected_at))} · 收录 ${task.repo_count} 个 · AI ${task.ai_count} 个${error}</div>`;
    return `<div class="task-card${activeCls}" data-id="${task.id}">
      <div class="tc-head">
        <span class="${dot}"></span>
        <span class="tc-no">任务 #${task.id}</span>
        <span class="tc-range">${esc(taskRange(task))}</span>
      </div>
      ${summary}${detail}
    </div>`;
  }).join("");
  moreBtn.hidden = tasks.length <= previewLimit;
  if(!moreBtn.hidden){
    moreBtn.textContent = state.showAllTasks ? "收起" : `展开全部（${tasks.length - previewLimit}）`;
  } else if(state.showAllTasks && tasks.length > 0){
    // 全部展开后仍提供「收起」入口
    moreBtn.hidden = false;
    moreBtn.textContent = "收起";
  }
}

/* 点击任务：单选选中并切换右侧为该任务的榜单（再次点击保持选中） */
async function openTask(taskId){
  if(state.view.type === "task" && state.view.taskId === taskId && TASK_CACHE[taskId]){
    // 已选中：仅确保展开，不取消
    openTasks.add(taskId);
    renderTasks();
    return;
  }
  openTasks.add(taskId);
  renderTasks();
  if(!TASK_CACHE[taskId]){
    showTableSkeleton(true);
    try{
      const resp = await fetch(`/api/data?task=${taskId}`);
      const payload = await resp.json();
      if(payload.error || !payload.data){
        showBanner(payload.error || "加载任务数据失败", true);
        showTableSkeleton(false);
        return;
      }
      TASK_CACHE[taskId] = payload.data;
    }catch(err){
      showBanner("加载任务数据失败，请重试", true);
      showTableSkeleton(false);
      return;
    }
  }
  state.view = {type:"task", taskId};
  renderTasks(); // 左栏高亮同步到新选中的任务
  renderMainHeader();
  showTableSkeleton(false);
}

/* 任务增长区间：采集日往前推 N 天（daily 1 / weekly 7 / monthly 30） */
function taskRange(task){
  const days = RANGE_DAYS[task.since || "weekly"] || 7;
  const end = new Date(task.collected_at);
  const start = new Date(end.getTime() - days * 86400000);
  const p = (n) => String(n).padStart(2, "0");
  return `${p(start.getMonth()+1)}/${p(start.getDate())}-${p(end.getMonth()+1)}/${p(end.getDate())}`;
}

function renderMainHeader(){
  const title = document.getElementById("mainTitle");
  const note = document.getElementById("tableNote");
  const task = (PAGE.tasks || []).find((t) => t.id === state.view.taskId);
  const data = TASK_CACHE[state.view.taskId] || {items:[], meta:{}};
  title.textContent = task ? `任务 #${task.id} · 榜单` : "任务榜单";
  note.textContent = data.meta && data.meta.collected_at
    ? `采集于 ${formatWhen(data.meta.collected_at)} · 收录 ${data.items.length} 个`
    : "该任务没有保存仓库快照（历史数据）";
}

/* ── 仓库详情：README 原文 / 中文版 ── */
let REPO_DATA = null; // 当前详情数据
let REPO_TAB = "raw";
let SAVED_SCROLL = 0; // 进入详情前的滚动位置，返回时恢复

/* HTML 风格 README 转 Markdown（仅离线 fallback 使用） */
function htmlToMd(md){
  if(!/<[a-z][\s\S]*>/i.test(md)) return md;
  let t = md;
  t = t.replace(/<h([1-6])[^>]*>([\s\S]*?)<\/h\1>/gi, (m, lv, inner) =>
    "#".repeat(Number(lv)) + " " + inner.trim() + "\n\n");
  t = t.replace(/<img[^>]*src=["']([^"']+)["'][^>]*alt=["']([^"']*)["'][^>]*\/?>/gi, "![$2]($1)");
  t = t.replace(/<img[^>]*alt=["']([^"']*)["'][^>]*src=["']([^"']+)["'][^>]*\/?>/gi, "![$1]($2)");
  t = t.replace(/<a[^>]*href=["'](https?:[^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi, "[$2]($1)");
  t = t.replace(/<(pre|code)[^>]*>([\s\S]*?)<\/\1>/gi, (m, tag, code) =>
    "```\n" + code.replace(/<[^>]+>/g, "") + "\n```");
  t = t.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, "- $1");
  t = t.replace(/<\/?(?:ul|ol)[^>]*>/gi, "\n");
  t = t.replace(/<br\s*\/?>/gi, "\n");
  t = t.replace(/<[^>]+>/g, "");
  t = t.replace(/\n{3,}/g, "\n\n");
  return t.trim();
}

/* 渲染结果安全过滤：移除脚本/内联事件，相对图片拼接 GitHub raw 地址 */
function sanitizeHtml(html, imgBase){
  const doc = new DOMParser().parseFromString(html, "text/html");
  doc.querySelectorAll("script, iframe, object, embed, style, link, meta").forEach((el) => el.remove());
  doc.querySelectorAll("*").forEach((el) => {
    [...el.attributes].forEach((attr) => {
      if(/^on/i.test(attr.name)) el.removeAttribute(attr.name);
    });
    if(el.tagName === "A" && /^\s*javascript:/i.test(el.getAttribute("href") || "")){
      el.removeAttribute("href");
    }
    if(el.tagName === "IMG"){
      const src = el.getAttribute("src") || "";
      if(src && !/^https?:|^data:|^#/.test(src)) el.setAttribute("src", `${imgBase}/${src}`);
    }
  });
  return doc.body.innerHTML;
}

/* 主渲染：marked（与 GitHub README 同源引擎）+ 安全过滤；离线时降级为简易渲染 */
function renderMarkdown(md, imgBase){
  if(!md || !md.trim()) return '<p class="readme-empty">（无内容）</p>';
  if(window.marked && window.marked.parse){
    try{
      const renderer = new marked.Renderer();
      renderer.image = (href, title, text) => {
        const url = /^https?:|^data:|^#/.test(href) ? href : `${imgBase}/${href}`;
        return `<img src="${url}" alt="${text || ""}" loading="lazy">`;
      };
      const html = marked.parse(md, { gfm:true, breaks:true, renderer });
      return sanitizeHtml(html, imgBase);
    }catch(err){
      const html = marked.parse(md, { gfm:true, breaks:true });
      return sanitizeHtml(html, imgBase);
    }
  }
  return renderMarkdownSimple(md, imgBase);
}

/* 离线 fallback：极简 Markdown 渲染 */
function renderMarkdownSimple(md, imgBase){
  if(!md || !md.trim()) return '<p class="readme-empty">（无内容）</p>';
  md = htmlToMd(md);
  const lines = esc(md).split("\n");
  const inline = (s) => s
    .replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (m, alt, src) => {
      const url = /^https?:/.test(src) ? src : `${imgBase}/${src}`;
      return `<img alt="${alt}" src="${url}" loading="lazy">`;
    })
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  let html = "";
  let inCode = false, codeBuf = [], inList = null;
  const closeList = () => { if(inList){ html += inList === "ul" ? "</ul>" : "</ol>"; inList = null; } };
  for(const line of lines){
    const t = line.trim();
    if(t.startsWith("```")){
      if(!inCode){ inCode = true; codeBuf = []; }
      else { html += `<pre><code>${codeBuf.join("\n")}</code></pre>`; inCode = false; }
      continue;
    }
    if(inCode){ codeBuf.push(line); continue; }
    if(/^#{1,4}\s/.test(t)){
      closeList();
      const level = t.match(/^#+/)[0].length;
      html += `<h${level}>${inline(t.replace(/^#+\s*/, ""))}</h${level}>`;
    } else if(/^-{3,}$/.test(t)){
      closeList();
      html += "<hr>";
    } else if(/^&gt;\s/.test(t)){
      closeList();
      html += `<blockquote>${inline(t.replace(/^&gt;\s*/, ""))}</blockquote>`;
    } else if(/^[-*]\s/.test(t)){
      if(inList !== "ul"){ closeList(); html += "<ul>"; inList = "ul"; }
      html += `<li>${inline(t.replace(/^[-*]\s*/, ""))}</li>`;
    } else if(/^\d+\.\s/.test(t)){
      if(inList !== "ol"){ closeList(); html += "<ol>"; inList = "ol"; }
      html += `<li>${inline(t.replace(/^\d+\.\s*/, ""))}</li>`;
    } else if(t.startsWith("|")){
      closeList();
      html += `<p class="md-table-row">${inline(t.replace(/^\||\|$/g, "").replace(/\|/g, " · "))}</p>`;
    } else {
      closeList();
      if(t) html += `<p>${inline(t)}</p>`;
    }
  }
  if(inCode) html += `<pre><code>${codeBuf.join("\n")}</code></pre>`;
  closeList();
  return html;
}

async function openRepo(fullName){
  SAVED_SCROLL = window.scrollY; // 记住进入详情前的滚动位置
  REPO_TAB = "raw";
  state.view = { type:"repo", repoName:fullName, from:{ type:"task", taskId: state.view.taskId } };
  document.getElementById("rankingPanel").hidden = true;
  const panel = document.getElementById("repoPanel");
  panel.hidden = false;
  document.getElementById("repoTitle").textContent = fullName;
  document.getElementById("repoNote").textContent = "";
  document.getElementById("repoTabs").hidden = true;
  document.getElementById("readmeContent").innerHTML = Array.from({length:8}, () => `
    <span class="sk" style="display:block;width:90%;margin-bottom:10px"></span>`).join("");
  try{
    const resp = await fetch(`/api/repo?name=${encodeURIComponent(fullName)}`);
    const payload = await resp.json();
    if(payload.error || !payload.readme_raw){
      document.getElementById("readmeContent").innerHTML = `<p class="repo-error">${esc(payload.error || "README 加载失败")}</p>`;
      return;
    }
    REPO_DATA = payload;
    renderRepo();
  }catch(err){
    document.getElementById("readmeContent").innerHTML = '<p class="repo-error">加载失败，请重试</p>';
  }
}

function renderRepo(){
  if(!REPO_DATA) return;
  const item = currentData().items.find((i) => i.full_name === REPO_DATA.full_name) || {};
  const bits = [];
  if(item.language) bits.push(item.language);
  if(item.stars) bits.push(`${fmtK(item.stars)} Stars`);
  if(item.weekly_stars) bits.push(`本周 +${fmtK(item.weekly_stars)}`);
  document.getElementById("repoNote").textContent = bits.join(" · ");
  const tabs = document.getElementById("repoTabs");
  if(REPO_DATA.is_zh){
    tabs.hidden = true;
  } else {
    tabs.hidden = false;
    tabs.querySelectorAll(".tab").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === REPO_TAB);
      btn.disabled = btn.dataset.tab === "zh" && REPO_DATA.readme_translated === null && !REPO_DATA.translating;
    });
  }
  const imgBase = `https://raw.githubusercontent.com/${REPO_DATA.full_name}/HEAD`;
  if(REPO_TAB === "raw" || REPO_DATA.is_zh){
    document.getElementById("readmeContent").innerHTML = renderMarkdown(REPO_DATA.readme_raw, imgBase);
  } else if(REPO_DATA.readme_translated){
    document.getElementById("readmeContent").innerHTML = renderMarkdown(REPO_DATA.readme_translated, imgBase);
  } else {
    document.getElementById("readmeContent").innerHTML = '<p class="readme-empty">正在翻译中，请稍候...</p>';
    ensureTranslation();
  }
}

async function ensureTranslation(){
  if(!REPO_DATA || REPO_DATA.is_zh || REPO_DATA.readme_translated || REPO_DATA.translating) return;
  REPO_DATA.translating = true;
  renderRepo();
  try{
    const resp = await fetch(`/api/repo?name=${encodeURIComponent(REPO_DATA.full_name)}&translate=1`);
    const payload = await resp.json();
    REPO_DATA = payload;
    REPO_DATA.translating = false;
    if(payload.readme_translated){
      REPO_TAB = "zh";
      renderRepo();
    } else {
      document.getElementById("readmeContent").innerHTML =
        `<p class="repo-error">翻译失败：${esc(payload.translate_error || "未知错误")}</p>`;
    }
  }catch(err){
    document.getElementById("readmeContent").innerHTML = '<p class="repo-error">翻译请求失败，请重试</p>';
  }
}

function backToRanking(){
  const from = state.view.from || { type:"task", taskId:null };
  state.view = from;
  document.getElementById("repoPanel").hidden = true;
  document.getElementById("rankingPanel").hidden = false;
  renderTasks();
  renderTable();
  renderMainHeader();
  // 渲染完成后恢复进入详情前的滚动位置
  requestAnimationFrame(() => window.scrollTo(0, SAVED_SCROLL));
}

/* ── 榜单 ── */
function renderTable(){
  renderLangOptions();
  const items = visibleItems();
  const tbody = document.getElementById("tableBody");
  const empty = document.getElementById("emptyState");
  const isMobile = window.matchMedia("(max-width: 640px)").matches;
  if(isMobile){
    const list = document.getElementById("repoList");
    list.innerHTML = items.map((item) => {
      const growth = item.weekly_growth == null
        ? '<span>-</span>'
        : `<b class="rr-growth">+${item.weekly_growth.toFixed(1)}%</b>`;
      const aiBadge = item.is_ai ? '<span class="ai-badge">AI</span>' : '';
      const blurb = item.ai_summary || item.description;
      const lang = `<span><span class="lang-dot" style="background:${langColor(item.language)}"></span>${esc(item.language || "Unknown")}</span>`;
      return `<div class="repo-row" data-name="${esc(item.full_name)}">
        <div class="rr-top">
          <span class="rr-rank">#${item.rank}</span>
          <a class="rr-name" href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.full_name)}</a>${aiBadge}
        </div>
        ${blurb ? `<div class="rr-blurb">${esc(blurb)}</div>` : ''}
        <div class="rr-meta">${lang}<span>本周 <b>+${fmtK(item.weekly_stars)}</b></span><span>总 <b>${fmtK(item.stars)}</b></span><span>增长 ${growth}</span></div>
      </div>`;
    }).join("");
  } else {
    tbody.innerHTML = items.map((item) => {
      const growth = item.weekly_growth == null
        ? '<span class="num">-</span>'
        : `<span class="num growth">+${item.weekly_growth.toFixed(1)}%</span>`;
      const lang = `<span class="lang"><span class="lang-dot" style="background:${langColor(item.language)}"></span>${esc(item.language || "Unknown")}</span>`;
      const aiBadge = item.is_ai ? '<span class="ai-badge">AI</span>' : '';
      const blurb = item.ai_summary || item.description;
      return `<tr data-name="${esc(item.full_name)}">
        <td class="rank">${item.rank}</td>
        <td>
          <div class="repo-name"><a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.full_name)}</a>${aiBadge}</div>
          <div class="repo-desc">${esc(blurb || "暂无简介")}</div>
        </td>
        <td>${lang}</td>
        <td class="num weekly">+${fmtK(item.weekly_stars)}</td>
        <td class="num">${fmtK(item.stars)}</td>
        <td>${growth}</td>
      </tr>`;
    }).join("");
  }
  empty.style.display = items.length ? "none" : "block";
  empty.textContent = state.view.type === "task" && !currentData().items.length
    ? "该任务没有保存仓库快照（历史数据）"
    : "当前筛选条件下没有项目";
  document.getElementById("countLabel").textContent = items.length
    ? `${fmt.format(items.length)} / ${fmt.format(currentData().items.length)}`
    : "";
}

function showBanner(message, isError){
  const banner = document.getElementById("banner");
  if(!message){
    banner.style.display = "none";
    return;
  }
  banner.textContent = message;
  banner.className = "banner" + (isError ? " error" : "");
  banner.style.display = "block";
}

function renderAll(){
  // 默认选中第一个任务（最新一次采集），其快照即页面首屏数据
  const tasks = PAGE.tasks || [];
  if(tasks.length && !state.view.taskId){
    const first = tasks[0];
    if(first.collected_at === (PAGE.data.meta || {}).collected_at){
      TASK_CACHE[first.id] = PAGE.data;
    }
    state.view = {type:"task", taskId: first.id};
    openTasks.add(first.id);
  }
  renderTasks();
  renderTable();
  renderMainHeader();
  const meta = PAGE.data.meta || {};
  document.getElementById("navUpdated").textContent = meta.collected_at
    ? `最近采集：${formatWhen(meta.collected_at)}`
    : "尚无数据";
}

/* 仅榜单区域的骨架屏（加载任务数据时用） */
function showTableSkeleton(on){
  if(!on){
    renderTable();
    return;
  }
  const isMobile = window.matchMedia("(max-width: 640px)").matches;
  if(isMobile){
    document.getElementById("repoList").innerHTML = Array.from({length:5}, () => `
      <div class="repo-row">
        <span class="sk" style="display:block;width:55%;margin-bottom:9px"></span>
        <span class="sk" style="display:block;width:88%;margin-bottom:9px"></span>
        <span class="sk" style="display:block;width:60%"></span>
      </div>`).join("");
    return;
  }
  document.getElementById("tableBody").innerHTML = Array.from({length:5}, () => `
    <div class="sk-row" style="display:grid;grid-template-columns:36px 1fr 80px 90px 80px;gap:12px;align-items:center;padding:12px 10px;border-bottom:1px solid var(--hairline)">
      <span class="sk" style="width:18px"></span>
      <span class="sk"></span>
      <span class="sk" style="width:64px"></span>
      <span class="sk" style="width:70px"></span>
      <span class="sk" style="width:70px"></span>
    </div>`).join("");
}

function showSkeleton(on){
  if(!on){
    renderAll();
    return;
  }
  document.getElementById("taskList").innerHTML = Array.from({length:4}, () => `
    <div style="padding:11px 12px;margin-bottom:8px">
      <span class="sk" style="display:block;width:45%;margin-bottom:9px"></span>
      <span class="sk" style="display:block;width:92%"></span>
    </div>`).join("");
  showTableSkeleton(true);
}

async function refresh(){
  const btn = document.getElementById("refreshBtn");
  const label = btn.querySelector(".btn-label");
  btn.disabled = true;
  label.textContent = "采集中...";
  showSkeleton(true);
  try{
    const resp = await fetch("/api/refresh", { method:"POST" });
    const payload = await resp.json();
    if(payload.error){
      showBanner(payload.error, true);
      return;
    }
    PAGE.data = payload.data;
    PAGE.tasks = payload.tasks || [];
    openTasks.clear();
    state.showAllTasks = false;
    state.view = {type:"task", taskId:null}; // 重新选中最新任务
    document.getElementById("repoPanel").hidden = true;
    document.getElementById("rankingPanel").hidden = false;
    renderAll();
    const latest = (PAGE.tasks || [])[0];
    showBanner(latest ? `数据已更新，任务 #${latest.id} 已生成` : "数据已更新", false);
  }catch(err){
    showBanner("刷新失败，请稍后重试", true);
  }finally{
    btn.disabled = false;
    label.textContent = "立即采集";
    showSkeleton(false);
  }
}

/* 事件绑定 */
document.getElementById("refreshBtn").addEventListener("click", refresh);
document.getElementById("searchInput").oninput = (e) => { state.query = e.target.value; renderTable(); };
document.getElementById("aiOnly").onchange = (e) => { state.aiOnly = e.target.checked; renderTable(); };
document.getElementById("langSelect").onchange = (e) => { state.lang = e.target.value; renderTable(); };
document.getElementById("taskMore").addEventListener("click", () => {
  state.showAllTasks = !state.showAllTasks;
  renderTasks();
});
document.getElementById("taskList").addEventListener("click", (e) => {
  const card = e.target.closest(".task-card");
  if(card) openTask(Number(card.dataset.id));
});
document.getElementById("repoBackBtn").addEventListener("click", backToRanking);
// 回到顶部：滚动超过一屏后显示，点击平滑回顶（尊重 reduced-motion）
const backTopBtn = document.getElementById("backTopBtn");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let scrollTicking = false;
window.addEventListener("scroll", () => {
  if(scrollTicking) return;
  scrollTicking = true;
  requestAnimationFrame(() => {
    backTopBtn.hidden = window.scrollY < 600;
    scrollTicking = false;
  });
}, {passive:true});
backTopBtn.addEventListener("click", () => {
  window.scrollTo({ top:0, behavior: reduceMotion ? "auto" : "smooth" });
});
document.getElementById("repoTabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if(!btn || btn.disabled) return;
  REPO_TAB = btn.dataset.tab;
  renderRepo();
});
// 仓库行点击进入详情（仓库名链接仍可单独打开 GitHub）
function bindRepoRowClicks(container){
  container.addEventListener("click", (e) => {
    if(e.target.closest("a")) return;
    const row = e.target.closest("[data-name]");
    if(row) openRepo(row.dataset.name);
  });
}
bindRepoRowClicks(document.getElementById("tableBody"));
bindRepoRowClicks(document.getElementById("repoList"));
// 窗口尺寸跨断点时重新渲染（表格/列表切换、任务折叠条数变化）
window.matchMedia("(max-width: 640px)").addEventListener("change", () => { renderTable(); renderTasks(); });
renderAll();
</script>
</body>
</html>
"""
