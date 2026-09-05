"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface Doc { id: number; title: string; doc_type: string; created_at: string; expires_on?: string | null }

const TYPE_LABELS: Record<string, string> = {
  CONTRACT: "Договор", INVOICE: "Счёт", COMMERCIAL_OFFER: "КП", SPECIFICATION: "Спецификация",
  INSTRUCTION: "Инструкция", REGULATION: "Регламент", TECH_DOC: "Техдокумент", REPORT: "Отчёт", UNCLASSIFIED: "Не классифицирован",
};

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  function load() {
    apiFetch<Doc[]>("/api/v1/documents").then(setDocs).catch(() => setDocs([]));
  }
  useEffect(load, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      await apiFetch("/api/v1/documents/upload", { method: "POST", body: fd });
      load();
    } catch {
      // handled by global error boundary in a real UI; keep minimal here
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Documents</h1>
        <label className="cursor-pointer rounded border border-base-border bg-base-panel2 px-3 py-1.5 text-xs hover:border-accent/50">
          {uploading ? "Загрузка..." : "+ Загрузить документ"}
          <input ref={fileRef} type="file" className="hidden" onChange={handleUpload} accept=".pdf,.docx,.xlsx,.txt,.csv,.png,.jpg,.jpeg" />
        </label>
      </div>
      <Panel title="Документы">
        {docs === null ? <p className="text-xs text-base-muted">Загрузка...</p> : docs.length === 0 ? <EmptyState text="Документов нет." /> : (
          <div className="space-y-1.5">
            {docs.map((d) => (
              <div key={d.id} className="flex items-center justify-between rounded border border-base-border bg-base-panel2 px-3 py-2 text-xs">
                <span>{d.title}</span>
                <span className="flex items-center gap-3 text-base-muted">
                  <span>{TYPE_LABELS[d.doc_type] || d.doc_type}</span>
                  {d.expires_on && <span className="text-sev-medium">истекает {d.expires_on}</span>}
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
