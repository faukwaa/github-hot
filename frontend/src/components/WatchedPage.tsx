import { useCallback, useEffect, useState } from "react";
import { Heart } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  fetchWatchedRepos,
  fmtK,
  formatWhen,
  langColor,
  type WatchedRepo,
} from "@/lib/api";
import { cn } from "@/lib/utils";

interface WatchedPageProps {
  watched: Set<string>;
  onToggleWatch: (name: string) => void;
  onOpenRepo: (name: string) => void;
}

export function WatchedPage({ watched, onToggleWatch, onOpenRepo }: WatchedPageProps) {
  const [repos, setRepos] = useState<WatchedRepo[] | null>(null);

  useEffect(() => {
    fetchWatchedRepos()
      .then((p) => setRepos(p.repos))
      .catch(() => setRepos([]));
  }, []);

  const removeWatch = useCallback(
    (name: string) => {
      onToggleWatch(name);
      setRepos((prev) => (prev ? prev.filter((r) => r.full_name !== name) : prev));
    },
    [onToggleWatch]
  );

  const taskLabel = (tasks: WatchedRepo["tasks"]) => {
    if (!tasks.length) return "未出现在任何任务榜单";
    const shown = tasks.slice(0, 3);
    const rest = tasks.length - shown.length;
    const text = `任务 #${shown.map((t) => t.id).join("、#")}`;
    return rest > 0 ? `${text} 等 ${tasks.length} 个任务` : text;
  };

  return (
    <div className="mx-auto max-w-[1400px] px-6 py-6">
      <div className="mb-5">
        <h1 className="font-display text-2xl font-normal tracking-tight">关注的仓库</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          {repos ? `${repos.length} 个仓库，汇总自不同任务的榜单` : "加载中..."}
        </p>
      </div>

      {repos === null ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : repos.length === 0 ? (
        <div className="rounded-xl border bg-card p-12 text-center text-[13.5px] text-muted-foreground">
          还没有关注的仓库。在榜单或仓库详情页点击爱心即可特别关注。
        </div>
      ) : (
        <div className="divide-y rounded-xl border bg-card">
          {repos.map((repo) => {
            const item = repo.latest;
            return (
              <div key={repo.full_name} className="flex items-start gap-4 p-4">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="取消关注"
                  title="取消关注"
                  onClick={() => removeWatch(repo.full_name)}
                  className={cn(
                    "mt-0.5 size-8 shrink-0 rounded-md text-primary hover:bg-accent",
                    !watched.has(repo.full_name) && "text-muted-foreground"
                  )}
                >
                  <Heart className={cn("size-4", watched.has(repo.full_name) && "fill-primary")} />
                </Button>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => onOpenRepo(repo.full_name)}
                      className="font-semibold tracking-tight hover:text-primary"
                    >
                      {repo.full_name}
                    </button>
                    {item?.is_ai && (
                      <Badge className="h-4 gap-1 border-0 bg-secondary px-1.5 text-[10px] font-medium text-foreground">
                        AI
                      </Badge>
                    )}
                  </div>

                  {(item?.ai_summary || item?.description) && (
                    <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                      {item?.ai_summary || item?.description}
                    </p>
                  )}

                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs tabular-nums text-muted-foreground">
                    <span>
                      <span
                        className="mr-1.5 inline-block size-2 rounded-full"
                        style={{ background: langColor(item?.language || null) }}
                      />
                      {item?.language || "Unknown"}
                    </span>
                    {item?.stars ? <span>总 {fmtK(item.stars)}</span> : null}
                    {item?.weekly_stars ? <span>本周 +{fmtK(item.weekly_stars)}</span> : null}
                    <span className="text-muted-foreground/70">关注于 {formatWhen(repo.watched_at)}</span>
                  </div>
                </div>

                <div className="shrink-0 self-center text-right">
                  {repo.tasks.length > 0 && (
                    <div className="text-[11.5px] text-muted-foreground">
                      <div className="mb-1">出现在</div>
                      <div className="font-medium text-foreground/80">{taskLabel(repo.tasks)}</div>
                      {repo.tasks[0] && (
                        <div className="mt-0.5 text-[11px] text-muted-foreground/70">
                          最近：{formatWhen(repo.tasks[0].collected_at)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
