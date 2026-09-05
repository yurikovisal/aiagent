"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface ProductionOrder {
  id: number; number: string; order_id: number; status: string; progress: number;
  planned_start?: string | null; planned_end?: string | null; notes: string;
}
interface Stage {
  id: number; name: string; status: string; sequence: number;
  planned_start?: string | null; planned_end?: string | null; blocked_reason: string;
}
interface Detail {
  production_order: ProductionOrder; order: { number: string; deadline?: string | null } | null;
  stages: Stage[];
  impact: { deadline_missed_by_days?: number | null; new_completion?: string | null; chain: { stage: string; delay_days: number; reason: string }[] } | null;
}

const STATUS_LABELS: Record<string, string> = {
  PLANNED: "Запланировано", READY: "Готово к старту", IN_PROGRESS: "В работе",
  BLOCKED: "Заблокировано", DONE: "Завершено", COMPLETED: "Завершено", CANCELLED: "Отменено",
};

export default function ProductionPage() {
  const [orders, setOrders] = useState<ProductionOrder[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);

  useEffect(() => {
    apiFetch<ProductionOrder[]>("/api/v1/production/orders").then((os) => {
      setOrders(os);
      if (os.length) setSelected(os[0].id);
    }).catch(() => setOrders([]));
  }, []);

  useEffect(() => {
    if (selected == null) return;
    apiFetch<Detail>(`/api/v1/production/orders/${selected}`).then(setDetail).catch(() => setDetail(null));
  }, [selected]);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="lg:col-span-1">
        <Panel title="Производственные заказы">
          {orders === null ? <p className="text-xs text-base-muted">Загрузка...</p> : orders.length === 0 ? <EmptyState text="Нет производственных заказов." /> : (
            <div className="space-y-1.5">
              {orders.map((o) => (
                <button
                  key={o.id}
                  onClick={() => setSelected(o.id)}
                  className={`block w-full rounded border px-3 py-2 text-left text-xs transition ${selected === o.id ? "border-accent bg-accent/10" : "border-base-border bg-base-panel2 hover:border-accent/40"}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="mono">{o.number}</span>
                    <span className={o.status === "BLOCKED" ? "text-sev-critical" : "text-base-muted"}>{STATUS_LABELS[o.status] || o.status}</span>
                  </div>
                  <div className="mt-1 h-1 overflow-hidden rounded bg-base-border">
                    <div className="h-full bg-accent" style={{ width: `${Math.round(o.progress * 100)}%` }} />
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </div>
      <div className="space-y-6 lg:col-span-2">
        {detail && (
          <>
            <Panel title={`Этапы — ${detail.production_order.number}`} subtitle={detail.order ? `Заказ ${detail.order.number}, срок ${detail.order.deadline || "—"}` : undefined}>
              <div className="space-y-1.5">
                {detail.stages.map((s) => (
                  <div key={s.id} className="flex items-center justify-between rounded border border-base-border bg-base-panel2 px-3 py-2 text-xs">
                    <div className="flex items-center gap-2">
                      <span className={`h-1.5 w-1.5 rounded-full ${s.status === "BLOCKED" ? "bg-sev-critical" : s.status === "DONE" ? "bg-sev-low" : s.status === "IN_PROGRESS" ? "bg-accent" : "bg-base-muted"}`} />
                      <span>{s.sequence}. {s.name}</span>
                    </div>
                    <div className="flex items-center gap-3 text-base-muted">
                      <span>{STATUS_LABELS[s.status] || s.status}</span>
                      <span>{s.planned_start} → {s.planned_end}</span>
                    </div>
                  </div>
                ))}
                {detail.stages.some((s) => s.status === "BLOCKED") && (
                  <p className="mt-1 text-xs text-sev-critical">
                    {detail.stages.find((s) => s.status === "BLOCKED")?.blocked_reason}
                  </p>
                )}
              </div>
            </Panel>
            {detail.impact && (
              <Panel title="Причинно-следственная цепочка" subtitle="Влияние текущей задержки на последующие этапы">
                <div className="space-y-1">
                  {detail.impact.chain.map((c, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="w-40 shrink-0">{c.stage}</span>
                      <span className="text-sev-high">+{c.delay_days} дн.</span>
                      <span className="text-base-muted">{c.reason}</span>
                    </div>
                  ))}
                </div>
                {detail.impact.deadline_missed_by_days ? (
                  <p className="mt-2 border-t border-base-border pt-2 text-xs text-sev-critical">
                    Итоговая задержка приведёт к срыву дедлайна на {detail.impact.deadline_missed_by_days} дн. (новое завершение: {detail.impact.new_completion}).
                  </p>
                ) : null}
              </Panel>
            )}
          </>
        )}
      </div>
    </div>
  );
}
