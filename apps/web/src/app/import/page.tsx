"use client";

import { useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel } from "@/components/Panel";

interface ImportJob {
  id: number;
  filename: string;
  file_type: string;
  target_entity: string;
  detected_columns: string[];
  suggested_mapping: Record<string, string>;
  mapping: Record<string, string>;
  preview: Record<string, unknown>[];
  validation: { valid: boolean; errors: { row: number; field: string; error: string }[]; row_count: number } | null;
  row_count: number;
  imported_count: number;
  status: string;
}

const TARGET_FIELDS: Record<string, string[]> = {
  materials: ["sku", "name", "unit", "category", "min_stock", "reorder_quantity", "lead_time_days", "unit_cost"],
  suppliers: ["name", "category", "contact", "avg_lead_time_days"],
};

export default function ImportPage() {
  const [target, setTarget] = useState("materials");
  const [job, setJob] = useState<ImportJob | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("target_entity", target);
    try {
      const result = await apiFetch<ImportJob>("/api/v1/imports/upload", { method: "POST", body: fd });
      setJob(result);
      setMapping(result.mapping || {});
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function saveMapping() {
    if (!job) return;
    setBusy(true);
    try {
      const result = await apiFetch<ImportJob>(`/api/v1/imports/${job.id}/mapping`, { method: "POST", body: JSON.stringify({ mapping }) });
      setJob(result);
    } finally {
      setBusy(false);
    }
  }

  async function confirmImport() {
    if (!job) return;
    setBusy(true);
    try {
      const result = await apiFetch<ImportJob>(`/api/v1/imports/${job.id}/confirm`, { method: "POST" });
      setJob(result);
    } finally {
      setBusy(false);
    }
  }

  const fields = TARGET_FIELDS[target] || [];

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Import Center</h1>
      <Panel title="1. Загрузить файл" subtitle="CSV, XLSX или JSON">
        <div className="flex items-center gap-3">
          <select value={target} onChange={(e) => { setTarget(e.target.value); setJob(null); }}
            className="rounded border border-base-border bg-base-panel2 px-2 py-1.5 text-xs outline-none focus:border-accent">
            <option value="materials">Материалы</option>
            <option value="suppliers">Поставщики</option>
          </select>
          <label className="cursor-pointer rounded border border-base-border bg-base-panel2 px-3 py-1.5 text-xs hover:border-accent/50">
            {busy ? "Обработка..." : "Выбрать файл"}
            <input ref={fileRef} type="file" accept=".csv,.xlsx,.json" className="hidden" onChange={handleUpload} />
          </label>
        </div>
      </Panel>

      {job && (
        <>
          <Panel title="2. Сопоставление колонок" subtitle={`Обнаружено колонок: ${job.detected_columns.length}, строк: ${job.row_count}`}>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {fields.map((field) => (
                <label key={field} className="text-xs">
                  <span className="mb-1 block text-base-muted">{field}</span>
                  <select
                    value={mapping[field] || ""}
                    onChange={(e) => setMapping({ ...mapping, [field]: e.target.value })}
                    className="w-full rounded border border-base-border bg-base-panel2 px-2 py-1 outline-none focus:border-accent"
                  >
                    <option value="">—</option>
                    {job.detected_columns.map((col) => <option key={col} value={col}>{col}</option>)}
                  </select>
                </label>
              ))}
            </div>
            <button onClick={saveMapping} disabled={busy} className="mt-3 rounded bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-dim disabled:opacity-50">
              Проверить сопоставление
            </button>
          </Panel>

          <Panel title="3. Предпросмотр" subtitle="Первые строки файла">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-base-border text-base-muted">
                    {job.detected_columns.map((c) => <th key={c} className="pb-2 pr-4 font-normal">{c}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {job.preview.map((row, i) => (
                    <tr key={i} className="border-b border-base-border/50">
                      {job.detected_columns.map((c) => <td key={c} className="py-1.5 pr-4">{String(row[c] ?? "")}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="4. Валидация и импорт">
            {job.validation && !job.validation.valid && (
              <div className="mb-2 space-y-1 text-xs text-sev-critical">
                {job.validation.errors.slice(0, 10).map((e, i) => (
                  <p key={i}>Строка {e.row}: поле &laquo;{e.field}&raquo; — {e.error}</p>
                ))}
              </div>
            )}
            <div className="flex items-center gap-3">
              <span className="text-xs text-base-muted">Статус: {job.status}</span>
              {job.status === "IMPORTED" ? (
                <span className="text-xs text-sev-low">Импортировано записей: {job.imported_count}</span>
              ) : (
                <button
                  onClick={confirmImport}
                  disabled={busy || job.status !== "VALIDATED"}
                  className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-dim disabled:opacity-50"
                >
                  Подтвердить импорт
                </button>
              )}
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
