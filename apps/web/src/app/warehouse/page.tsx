"use client";

import { Fragment, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface MaterialRow {
  id: number; sku: string; name: string; unit: string; min_stock: number;
  on_hand: number; reserved: number; available: number; last_movement_days?: number | null;
}

interface Movement {
  id: number; movement_type: string; quantity: number; occurred_at: string; performed_by: string; note: string;
}

interface WarehouseRow { id: number; code: string; name: string }

const MOVEMENT_LABELS: Record<string, string> = {
  RECEIPT: "Приход", CONSUMPTION: "Расход", TRANSFER_IN: "Перемещение (в)",
  TRANSFER_OUT: "Перемещение (из)", ADJUSTMENT: "Корректировка",
};

function MovementPanel({ material, warehouses, onRecorded }: { material: MaterialRow; warehouses: WarehouseRow[]; onRecorded: () => void }) {
  const [movements, setMovements] = useState<Movement[] | null>(null);
  const [type, setType] = useState("RECEIPT");
  const [qty, setQty] = useState("");
  const [warehouseId, setWarehouseId] = useState<number | "">(warehouses[0]?.id ?? "");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiFetch<Movement[]>(`/api/v1/inventory/materials/${material.id}/movements`).then(setMovements).catch(() => setMovements([]));
  }
  useEffect(load, [material.id]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const quantity = Number(qty);
    if (!quantity || quantity <= 0 || !warehouseId) return;
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/api/v1/inventory/materials/${material.id}/movements`, {
        method: "POST",
        body: JSON.stringify({ warehouse_id: warehouseId, movement_type: type, quantity, note }),
      });
      setQty("");
      setNote("");
      load();
      onRecorded();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border-t border-base-border bg-base-bg/40 p-3">
      <form onSubmit={submit} className="mb-3 flex flex-wrap items-end gap-2">
        <select value={type} onChange={(e) => setType(e.target.value)} className="rounded border border-base-border bg-base-panel2 px-2 py-1 text-xs outline-none focus:border-accent">
          {Object.entries(MOVEMENT_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input type="number" min="0" step="any" placeholder={`Кол-во, ${material.unit}`} value={qty} onChange={(e) => setQty(e.target.value)}
          className="w-28 rounded border border-base-border bg-base-panel2 px-2 py-1 text-xs outline-none focus:border-accent" />
        <select value={warehouseId} onChange={(e) => setWarehouseId(Number(e.target.value))} className="rounded border border-base-border bg-base-panel2 px-2 py-1 text-xs outline-none focus:border-accent">
          {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
        <input placeholder="Комментарий" value={note} onChange={(e) => setNote(e.target.value)}
          className="flex-1 min-w-32 rounded border border-base-border bg-base-panel2 px-2 py-1 text-xs outline-none focus:border-accent" />
        <button type="submit" disabled={busy} className="rounded bg-accent px-3 py-1 text-xs font-medium text-white hover:bg-accent-dim disabled:opacity-50">
          Записать
        </button>
      </form>
      {error && <p className="mb-2 text-xs text-sev-critical">{error}</p>}
      {movements === null ? <p className="text-xs text-base-muted">Загрузка...</p> : movements.length === 0 ? <EmptyState text="Движений ещё не было." /> : (
        <div className="space-y-1">
          {movements.map((mv) => (
            <div key={mv.id} className="flex items-center justify-between text-[11px] text-base-muted">
              <span>{MOVEMENT_LABELS[mv.movement_type] || mv.movement_type} — {mv.quantity.toLocaleString("ru-RU")} {material.unit}</span>
              <span>{new Date(mv.occurred_at).toLocaleString("ru-RU")} · {mv.performed_by}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function WarehousePage() {
  const [materials, setMaterials] = useState<MaterialRow[] | null>(null);
  const [warehouses, setWarehouses] = useState<WarehouseRow[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);

  function load() {
    apiFetch<MaterialRow[]>("/api/v1/inventory/materials").then(setMaterials).catch(() => setMaterials([]));
  }
  useEffect(() => {
    load();
    apiFetch<WarehouseRow[]>("/api/v1/inventory/warehouses").then(setWarehouses).catch(() => setWarehouses([]));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Warehouse</h1>
      <Panel title="Остатки материалов" subtitle="Нажмите на строку, чтобы записать движение или увидеть историю">
        {materials === null ? <p className="text-xs text-base-muted">Загрузка...</p> : materials.length === 0 ? <EmptyState text="Материалов нет." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-base-border text-base-muted">
                  <th className="pb-2 font-normal">SKU</th>
                  <th className="pb-2 font-normal">Материал</th>
                  <th className="pb-2 font-normal">В наличии</th>
                  <th className="pb-2 font-normal">Резерв</th>
                  <th className="pb-2 font-normal">Доступно</th>
                  <th className="pb-2 font-normal">Минимум</th>
                  <th className="pb-2 font-normal">Статус</th>
                </tr>
              </thead>
              <tbody>
                {materials.map((m) => {
                  const low = m.available < m.min_stock;
                  return (
                    <Fragment key={m.id}>
                      <tr className="cursor-pointer border-b border-base-border/50 hover:bg-base-panel2" onClick={() => setExpanded(expanded === m.id ? null : m.id)}>
                        <td className="py-2 mono text-base-muted">{m.sku}</td>
                        <td className="py-2">{m.name}</td>
                        <td className="py-2">{m.on_hand.toLocaleString("ru-RU")} {m.unit}</td>
                        <td className="py-2">{m.reserved.toLocaleString("ru-RU")} {m.unit}</td>
                        <td className="py-2">{m.available.toLocaleString("ru-RU")} {m.unit}</td>
                        <td className="py-2 text-base-muted">{m.min_stock.toLocaleString("ru-RU")} {m.unit}</td>
                        <td className="py-2">
                          {low ? <span className="text-sev-critical">Ниже минимума</span> : <span className="text-sev-low">Норма</span>}
                        </td>
                      </tr>
                      {expanded === m.id && (
                        <tr>
                          <td colSpan={7} className="p-0">
                            <MovementPanel material={m} warehouses={warehouses} onRecorded={load} />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
