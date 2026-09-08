"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface Task { id: number; title: string; status: string; priority: string; due_at?: string | null }
interface Project { id: number; code: string; name: string; status: string; progress: number; deadline?: string | null }

interface DelayChainStep { task_id: number; title: string; status: string; due_at: string | null; is_overdue: boolean }
interface DelayAnalysis { root_cause: DelayChainStep | null; chain: DelayChainStep[]; overdue_task_count: number; blocked_task_count: number }

function DelayChainPanel({ projectId }: { projectId: number }) {
  const [analysis, setAnalysis] = useState<DelayAnalysis | null>(null);

  useEffect(() => {
    apiFetch<DelayAnalysis>(`/api/v1/projects/${projectId}/delay-analysis`).then(setAnalysis).catch(() => setAnalysis(null));
  }, [projectId]);

  if (!analysis) return <div className="border-t border-base-border bg-base-bg/40 p-3 text-xs text-base-muted">Загрузка...</div>;
  if (!analysis.root_cause) return <div className="border-t border-base-border bg-base-bg/40 p-3 text-xs text-sev-low">Явных причин задержки не найдено.</div>;

  return (
    <div className="space-y-1.5 border-t border-base-border bg-base-bg/40 p-3 text-xs">
      <p className="text-[10px] uppercase text-base-muted">Причинно-следственная цепочка</p>
      {analysis.chain.map((s, i) => (
        <div key={s.task_id} className="flex items-center gap-2">
          {i > 0 && <span className="text-base-muted">↓</span>}
          <span className={s.is_overdue ? "text-sev-critical" : ""}>{s.title}</span>
          <span className="text-base-muted">({s.status}{s.due_at ? `, срок ${new Date(s.due_at).toLocaleDateString("ru-RU")}` : ""})</span>
        </div>
      ))}
    </div>
  );
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [overdueTasks, setOverdueTasks] = useState<Task[] | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    apiFetch<Project[]>("/api/v1/projects").then(setProjects).catch(() => setProjects([]));
    apiFetch<Task[]>("/api/v1/tasks").then((t) => setOverdueTasks(t.filter((x) => x.status !== "DONE" && x.due_at && new Date(x.due_at) < new Date()))).catch(() => setOverdueTasks([]));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Projects</h1>
      <Panel title="Проекты" subtitle="Нажмите на проект, чтобы увидеть причину задержки">
        {projects === null ? <p className="text-xs text-base-muted">Загрузка...</p> : projects.length === 0 ? <EmptyState text="Проектов нет." /> : (
          <div className="space-y-2">
            {projects.map((p) => (
              <div key={p.id} className="rounded border border-base-border bg-base-panel2">
                <button onClick={() => setExpanded(expanded === p.id ? null : p.id)} className="flex w-full items-center justify-between px-3 py-2 text-left text-xs">
                  <div>
                    <span className="mono text-base-muted">{p.code}</span> <span className="ml-1">{p.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-base-muted">до {p.deadline || "—"}</span>
                    <div className="h-1.5 w-24 overflow-hidden rounded bg-base-border">
                      <div className="h-full bg-accent" style={{ width: `${Math.round(p.progress * 100)}%` }} />
                    </div>
                    <span>{Math.round(p.progress * 100)}%</span>
                  </div>
                </button>
                {expanded === p.id && <DelayChainPanel projectId={p.id} />}
              </div>
            ))}
          </div>
        )}
      </Panel>
      <Panel title="Просроченные задачи">
        {overdueTasks === null ? <p className="text-xs text-base-muted">Загрузка...</p> : overdueTasks.length === 0 ? <EmptyState text="Просроченных задач нет." /> : (
          <ul className="space-y-1.5 text-xs">
            {overdueTasks.map((t) => (
              <li key={t.id} className="flex items-center justify-between rounded border border-base-border bg-base-panel2 px-3 py-2">
                <span>{t.title}</span>
                <span className="text-sev-high">{t.due_at ? new Date(t.due_at).toLocaleDateString("ru-RU") : ""}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
