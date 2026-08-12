export interface RepoItem {
  full_name: string;
  url: string;
  description: string | null;
  language: string | null;
  stars: number;
  forks: number;
  weekly_stars: number | null;
  topics: string[];
  created_at: string | null;
  pushed_at: string | null;
  source: string;
  ai_reasons: string[];
  ai_summary: string | null;
  collected_at: string;
  rank: number;
  weekly_growth: number | null;
  is_ai: boolean;
}

export interface Task {
  id: number;
  collected_at: string;
  status: string;
  repo_count: number;
  ai_count: number;
  summary: string | null;
  error: string | null;
  since: string;
  created_at: string;
}

export interface RankingData {
  items: RepoItem[];
  meta: { collected_at?: string | null; repo_count?: number } & Record<string, unknown>;
}

export interface Payload {
  data: RankingData;
  tasks: Task[];
  warnings: string[];
  error: string | null;
  generated_at: string;
}

export interface RepoReadme {
  full_name: string;
  readme_raw: string | null;
  readme_translated: string | null;
  is_zh: boolean;
  translate_error?: string | null;
  cached?: boolean;
  error?: string | null;
}

export async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()) as T;
}

export function fetchDashboard(): Promise<Payload> {
  return fetchJson<Payload>("/api/data");
}

export async function deleteTask(taskId: number): Promise<void> {
  const resp = await fetch(`/api/tasks/delete?task=${taskId}`, { method: "POST" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
}

export function refreshDashboard(): Promise<Payload> {
  return fetchJson<Payload>("/api/refresh");
}

export async function fetchTaskData(taskId: number): Promise<RankingData> {
  const p = await fetchJson<{ data: RankingData; error?: string | null }>(
    `/api/data?task=${taskId}`
  );
  if (p.error) throw new Error(p.error);
  return p.data;
}

export function fetchRepoReadme(name: string, translate = false): Promise<RepoReadme> {
  return fetchJson<RepoReadme>(`/api/repo?name=${encodeURIComponent(name)}&translate=${translate ? 1 : 0}`);
}

export function fetchWatched(): Promise<{ watched: string[] }> {
  return fetchJson<{ watched: string[] }>("/api/watched");
}

export interface WatchedTaskRef {
  id: number;
  collected_at: string;
  since: string;
}

export interface WatchedRepo {
  full_name: string;
  watched_at: string;
  tasks: WatchedTaskRef[];
  latest?: RepoItem;
}

export function fetchWatchedRepos(): Promise<{ repos: WatchedRepo[] }> {
  return fetchJson<{ repos: WatchedRepo[] }>("/api/watched/repos");
}

export async function toggleWatch(name: string): Promise<{ watched: boolean; watched_list: string[] }> {
  const resp = await fetch(`/api/watched/toggle?name=${encodeURIComponent(name)}`, { method: "POST" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()) as { watched: boolean; watched_list: string[] };
}

/** Star 数格式化：>=1000 用 k 为单位（8,182 -> 8.2k） */
export function fmtK(value: number | null | undefined): string {
  if (value == null) return "-";
  if (value < 1000) return String(value);
  return (Math.round((value / 1000) * 10) / 10).toString() + "k";
}

export function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

const RANGE_DAYS: Record<string, number> = { daily: 1, weekly: 7, monthly: 30 };

/** 任务增长区间：采集日往前推 N 天（daily 1 / weekly 7 / monthly 30） */
export function taskRange(task: Task): string {
  const days = RANGE_DAYS[task.since || "weekly"] || 7;
  const end = new Date(task.collected_at);
  const start = new Date(end.getTime() - days * 86400000);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(start.getMonth() + 1)}/${p(start.getDate())}-${p(end.getMonth() + 1)}/${p(end.getDate())}`;
}

const LANG_COLORS: Record<string, string> = {
  Python: "#3776ab",
  TypeScript: "#3178c6",
  JavaScript: "#c2a53a",
  Go: "#00a2b8",
  Rust: "#d97706",
  "C++": "#db4d69",
  "Jupyter Notebook": "#da5b0b",
  C: "#5a6b7b",
  Shell: "#4e9a51",
  Java: "#c1440e",
  Swift: "#e05e2f",
  Kotlin: "#a95c9a",
  Dart: "#0175c2",
  PHP: "#7a4fd3",
  Ruby: "#c4283c",
  Unknown: "#8b93a3",
};

export function langColor(lang: string | null): string {
  return LANG_COLORS[lang || "Unknown"] || LANG_COLORS.Unknown;
}
