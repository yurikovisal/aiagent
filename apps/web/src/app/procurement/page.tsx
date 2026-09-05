"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface PurchaseRequest {
  id: number; number: string; quantity: number; unit: string; status: string; reason: string; needed_by?: string | null;
}
interface PurchaseOrder {
  id: number; number: string; quantity: number; unit: string; status: string; expected_at?: string | null;
}

const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Черновик", SUBMITTED: "Подана", APPROVED: "Одобрена", ORDERED: "Заказано",
  REJECTED: "Отклонена", CLOSED: "Закрыта", IN_TRANSIT: "В пути", RECEIVED: "Получено", PARTIAL: "Частично",
};

export default function ProcurementPage() {
  const [requests, setRequests] = useState<PurchaseRequest[] | null>(null);
  const [orders, setOrders] = useState<PurchaseOrder[] | null>(null);

  useEffect(() => {
    apiFetch<PurchaseRequest[]>("/api/v1/procurement/requests").then(setRequests).catch(() => setRequests([]));
    apiFetch<PurchaseOrder[]>("/api/v1/procurement/orders").then(setOrders).catch(() => setOrders([]));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Procurement</h1>
      <Panel title="Заявки на закупку">
        {requests === null ? <p className="text-xs text-base-muted">Загрузка...</p> : requests.length === 0 ? <EmptyState text="Заявок нет." /> : (
          <div className="space-y-1.5">
            {requests.map((r) => (
              <div key={r.id} className="rounded border border-base-border bg-base-panel2 px-3 py-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="mono">{r.number}</span>
                  <span>{STATUS_LABELS[r.status] || r.status}</span>
                </div>
                <p className="mt-1 text-base-muted">{r.quantity} {r.unit} — {r.reason}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <Panel title="Заказы поставщикам">
        {orders === null ? <p className="text-xs text-base-muted">Загрузка...</p> : orders.length === 0 ? <EmptyState text="Заказов поставщикам нет." /> : (
          <div className="space-y-1.5">
            {orders.map((o) => (
              <div key={o.id} className="flex items-center justify-between rounded border border-base-border bg-base-panel2 px-3 py-2 text-xs">
                <span className="mono">{o.number}</span>
                <span>{o.quantity} {o.unit}</span>
                <span className="text-base-muted">ETA {o.expected_at || "—"}</span>
                <span>{STATUS_LABELS[o.status] || o.status}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
