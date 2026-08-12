import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Heart, Search, Sparkles } from "lucide-react";
import {
  fmtK,
  langColor,
  type RankingData,
  type RepoItem,
} from "@/lib/api";
import { cn } from "@/lib/utils";

interface RankingPanelProps {
  data: RankingData;
  title: string;
  note: string;
  query: string;
  lang: string;
  aiOnly: boolean;
  watched: Set<string>;
  watchedOnly: boolean;
  loading: boolean;
  onQueryChange: (v: string) => void;
  onLangChange: (v: string) => void;
  onAiOnlyChange: (v: boolean) => void;
  onWatchedOnlyChange: (v: boolean) => void;
  onToggleWatch: (name: string) => void;
  onOpenRepo: (name: string) => void;
}

const ALL_LANG = "__all__";

function visibleItems(
  data: RankingData,
  query: string,
  lang: string,
  aiOnly: boolean,
  watched: Set<string>,
  watchedOnly: boolean
): RepoItem[] {
  const q = query.trim().toLowerCase();
  return data.items
    .filter((item) => {
      const matchLang = !lang || item.language === lang;
      const matchAi = !aiOnly || item.is_ai;
      const matchWatched = !watchedOnly || watched.has(item.full_name);
      const haystack = `${item.full_name} ${item.description || ""} ${item.ai_summary || ""}`.toLowerCase();
      return matchLang && matchAi && matchWatched && (!q || haystack.includes(q));
    })
    .sort((a, b) => (b.weekly_stars || 0) - (a.weekly_stars || 0));
}

function WatchButton({
  name,
  watched,
  onToggleWatch,
}: {
  name: string;
  watched: boolean;
  onToggleWatch: (name: string) => void;
}) {
  return (
    <button
      type="button"
      aria-label={watched ? "取消关注" : "特别关注"}
      title={watched ? "取消关注" : "特别关注"}
      onClick={(e) => {
        e.stopPropagation();
        onToggleWatch(name);
      }}
      className={cn(
        "grid size-6 shrink-0 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-primary",
        watched && "text-primary"
      )}
    >
      <Heart className={cn("size-3.5", watched && "fill-primary")} />
    </button>
  );
}

function RepoName({ item, onOpenRepo }: { item: RepoItem; onOpenRepo: (n: string) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <button
        type="button"
        onClick={() => onOpenRepo(item.full_name)}
        className="font-semibold tracking-tight hover:text-primary"
      >
        {item.full_name}
      </button>
      {item.is_ai && (
        <Badge className="h-4 gap-1 border-0 bg-secondary px-1.5 text-[10px] font-medium text-foreground">
          <Sparkles className="size-2.5 text-primary" />
          AI
        </Badge>
      )}
    </div>
  );
}

