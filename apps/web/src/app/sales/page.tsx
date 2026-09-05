"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface Deal {
  id: number; code: string; title: string; stage: string; amount: number; currency: string;
  probability: number; expected_close?: string | null; last_activity_at?: string | null;
}

const STAGE_LABELS: Record<string, string> = {
  NEW: "Новая", QUALIFIED: "Квалифицирована", PROPOSAL: "Предложение",
  NEGOTIATION: "Переговоры", WON: "Выиграна", LOST: "Проиграна",
};

export default function SalesPage() {
  const [deals, setDeals] = useState<Deal[] | null>(null);

  useEffect(() => {
    apiFetch<Deal[]>("/api/v1/deals").then(setDeals).catch(() => setDeals([]));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Sales</h1>
      <Panel title="Сделки">
        {deals === null ? (
          <p className="text-xs text-base-muted">Загрузка...</p>
        ) : deals.length === 0 ? (
          <EmptyState text="Сделок нет." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-base-border text-base-muted">
                  <th className="pb-2 font-normal">Код</th>
                  <th className="pb-2 font-normal">Название</th>
                  <th className="pb-2 font-normal">Стадия</th>
                  <th className="pb-2 font-normal">Сумма</th>
                  <th className="pb-2 font-normal">Вероятность</th>
                  <th className="pb-2 font-normal">Закрытие</th>
                </tr>
              </thead>
              <tbody>
                {deals.map((d) => (
                  <tr key={d.id} className="border-b border-base-border/50">
                    <td className="py-2 mono text-base-muted">{d.code}</td>
                    <td className="py-2">{d.title}</td>
                    <td className="py-2">{STAGE_LABELS[d.stage] || d.stage}</td>
                    <td className="py-2">{d.amount.toLocaleString("ru-RU")} {d.currency}</td>
                    <td className="py-2">{Math.round(d.probability * 100)}%</td>
                    <td className="py-2 text-base-muted">{d.expected_close || "—"}</td>
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
