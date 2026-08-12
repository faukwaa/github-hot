import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, ExternalLink, Heart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { fetchRepoReadme, fmtK, type RepoReadme, type RepoItem } from "@/lib/api";
import { renderMarkdown } from "@/lib/markdown";
import { cn } from "@/lib/utils";

interface RepoDetailProps {
  fullName: string;
  item?: RepoItem;
  watched: boolean;
  onToggleWatch: () => void;
  onBack: () => void;
}

export function RepoDetail({ fullName, item, watched, onToggleWatch, onBack }: RepoDetailProps) {
  const [repo, setRepo] = useState<RepoReadme | null>(null);
  const [tab, setTab] = useState("raw");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [translating, setTranslating] = useState(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    setLoading(true);
    setError(null);
    setTab("raw");
    setRepo(null);
    fetchRepoReadme(fullName)
      .then((p) => {
        if (!mounted.current) return;
        if (p.error || !p.readme_raw) {
          setError(p.error || "README 加载失败");
        } else {
          setRepo(p);
        }
      })
      .catch(() => mounted.current && setError("加载失败，请重试"))
      .finally(() => mounted.current && setLoading(false));
    return () => {
      mounted.current = false;
    };
  }, [fullName]);

  const ensureTranslation = useCallback(async () => {
    if (!repo || repo.is_zh || repo.readme_translated || translating) return;
    setTranslating(true);
    try {
      const p = await fetchRepoReadme(fullName, true);
      if (!mounted.current) return;
      if (p.readme_translated) {
        setRepo(p);
        setTab("zh");
      } else {
        setError(p.translate_error || "翻译失败");
      }
    } catch {
      if (mounted.current) setError("翻译请求失败，请重试");
    } finally {
      if (mounted.current) setTranslating(false);
    }
  }, [repo, fullName, translating]);

  const handleTabChange = (value: string) => {
    setTab(value);
    if (value === "zh" && repo && !repo.is_zh && !repo.readme_translated) {
      ensureTranslation();
    }
  };

  const bits = [];
  if (item?.language) bits.push(item.language);
  if (item?.stars) bits.push(`${fmtK(item.stars)} Stars`);
  if (item?.weekly_stars) bits.push(`本周 +${fmtK(item.weekly_stars)}`);

  const showZhTab = repo && !repo.is_zh;
  let readmeHtml = "";
  if (repo) {
    readmeHtml = renderMarkdown(
      tab === "zh" && repo.readme_translated ? repo.readme_translated : repo.readme_raw,
      fullName
    );
  }

  return (
    <div className="rounded-xl border bg-card p-5">
      <div className="mb-3.5 flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate font-display text-xl font-normal tracking-tight">{fullName}</h2>
          <p className="text-xs text-muted-foreground">{bits.join(" · ")}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            variant={watched ? "default" : "outline"}
            size="sm"
            onClick={onToggleWatch}
            className="gap-1.5"
          >
            <Heart className={cn("size-3.5", watched && "fill-primary-foreground")} />
            {watched ? "已关注" : "关注"}
          </Button>
          <Button asChild variant="outline" size="sm">
            <a href={`https://github.com/${fullName}`} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="size-3.5" />
              打开原仓库
            </a>
          </Button>
          <Button variant="outline" size="sm" onClick={onBack}>
            <ArrowLeft className="size-3.5" />
            返回榜单
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-full" />
          ))}
        </div>
      ) : error ? (
        <p className="py-4 text-[13.5px] text-orange">{error}</p>
      ) : repo ? (
        <>
          {showZhTab && (
            <Tabs value={tab} onValueChange={handleTabChange} className="-mx-1 mb-2">
              <TabsList className="h-10 gap-2 rounded-none border-b bg-transparent p-0">
                <TabsTrigger
                  value="raw"
                  className="rounded-none border-b-2 border-transparent px-3 pb-2 pt-1 text-[13.5px] font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-primary"
                >
                  原文
                </TabsTrigger>
                <TabsTrigger
                  value="zh"
                  disabled={translating && !repo.readme_translated}
                  className="rounded-none border-b-2 border-transparent px-3 pb-2 pt-1 text-[13.5px] font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-primary disabled:opacity-50"
                >
                  {translating && !repo.readme_translated ? "翻译中..." : "中文版"}
                </TabsTrigger>
              </TabsList>
            </Tabs>
          )}
          <div
            className="readme max-w-none text-[15px] leading-relaxed text-foreground"
            dangerouslySetInnerHTML={{ __html: readmeHtml }}
          />
          {tab === "zh" && repo && !repo.is_zh && !repo.readme_translated && !translating && (
            <Button variant="outline" size="sm" onClick={ensureTranslation} className="mt-2">
              生成中文版
            </Button>
          )}
        </>
      ) : null}
    </div>
  );
}
