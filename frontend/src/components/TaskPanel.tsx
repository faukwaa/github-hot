import { useState } from "react";
import { ChevronRight, Trash2 } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { formatWhen, taskRange, type Task } from "@/lib/api";
import { cn } from "@/lib/utils";

interface TaskPanelProps {
  tasks: Task[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onDeleteTask: (id: number) => void;
}

const DAY_MS = 86400000;
const OLD_AFTER_DAYS = 30; // 超过 30 天的任务自动折叠

export function TaskPanel({ tasks, selectedId, onSelect, onDeleteTask }: TaskPanelProps) {
  const [midExpanded, setMidExpanded] = useState(false);
  const [yearExpanded, setYearExpanded] = useState<Set<number>>(new Set());

  const now = new Date();
  const thisYear = now.getFullYear();
  const ageDays = (collectedAt: string) =>
    (now.getTime() - new Date(collectedAt).getTime()) / DAY_MS;

  const recent = tasks.filter((t) => ageDays(t.collected_at) <= OLD_AFTER_DAYS);
  const mid = tasks.filter(
    (t) => ageDays(t.collected_at) > OLD_AFTER_DAYS && new Date(t.collected_at).getFullYear() === thisYear
  );
  // 一年前及更早：按年份分组折叠
  const yearGroups: { year: number; tasks: Task[] }[] = [];
  for (const task of tasks) {
    const year = new Date(task.collected_at).getFullYear();
    if (year >= thisYear) continue;
    let group = yearGroups.find((g) => g.year === year);
    if (!group) {
      group = { year, tasks: [] };
      yearGroups.push(group);
    }
    group.tasks.push(task);
  }
  yearGroups.sort((a, b) => b.year - a.year);

  const toggleYear = (year: number) => {
    setYearExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(year)) {
        next.delete(year);
      } else {
        next.add(year);
      }
      return next;
    });
  };

  const renderCollapseHead = (label: string, count: number, expanded: boolean, onToggle: () => void) => (
    <button
      type="button"
      onClick={onToggle}
      className="flex w-full items-center gap-1.5 rounded-lg px-3 py-2 text-left text-[12.5px] font-medium text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground"
    >
      <ChevronRight className={cn("size-3.5 transition-transform", expanded && "rotate-90")} />
      {label}（{count}）
    </button>
  );

  const renderTask = (task: Task) => {
    const selected = task.id === selectedId;
    const dotCls = task.status === "done" ? "bg-green" : "bg-orange";
    return (
      <button
        key={task.id}
        type="button"
        onClick={() => onSelect(task.id)}
        className={cn(
          "group w-full rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-accent/60",
          selected && "bg-secondary"
        )}
      >
        <div className="flex items-center gap-2">
          <span className={cn("size-[7px] shrink-0 rounded-full", dotCls)} />
          <span className={cn("text-[13px] font-bold tracking-tight", selected && "text-primary")}>
            任务 #{task.id}
          </span>
          <button
            type="button"
            aria-label={`删除任务 #${task.id}`}
            title="删除任务"
            onClick={(e) => {
              e.stopPropagation();
              onDeleteTask(task.id);
            }}
            className="ml-auto grid size-6 shrink-0 place-items-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:bg-accent hover:text-destructive group-hover:opacity-100"
          >
            <Trash2 className="size-3.5" />
          </button>
          <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground">
            {taskRange(task)}
          </span>
        </div>
        <p
          className={cn(
            "mt-1.5 text-[12.5px] leading-relaxed text-muted-foreground",
            !selected && "line-clamp-2"
          )}
        >
          {task.summary || "该任务未生成 AI 总结。"}
        </p>
        {selected && (
          <div className="mt-2 border-t pt-2 text-[11.5px] text-muted-foreground">
            <span>
              采集于 {formatWhen(task.collected_at)} · 收录 {task.repo_count} 个 · AI {task.ai_count} 个
            </span>
            {task.error && <p className="mt-1 text-orange">{task.error}</p>}
          </div>
        )}
      </button>
    );
  };

  return (
    <aside className="flex h-full max-h-[34vh] flex-col rounded-xl border bg-card p-4 lg:max-h-none">
      <div className="flex items-baseline gap-2 border-b px-1 pb-3">
        <h2 className="font-display text-lg font-normal tracking-tight">采集任务</h2>
        <span className="text-[11.5px] text-muted-foreground">
          {tasks.length ? `${tasks.length} 次` : ""}
        </span>
      </div>

      <ScrollArea className="min-h-0 flex-1 py-2 pr-1">
        {tasks.length === 0 ? (
          <p className="px-2 py-6 text-center text-[13px] text-muted-foreground">
            还没有采集任务。点击右上角「立即采集」，每次拉取会登记为一个任务并生成 AI 总结。
          </p>
        ) : (
          <div className="space-y-1.5">
            {recent.map(renderTask)}

            {mid.length > 0 && (
              <>
                {renderCollapseHead("更早的任务", mid.length, midExpanded, () => setMidExpanded((v) => !v))}
                {midExpanded && mid.map(renderTask)}
              </>
            )}

            {yearGroups.map(({ year, tasks: groupTasks }) => (
              <div key={year}>
                {renderCollapseHead(`${year} 年`, groupTasks.length, yearExpanded.has(year), () =>
                  toggleYear(year)
                )}
                {yearExpanded.has(year) && groupTasks.map(renderTask)}
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </aside>
  );
}
