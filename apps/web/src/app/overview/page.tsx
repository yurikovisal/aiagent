"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Panel, EmptyState } from "@/components/Panel";
import { SeverityBadge } from "@/components/SeverityBadge";
import type { ExecutiveBrief, RiskItem } from "@/lib/types";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return "Доброй ночи";
  if (h < 12) return "Доброе утро";
  if (h < 18) return "Добрый день";
  return "Добрый вечер";
}

interface Changes {
  hours: number;
  total: number;
  by_type: Record<string, { count: number; items: Record<string, unknown>[] }>;
}

const EVENT_LABELS: Record<string, string> = {
  ORDER_CREATED: "Заказы созданы", ORDER_UPDATED: "Заказы обновлены", ORDER_DELAYED: "Заказы задержаны",
  DEAL_CREATED: "Сделки созданы", DEAL_STALLED: "Сделки зависли",
  TASK_CREATED: "Задачи созданы", TASK_OVERDUE: "Задачи просрочены", TASK_COMPLETED: "Задачи завершены",
  MATERIAL_RECEIVED: "Приход материалов", MATERIAL_RESERVED: "Резерв материалов",
  MATERIAL_CONSUMED: "Расход материалов", MATERIAL_LOW: "Материалы на исходе",
  PURCHASE_REQUEST_CREATED: "Заявки на закупку", PURCHASE_ORDER_CREATED: "Заказы поставщикам",
  PRODUCTION_STARTED: "Производство начато", PRODUCTION_COMPLETED: "Производство завершено",
  PRODUCTION_DELAYED: "Производство задержано",
  DOCUMENT_ADDED: "Документы добавлены", DOCUMENT_EXPIRES: "Истекают документы",
  PAYMENT_RECEIVED: "Платежи получены", PAYMENT_OVERDUE: "Платежи просрочены",
  ANOMALY_DETECTED: "Аномалии", RISK_DETECTED: "Риски обнаружены",
};

export default function OverviewPage() {
  const { user } = useAuth();
  const [brief, setBrief] = useState<ExecutiveBrief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [changes, setChanges] = useState<Changes | null>(null);

  useEffect(() => {
    apiFetch<ExecutiveBrief>("/api/v1/meza/brief").then(setBrief).catch((e) => setError(e.message));
    apiFetch<Changes>("/api/v1/meza/changes?hours=24").then(setChanges).catch(() => setChanges(null));
  }, []);

  const critical = (brief?.sections.critical as RiskItem[]) || [];
  const high = (brief?.sections.high_priority as RiskItem[]) || [];
  const decisions = (brief?.sections.decisions_required as Record<string, unknown>[]) || [];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">
          {greeting()}{user ? `, ${user.full_name.split(" ")[0] || user.email}` : ""}.
        </h1>
        {brief ? (
          <p className="mt-1 text-sm text-base-muted">{brief.executive_summary}</p>
        ) : error ? (
          <p className="mt-1 text-sm text-sev-critical">Не удалось загрузить сводку: {error}</p>
        ) : (
          <p className="mt-1 text-sm text-base-muted">Загрузка сводки...</p>
        )}
      </div>

      {(critical.length > 0 || high.length > 0) && (
        <Panel title="Needs Attention">
          <div className="space-y-2">
            {[...critical, ...high].map((r) => (
              <div key={r.id} className="rounded border border-base-border bg-base-panel2 p-3">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={r.severity} />
                  <span className="text-sm font-medium">{r.title}</span>
                </div>
                <div className="mt-1.5 grid grid-cols-1 gap-x-6 gap-y-1 text-xs text-base-muted sm:grid-cols-2">
                  <p><span className="text-base-text/80">Причина: </span>{r.cause}</p>
                  <p><span className="text-base-text/80">Влияние: </span>{r.impact}</p>
                </div>
                {r.recommendation && (
                  <p className="mt-1.5 text-xs">
                    <span className="text-accent">Рекомендовано: </span>{r.recommendation}
                  </p>
                )}
              </div>
            ))}
          </div>
        </Panel>
      )}

      {decisions.length > 0 && (
        <Panel title="Decisions Required" subtitle="Ожидают вашего утверждения">
          <div className="space-y-1.5">
            {decisions.map((d) => (
              <div key={String(d.id)} className="flex items-center justify-between rounded border border-base-border bg-base-panel2 px-3 py-2 text-xs">
                <span>{String(d.title)}</span>
                <a href="/approvals" className="text-accent hover:underline">Перейти →</a>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {brief && critical.length === 0 && high.length === 0 && decisions.length === 0 && (
        <Panel><EmptyState text="Критических событий нет. Хорошего дня." /></Panel>
      )}

      {changes && changes.total > 0 && (
        <Panel title="What Changed" subtitle={`За последние ${changes.hours} ч.`}>
          <div className="flex flex-wrap gap-2">
            {Object.entries(changes.by_type).map(([type, info]) => (
              <span key={type} className="rounded border border-base-border bg-base-panel2 px-2.5 py-1 text-xs">
                {EVENT_LABELS[type] || type} <span className="text-accent">{info.count}</span>
              </span>
            ))}
          </div>
        </Panel>
      )}

      <p className="text-center text-[11px] text-base-muted">
        Нажмите ⌘K или используйте Ask MEZA сверху, чтобы задать вопрос о состоянии компании.
      </p>
    </div>
  );
}