export function RankingPanel({
  data,
  title,
  note,
  query,
  lang,
  aiOnly,
  watched,
  watchedOnly,
  loading,
  onQueryChange,
  onLangChange,
  onAiOnlyChange,
  onWatchedOnlyChange,
  onToggleWatch,
  onOpenRepo,
}: RankingPanelProps) {
  const items = visibleItems(data, query, lang, aiOnly, watched, watchedOnly);
  const langs = [...new Set(data.items.map((i) => i.language || "Unknown"))].sort();
  const growthText = (item: RepoItem) =>
    item.weekly_growth == null ? "-" : `+${item.weekly_growth.toFixed(1)}%`;

  return (
    <div className="rounded-xl border bg-card p-5">
      <div className="mb-3.5 flex items-baseline justify-between gap-3">
        <div>
          <h2 className="font-display text-xl font-normal tracking-tight">{title}</h2>
          <p className="text-xs text-muted-foreground">{note}</p>
        </div>
      </div>

      <div className="mb-3.5 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[180px] flex-1">
          <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => onQueryChange(e.target.value)}
            placeholder="搜索项目或简介"
            className="pl-8"
          />
        </div>
        <Select value={lang || ALL_LANG} onValueChange={(v: string) => onLangChange(v === ALL_LANG ? "" : v)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="全部语言" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_LANG}>全部语言</SelectItem>
            {langs.map((l) => (
              <SelectItem key={l} value={l}>
                {l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <label className="flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-[13px]">
          <Switch checked={aiOnly} onCheckedChange={onAiOnlyChange} />
          只看 AI
        </label>
        <Button
          type="button"
          variant={watchedOnly ? "default" : "outline"}
          size="sm"
          onClick={() => onWatchedOnlyChange(!watchedOnly)}
          className="gap-1.5"
        >
          <Heart className={cn("size-3.5", watchedOnly && "fill-primary-foreground")} />
          关注
        </Button>
        <span className="ml-auto whitespace-nowrap text-xs text-muted-foreground">
          {items.length} / {data.items.length}
        </span>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : (
        <>
          {/* 桌面表格 */}
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full border-collapse text-[13.5px]">
              <thead>
                <tr className="border-b text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                  <th className="whitespace-nowrap px-2.5 py-2 font-semibold">#</th>
                  <th className="whitespace-nowrap px-2.5 py-2 font-semibold">项目</th>
                  <th className="whitespace-nowrap px-2.5 py-2 font-semibold">语言</th>
                  <th className="whitespace-nowrap px-2.5 py-2 text-right font-semibold">本周 Star</th>
                  <th className="whitespace-nowrap px-2.5 py-2 text-right font-semibold">总 Star</th>
                  <th className="whitespace-nowrap px-2.5 py-2 text-right font-semibold">周增长</th>
                  <th className="px-2.5 py-2" />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.full_name}
                    onClick={() => onOpenRepo(item.full_name)}
                    className="cursor-pointer border-b transition-colors last:border-0 hover:bg-accent/40"
                  >
                    <td className="px-2.5 py-3 tabular-nums text-muted-foreground">{item.rank}</td>
                    <td className="px-2.5 py-3">
                      <RepoName item={item} onOpenRepo={onOpenRepo} />
                      <p className="mt-1 max-w-[420px] text-[12.5px] leading-relaxed text-muted-foreground">
                        {item.ai_summary || item.description || "暂无简介"}
                      </p>
                    </td>
                    <td className="whitespace-nowrap px-2.5 py-3">
                      <span className="mr-1.5 inline-block size-2 rounded-full" style={{ background: langColor(item.language) }} />
                      {item.language || "Unknown"}
                    </td>
                    <td className="px-2.5 py-3 text-right font-semibold tabular-nums">
                      +{fmtK(item.weekly_stars)}
                    </td>
                    <td className="px-2.5 py-3 text-right tabular-nums">{fmtK(item.stars)}</td>
                    <td className={cn("px-2.5 py-3 text-right font-semibold tabular-nums", item.weekly_growth != null && "text-destructive")}>
                      {growthText(item)}
                    </td>
                    <td className="px-2.5 py-3 text-right">
                      <WatchButton
                        name={item.full_name}
                        watched={watched.has(item.full_name)}
                        onToggleWatch={onToggleWatch}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 移动端列表卡片 */}
          <div className="divide-y md:hidden">
            {items.map((item) => (
              <button
                key={item.full_name}
                type="button"
                onClick={() => onOpenRepo(item.full_name)}
                className="block w-full py-3.5 text-left"
              >
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="text-[12.5px] tabular-nums text-muted-foreground">#{item.rank}</span>
                  <span className="min-w-0 break-all text-[14.5px] font-semibold tracking-tight">
                    {item.full_name}
                  </span>
                  {item.is_ai && (
                    <Badge className="h-4 gap-1 border-0 bg-secondary px-1.5 text-[10px] font-medium text-foreground">
                      <Sparkles className="size-2.5 text-primary" />
                      AI
                    </Badge>
                  )}
                  <WatchButton
                    name={item.full_name}
                    watched={watched.has(item.full_name)}
                    onToggleWatch={onToggleWatch}
                  />
                </div>
                {(item.ai_summary || item.description) && (
                  <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                    {item.ai_summary || item.description}
                  </p>
                )}
                <div className="mt-1.5 flex flex-wrap gap-3.5 text-xs tabular-nums text-muted-foreground">
                  <span>
                    <span className="mr-1.5 inline-block size-2 rounded-full" style={{ background: langColor(item.language) }} />
                    {item.language || "Unknown"}
                  </span>
                  <span>
                    本周 <b className="font-semibold text-foreground">+{fmtK(item.weekly_stars)}</b>
                  </span>
                  <span>
                    总 <b className="font-semibold text-foreground">{fmtK(item.stars)}</b>
                  </span>
                  <span>
                    增长{" "}
                    <b className={cn("font-semibold", item.weekly_growth != null ? "text-destructive" : "text-foreground")}>
                      {growthText(item)}
                    </b>
                  </span>
                </div>
              </button>
            ))}
          </div>

          {items.length === 0 && (
            <p className="py-10 text-center text-[13.5px] text-muted-foreground">当前筛选条件下没有项目</p>
          )}
        </>
      )}
    </div>
  );
}
