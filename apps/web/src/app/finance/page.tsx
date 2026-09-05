"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface OrderMargin {
  order_id: number; order_number: string; revenue: number; planned_cost: number; actual_cost: number;
  cost_variance: number; cost_variance_pct?: number | null; planned_margin?: number | null; actual_margin?: number | null;
  categories: { category: string; label: string; planned: number; actual: number; variance: number; variance_pct?: number | null }[];
}
interface Overview { orders: OrderMargin[]; total_revenue: number; total_actual_cost: number }

export default function FinancePage() {
  const [data, setData] = useState<Overview | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    apiFetch<Overview>("/api/v1/finance/overview").then(setData).catch(() => setData({ orders: [], total_revenue: 0, total_actual_cost: 0 }));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Finance</h1>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded border border-base-border bg-base-panel p-4">
          <p className="text-[11px] uppercase tracking-wide text-base-muted">Выручка (заказы с затратами)</p>
          <p className="mt-1 text-lg font-semibold">{data ? data.total_revenue.toLocaleString("ru-RU") : "—"} ₸</p>
        </div>
        <div className="rounded border border-base-border bg-base-panel p-4">
          <p className="text-[11px] uppercase tracking-wide text-base-muted">Фактическая себестоимость</p>
          <p className="mt-1 text-lg font-semibold">{data ? data.total_actual_cost.toLocaleString("ru-RU") : "—"} ₸</p>
        </div>
      </div>
      <Panel title="Заказы: план / факт">
        {data === null ? <p className="text-xs text-base-muted">Загрузка...</p> : data.orders.length === 0 ? <EmptyState text="Нет заказов с данными по затратам." /> : (
          <div className="space-y-1.5">
            {data.orders.map((o) => (
              <div key={o.order_id} className="rounded border border-base-border bg-base-panel2 p-3 text-xs">
                <button className="flex w-full items-center justify-between" onClick={() => setExpanded(expanded === o.order_id ? null : o.order_id)}>
                  <span className="mono">{o.order_number}</span>
                  <span className="flex items-center gap-3">
                    <span>план {o.planned_cost.toLocaleString("ru-RU")}</span>
                    <span>факт {o.actual_cost.toLocaleString("ru-RU")}</span>
                    <span className={o.cost_variance > 0 ? "text-sev-high" : "text-sev-low"}>
                      {o.cost_variance > 0 ? "+" : ""}{o.cost_variance.toLocaleString("ru-RU")}
                      {o.cost_variance_pct != null ? ` (${o.cost_variance_pct > 0 ? "+" : ""}${o.cost_variance_pct.toFixed(1)}%)` : ""}
                    </span>
                  </span>
                </button>
                {expanded === o.order_id && (
                  <div className="mt-2 space-y-1 border-t border-base-border pt-2 text-base-muted">
                    {o.categories.map((c) => (
                      <div key={c.category} className="flex items-center justify-between">
                        <span>{c.label}</span>
                        <span>план {c.planned.toLocaleString("ru-RU")} → факт {c.actual.toLocaleString("ru-RU")}
                          {" "}<span className={c.variance > 0 ? "text-sev-high" : "text-sev-low"}>({c.variance > 0 ? "+" : ""}{c.variance.toLocaleString("ru-RU")})</span>
                        </span>
                      </div>
                    ))}
                    {o.planned_margin != null && o.actual_margin != null && (
                      <p className="pt-1 text-base-text">
                        Маржа: план {(o.planned_margin * 100).toFixed(1)}% → факт {(o.actual_margin * 100).toFixed(1)}%
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
