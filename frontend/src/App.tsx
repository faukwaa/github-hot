import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronUp, Heart, RefreshCw } from "lucide-react";
import { Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { RankingPanel } from "@/components/RankingPanel";
import { RepoDetail } from "@/components/RepoDetail";
import { TaskPanel } from "@/components/TaskPanel";
import { WatchedPage } from "@/components/WatchedPage";
import { Button } from "@/components/ui/button";
import {
  deleteTask,
  fetchDashboard,
  fetchTaskData,
  fetchWatched,
  formatWhen,
  refreshDashboard,
  toggleWatch,
  type Payload,
  type RankingData,
  type RepoItem,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const SCROLL_KEY = "ghot-scroll";

/* 应用壳：共享数据状态 + 导航 / footer / 回到顶部 */
export default function App() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [taskCache, setTaskCache] = useState<Record<number, RankingData>>({});
  const [refreshing, setRefreshing] = useState(false);
  const [banner, setBanner] = useState<{ text: string; error: boolean } | null>(null);
  const [backTopVisible, setBackTopVisible] = useState(false);
  const [watched, setWatched] = useState<Set<string>>(new Set());
  const navigate = useNavigate();
  const location = useLocation();
  const scrollTicking = useRef(false);
  const taskCacheRef = useRef(taskCache);
  taskCacheRef.current = taskCache;

  useEffect(() => {
    fetchDashboard()
      .then((p) => {
        setPayload(p);
        if (p.tasks.length > 0) {
          const first = p.tasks[0];
          setTaskCache((prev) => ({ ...prev, [first.id]: p.data }));
        }
        if (p.error) setBanner({ text: p.error, error: true });
      })
      .catch(() => setBanner({ text: "数据加载失败，请刷新页面重试", error: true }));
  }, []);

  /* 回到顶部按钮 */
  useEffect(() => {
    const onScroll = () => {
      if (scrollTicking.current) return;
      scrollTicking.current = true;
      requestAnimationFrame(() => {
        setBackTopVisible(window.scrollY > 600);
        scrollTicking.current = false;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  /* 加载某次任务的历史榜单（带缓存） */
  const loadTask = useCallback(async (taskId: number) => {
    if (taskCacheRef.current[taskId]) return;
    try {
      const data = await fetchTaskData(taskId);
      setTaskCache((prev) => ({ ...prev, [taskId]: data }));
    } catch {
      /* 任务数据加载失败时保留空列表 */
    }
  }, []);

  /* 加载关注列表 */
  useEffect(() => {
    fetchWatched()
      .then((p) => setWatched(new Set(p.watched)))
      .catch(() => {});
  }, []);

  /* 关注 / 取消关注 */
  const toggleWatched = useCallback(async (name: string) => {
    try {
      const p = await toggleWatch(name);
      setWatched(new Set(p.watched_list));
    } catch {
      /* 忽略失败 */
    }
  }, []);

  /* 删除任务：确认后调用 API，并重新加载任务列表 */
  const handleDeleteTask = useCallback(async (taskId: number) => {
    if (!window.confirm(`确定删除任务 #${taskId} 及其榜单快照？此操作不可恢复。`)) return;
    try {
      await deleteTask(taskId);
      const p = await fetchDashboard();
      setPayload(p);
      if (p.tasks.length > 0) {
        const first = p.tasks[0];
        setTaskCache({ [first.id]: p.data });
      }
      setBanner({ text: `任务 #${taskId} 已删除`, error: false });
    } catch {
      setBanner({ text: "删除任务失败，请重试", error: true });
    }
  }, []);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const p = await refreshDashboard();
      setPayload(p);
      if (p.tasks.length > 0) {
        const first = p.tasks[0];
        setTaskCache({ [first.id]: p.data });
      }
      if (p.error) {
        setBanner({ text: p.error, error: true });
      } else {
        const latest = p.tasks[0];
        setBanner({
          text: latest ? `数据已更新，任务 #${latest.id} 已生成` : "数据已更新",
          error: false,
        });
      }
    } catch {
      setBanner({ text: "刷新失败，请稍后重试", error: true });
    } finally {
      setRefreshing(false);
    }
  }, []);

  const openRepo = useCallback(
    (repoName: string) => {
      sessionStorage.setItem(SCROLL_KEY, String(window.scrollY));
      const [owner, name] = repoName.split("/");
      navigate(`/repo/${encodeURIComponent(owner)}/${encodeURIComponent(name)}`);
    },
    [navigate]
  );

  return (
    <div className="flex min-h-screen flex-col">
      {/* Nav */}
      <nav className="sticky top-0 z-50 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1400px] items-center gap-4 px-6">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="flex items-center gap-2.5 font-display text-[17px] font-normal tracking-tight hover:text-primary"
          >
            {/* Logo：暖黑方块 + 珊瑚上升线 + 奶油四辐星（与 favicon 一致） */}
            <svg viewBox="0 0 32 32" className="size-7" aria-hidden="true">
              <rect width="32" height="32" rx="8" fill="#141413" />
              <polyline
                points="6,23 11,18 16,20 21,13"
                fill="none"
                stroke="#cc785c"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path d="M22 4 L23.2 8.8 L28 10 L23.2 11.2 L22 16 L20.8 11.2 L16 10 L20.8 8.8 Z" fill="#faf9f5" />
            </svg>
            GitHub 热度周榜
          </button>
          <div className="flex-1" />
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/watched")}
            className={cn("gap-1.5", location.pathname === "/watched" && "border-primary text-primary")}
          >
            <Heart className={cn("size-3.5", watched.size > 0 && "fill-primary text-primary")} />
            关注{watched.size > 0 ? `（${watched.size}）` : ""}
          </Button>
          <span className="hidden text-xs tabular-nums text-muted-foreground sm:block">
            {payload?.data.meta?.collected_at
              ? `最近采集：${formatWhen(payload.data.meta.collected_at)}`
              : "尚无数据"}
          </span>
          <Button size="sm" onClick={refresh} disabled={refreshing}>
            <RefreshCw className={cn("size-3.5", refreshing && "animate-spin")} />
            {refreshing ? "采集中..." : "立即采集"}
          </Button>
        </div>
      </nav>

      {/* Banner */}
      {banner && (
        <div className="mx-auto max-w-[1400px] px-6 pt-4">
          <div
            className={cn(
              "rounded-lg border-l-4 border px-4 py-2.5 text-[13px]",
              banner.error ? "border-orange bg-card" : "border-primary bg-card"
            )}
          >
            {banner.text}
          </div>
        </div>
      )}

      <main className="flex-1">
        <Routes>
          <Route
            path="/"
            element={
              <RankingPage
                payload={payload}
                taskCache={taskCache}
                loadTask={loadTask}
                watched={watched}
                onToggleWatch={toggleWatched}
                onDeleteTask={handleDeleteTask}
                onOpenRepo={openRepo}
              />
            }
          />
          <Route
            path="/repo/:owner/:name"
            element={
              <RepoPage payload={payload} taskCache={taskCache} watched={watched} onToggleWatch={toggleWatched} />
            }
          />
          <Route
            path="/watched"
            element={
              <WatchedPage watched={watched} onToggleWatch={toggleWatched} onOpenRepo={openRepo} />
            }
          />
        </Routes>
      </main>

      {/* 回到顶部 */}
      <button
        type="button"
        aria-label="回到顶部"
        onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
        className={cn(
          "fixed bottom-7 right-7 z-50 grid size-11 place-items-center rounded-full border bg-background text-muted-foreground shadow-md transition-all hover:border-border hover:text-primary active:scale-95",
          backTopVisible ? "opacity-100" : "pointer-events-none opacity-0"
        )}
      >
        <ChevronUp className="size-5" />
      </button>
    </div>
  );
}

/* 列表页：任务栏 + 榜单（URL: /） */
interface RankingPageProps {
  payload: Payload | null;
  taskCache: Record<number, RankingData>;
  loadTask: (taskId: number) => Promise<void>;
  watched: Set<string>;
  onToggleWatch: (name: string) => void;
  onDeleteTask: (taskId: number) => void;
  onOpenRepo: (name: string) => void;
}

function RankingPage({
  payload,
  taskCache,
  loadTask,
  watched,
  onToggleWatch,
  onDeleteTask,
  onOpenRepo,
}: RankingPageProps) {
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [lang, setLang] = useState("");
  const [aiOnly, setAiOnly] = useState(false);
  const [watchedOnly, setWatchedOnly] = useState(false);

  /* 默认选中第一个任务 */
  useEffect(() => {
    if (payload && payload.tasks.length > 0 && selectedTaskId === null) {
      setSelectedTaskId(payload.tasks[0].id);
    }
  }, [payload, selectedTaskId]);

  /* 从详情返回时恢复滚动位置 */
  useEffect(() => {
    const saved = sessionStorage.getItem(SCROLL_KEY);
    if (saved) {
      sessionStorage.removeItem(SCROLL_KEY);
      requestAnimationFrame(() => window.scrollTo(0, Number(saved)));
    }
  }, []);

  const openTask = useCallback(
    (taskId: number) => {
      setSelectedTaskId(taskId);
      loadTask(taskId);
    },
    [loadTask]
  );

  const tasks = payload?.tasks || [];
  const selectedTask = tasks.find((t) => t.id === selectedTaskId);
  const data: RankingData =
    selectedTaskId != null ? taskCache[selectedTaskId] || { items: [], meta: {} } : { items: [], meta: {} };

  return (
    <div className="relative mx-auto max-w-[1400px] px-6">
      {/* 移动端：任务栏在文档流顶部 */}
      <div className="pt-6 lg:hidden">
        <TaskPanel tasks={tasks} selectedId={selectedTaskId} onSelect={openTask} onDeleteTask={onDeleteTask} />
      </div>

      {/* 桌面端：任务栏 fixed 固定，不随页面滚动 */}
      <div
        className="fixed top-20 z-30 hidden h-[calc(100vh-96px)] w-[300px] lg:block"
        style={{ left: "max(24px, calc((100vw - 1400px) / 2 + 24px))" }}
      >
        <TaskPanel tasks={tasks} selectedId={selectedTaskId} onSelect={openTask} onDeleteTask={onDeleteTask} />
      </div>

      <div className="px-0 pb-4 pt-4 lg:pl-[324px]">
        <RankingPanel
          data={data}
          title={selectedTask ? `任务 #${selectedTask.id} · 榜单` : "任务榜单"}
          note={
            data.meta?.collected_at
              ? `采集于 ${formatWhen(data.meta.collected_at)} · 收录 ${data.items.length} 个`
              : "该任务没有保存仓库快照（历史数据）"
          }
          query={query}
          lang={lang}
          aiOnly={aiOnly}
          loading={!payload}
          onQueryChange={setQuery}
          onLangChange={setLang}
          onAiOnlyChange={setAiOnly}
          watched={watched}
          watchedOnly={watchedOnly}
          onWatchedOnlyChange={setWatchedOnly}
          onToggleWatch={onToggleWatch}
          onOpenRepo={onOpenRepo}
        />
      </div>
    </div>
  );
}

/* 详情页：仓库 README（URL: /repo/:owner/:name） */
function RepoPage({
  payload,
  taskCache,
  watched,
  onToggleWatch,
}: {
  payload: Payload | null;
  taskCache: Record<number, RankingData>;
  watched: Set<string>;
  onToggleWatch: (name: string) => void;
}) {
  const { owner, name } = useParams<{ owner: string; name: string }>();
  const navigate = useNavigate();
  const fullName = `${owner}/${name}`;

  /* 从任务数据中查找仓库信息（找不到时 bits 留空，README 不受影响） */
  const item: RepoItem | undefined = (() => {
    const latest = payload?.data.items || [];
    const found = latest.find((i) => i.full_name === fullName);
    if (found) return found;
    for (const key of Object.keys(taskCache)) {
      const hit = taskCache[Number(key)].items.find((i) => i.full_name === fullName);
      if (hit) return hit;
    }
    return undefined;
  })();

  const backToRanking = useCallback(() => {
    navigate("/");
  }, [navigate]);

  return (
    <div className="mx-auto max-w-[1400px] px-6 pt-6">
      <div className="pb-4">
        <RepoDetail
          fullName={fullName}
          item={item}
          watched={watched.has(fullName)}
          onToggleWatch={() => onToggleWatch(fullName)}
          onBack={backToRanking}
        />
      </div>
    </div>
  );
}
