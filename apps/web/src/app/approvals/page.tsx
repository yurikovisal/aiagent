"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";
import type { ApprovalItem } from "@/lib/types";

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalItem[] | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [comment, setComment] = useState<Record<number, string>>({});
  const [tab, setTab] = useState<"PENDING" | "ALL">("PENDING");

  function load() {
    apiFetch<ApprovalItem[]>(tab === "PENDING" ? "/api/v1/approvals?status=PENDING" : "/api/v1/approvals")
      .then(setItems).catch(() => setItems([]));
  }
  useEffect(load, [tab]);

  async function decide(id: number, decision: "APPROVED" | "REJECTED") {
    setBusyId(id);
    try {
      await apiFetch(`/api/v1/approvals/${id}/decide`, {
        method: "POST",
        body: JSON.stringify({ decision, comment: comment[id] || "" }),
      });
      load();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Approvals</h1>
        <div className="flex gap-1 rounded border border-base-border p-0.5 text-xs">
          {(["PENDING", "ALL"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`rounded px-2.5 py-1 ${tab === t ? "bg-accent/15 text-accent" : "text-base-muted"}`}>
              {t === "PENDING" ? "Ожидают" : "Все"}
            </button>
          ))}
        </div>
      </div>
      <Panel>
        {items === null ? <p className="text-xs text-base-muted">Загрузка...</p> : items.length === 0 ? <EmptyState text="Нет заявок на утверждение." /> : (
          <div className="space-y-3">
            {items.map((a) => (
              <div key={a.id} className="rounded border border-base-border bg-base-panel2 p-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{a.title}</span>
                  <span className={`rounded px-1.5 py-0.5 text-[10px] uppercase ${
                    a.status === "PENDING" ? "bg-sev-medium/15 text-sev-medium" :
                    a.status === "EXECUTED" ? "bg-sev-low/15 text-sev-low" :
                    a.status === "REJECTED" ? "bg-sev-critical/15 text-sev-critical" : "bg-base-border text-base-muted"
                  }`}>{a.status}</span>
                </div>
                <p className="mt-1 text-base-muted">{a.description}</p>
                <p className="mt-1 text-[11px] text-base-muted">Предложил: {a.proposed_by_agent} · Риск: {a.risk}</p>
                {a.status === "PENDING" ? (
                  <div className="mt-2 flex items-center gap-2">
                    <input
                      placeholder="Комментарий (необязательно)"
                      value={comment[a.id] || ""}
                      onChange={(e) => setComment((c) => ({ ...c, [a.id]: e.target.value }))}
                      className="flex-1 rounded border border-base-border bg-base-panel px-2 py-1 text-xs outline-none focus:border-accent"
                    />
                    <button disabled={busyId === a.id} onClick={() => decide(a.id, "APPROVED")}
                      className="rounded bg-accent px-3 py-1 font-medium text-white hover:bg-accent-dim disabled:opacity-50">
                      Одобрить
                    </button>
                    <button disabled={busyId === a.id} onClick={() => decide(a.id, "REJECTED")}
                      className="rounded border border-base-border px-3 py-1 hover:border-sev-critical hover:text-sev-critical disabled:opacity-50">
                      Отклонить
                    </button>
                  </div>
                ) : (
                  <p className="mt-2 text-[11px] text-base-muted">
                    {a.decision_comment && <>Комментарий: {a.decision_comment} · </>}
                    {a.decided_at && new Date(a.decided_at).toLocaleString("ru-RU")}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
