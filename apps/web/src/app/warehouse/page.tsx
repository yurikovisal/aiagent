"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface MaterialRow {
  id: number; sku: string; name: string; unit: string; min_stock: number;
  on_hand: number; reserved: number; available: number; last_movement_days?: number | null;
}

export default function WarehousePage() {
  const [materials, setMaterials] = useState<MaterialRow[] | null>(null);

  useEffect(() => {
    apiFetch<MaterialRow[]>("/api/v1/inventory/materials").then(setMaterials).catch(() => setMaterials([]));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Warehouse</h1>
      <Panel title="Остатки материалов">
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
                    <tr key={m.id} className="border-b border-base-border/50">
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
