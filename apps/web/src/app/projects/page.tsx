"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface Task { id: number; title: string; status: string; priority: string; due_at?: string | null }
interface Project { id: number; code: string; name: string; status: string; progress: number; deadline?: string | null }

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [overdueTasks, setOverdueTasks] = useState<Task[] | null>(null);

  useEffect(() => {
    apiFetch<Project[]>("/api/v1/projects").then(setProjects).catch(() => setProjects([]));
    apiFetch<Task[]>("/api/v1/tasks").then((t) => setOverdueTasks(t.filter((x) => x.status !== "DONE" && x.due_at && new Date(x.due_at) < new Date()))).catch(() => setOverdueTasks([]));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Projects</h1>
      <Panel title="Проекты">
        {projects === null ? <p className="text-xs text-base-muted">Загрузка...</p> : projects.length === 0 ? <EmptyState text="Проектов нет." /> : (
          <div className="space-y-2">
            {projects.map((p) => (
              <div key={p.id} className="flex items-center justify-between rounded border border-base-border bg-base-panel2 px-3 py-2 text-xs">
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
