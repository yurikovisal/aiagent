"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";
import type { AgentStats, HealthCheck } from "@/lib/types";

interface Run { run_id: string; agent_id: string; intent?: string | null; status: string; started_at: string; duration_ms?: number | null; tool_calls_count: number; confidence?: number | null }
interface AgentManifest { id: string; name: string; risk_level: string; requires_approval: boolean }
interface AuditEntry {
  id: number; timestamp: string; user_email: string; agent: string; action: string;
  tool: string; execution_status: string; duration_ms: number;
}

export default function AIOperationsPage() {
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [agents, setAgents] = useState<AgentManifest[] | null>(null);
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const [audit, setAudit] = useState<AuditEntry[] | null>(null);

  useEffect(() => {
    apiFetch<AgentStats>("/api/v1/agents/stats").then(setStats).catch(() => {});
    apiFetch<Run[]>("/api/v1/agents/runs?limit=30").then(setRuns).catch(() => setRuns([]));
    apiFetch<AgentManifest[]>("/api/v1/agents").then(setAgents).catch(() => setAgents([]));
    apiFetch<AuditEntry[]>("/api/v1/audit-log?limit=40").then(setAudit).catch(() => setAudit([]));
    apiFetch<HealthCheck>("/api/v1/system/health").then(setHealth).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">AI Operations</h1>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          ["Активные запуски", stats?.active_runs],
          ["Завершено", stats?.completed_runs],
          ["Ошибки", stats?.failed_runs],
          ["Ожидают утверждения", stats?.pending_approvals],
          ["Вызовов инструментов", stats?.tool_calls_total],
          ["Вызовов LLM", stats?.llm_calls_total],
          ["Средняя длительность", stats ? `${stats.avg_duration_ms.toFixed(0)} мс` : undefined],
          ["Скорость генерации", stats ? `${stats.avg_tokens_per_sec.toFixed(1)} ток/с` : undefined],
        ].map(([label, value]) => (
          <div key={label as string} className="rounded border border-base-border bg-base-panel p-3">
            <p className="text-[10px] uppercase tracking-wide text-base-muted">{label}</p>
            <p className="mt-1 text-base font-semibold">{value ?? "—"}</p>
          </div>
        ))}
      </div>

      {health && (
        <Panel title="Состояние сервисов">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {Object.entries(health.checks).map(([name, check]) => (
              <div key={name} className="flex items-center gap-2 rounded border border-base-border bg-base-panel2 px-3 py-2 text-xs">
                <span className={`h-1.5 w-1.5 rounded-full ${check.status === "ok" ? "bg-sev-low" : check.status === "not_configured" ? "bg-base-muted" : "bg-sev-critical"}`} />
                <span className="capitalize">{name}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}

      <Panel title="Агенты">
        {agents === null ? <p className="text-xs text-base-muted">Загрузка...</p> : (
          <div className="flex flex-wrap gap-2">
            {agents.map((a) => (
              <span key={a.id} className="rounded border border-base-border bg-base-panel2 px-2.5 py-1 text-xs">
                {a.name} <span className="text-base-muted">· {a.risk_level}</span>
              </span>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Последние запуски">
        {runs === null ? <p className="text-xs text-base-muted">Загрузка...</p> : runs.length === 0 ? <EmptyState text="Запусков ещё не было." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-base-border text-base-muted">
                  <th className="pb-2 font-normal">Run</th>
                  <th className="pb-2 font-normal">Намерение</th>
                  <th className="pb-2 font-normal">Статус</th>
                  <th className="pb-2 font-normal">Инструменты</th>
                  <th className="pb-2 font-normal">Длительность</th>
                  <th className="pb-2 font-normal">Уверенность</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.run_id} className="border-b border-base-border/50">
                    <td className="py-1.5 mono text-base-muted">{r.run_id.slice(0, 8)}</td>
                    <td className="py-1.5">{r.intent || "—"}</td>
                    <td className="py-1.5">{r.status}</td>
                    <td className="py-1.5">{r.tool_calls_count}</td>
                    <td className="py-1.5">{r.duration_ms ?? "—"} мс</td>
                    <td className="py-1.5">{r.confidence != null ? `${Math.round(r.confidence * 100)}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="Audit Log" subtitle="Кто, когда и почему — каждое действие AI и решение об утверждении">
        {audit === null ? <p className="text-xs text-base-muted">Загрузка...</p> : audit.length === 0 ? <EmptyState text="Записей аудита ещё нет." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-base-border text-base-muted">
                  <th className="pb-2 font-normal">Время</th>
                  <th className="pb-2 font-normal">Пользователь</th>
                  <th className="pb-2 font-normal">Агент</th>
                  <th className="pb-2 font-normal">Действие</th>
                  <th className="pb-2 font-normal">Инструмент</th>
                  <th className="pb-2 font-normal">Статус</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((a) => (
                  <tr key={a.id} className="border-b border-base-border/50">
                    <td className="py-1.5 text-base-muted">{new Date(a.timestamp).toLocaleString("ru-RU")}</td>
                    <td className="py-1.5">{a.user_email || "—"}</td>
                    <td className="py-1.5">{a.agent || "—"}</td>
                    <td className="py-1.5">{a.action}</td>
                    <td className="py-1.5 mono text-base-muted">{a.tool || "—"}</td>
                    <td className="py-1.5">{a.execution_status || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
