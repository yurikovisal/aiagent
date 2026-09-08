"use client";

import { useRef, useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface InboxItem {
  id: number;
  filename: string;
  classification: string;
  confidence: number;
  proposal: { action: string; summary: string; confidence: number };
  status: string;
  created_at: string;
}

const ACTION_LABELS: Record<string, string> = {
  create_warehouse_receipt: "Похоже на приход товара",
  create_document: "Добавить как документ",
  review_manually: "Требует ручной проверки",
};

export default function InboxPage() {
  const [items, setItems] = useState<InboxItem[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  function load() {
    apiFetch<InboxItem[]>("/api/v1/inbox").then(setItems).catch(() => setItems([]));
  }
  useEffect(load, []);

  async function handleDrop(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      await apiFetch("/api/v1/inbox/drop", { method: "POST", body: fd });
      load();
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function accept(id: number) {
    await apiFetch(`/api/v1/inbox/${id}/accept`, { method: "POST" });
    load();
  }
  async function reject(id: number) {
    await apiFetch(`/api/v1/inbox/${id}/reject`, { method: "POST" });
    load();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">MEZA Inbox</h1>
          <p className="mt-1 text-xs text-base-muted">Загрузите произвольный файл — MEZA классифицирует его и предложит действие. Ничего не создаётся без вашего подтверждения.</p>
        </div>
        <label className="cursor-pointer rounded border border-base-border bg-base-panel2 px-3 py-1.5 text-xs hover:border-accent/50">
          {uploading ? "Обработка..." : "+ Загрузить файл"}
          <input ref={fileRef} type="file" className="hidden" onChange={handleDrop} />
        </label>
      </div>
      <Panel title="Необработанные">
        {items === null ? <p className="text-xs text-base-muted">Загрузка...</p> : items.filter((i) => i.status !== "ACCEPTED" && i.status !== "REJECTED").length === 0 ? (
          <EmptyState text="Нет новых файлов." />
        ) : (
          <div className="space-y-2">
            {items.filter((i) => i.status !== "ACCEPTED" && i.status !== "REJECTED").map((item) => (
              <div key={item.id} className="rounded border border-base-border bg-base-panel2 p-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{item.filename}</span>
                  <span className="text-base-muted">{item.classification}</span>
                </div>
                <p className="mt-1 text-accent">{ACTION_LABELS[item.proposal?.action] || item.proposal?.summary}</p>
                <p className="text-base-muted">{item.proposal?.summary}</p>
                <div className="mt-2 flex gap-2">
                  <button onClick={() => accept(item.id)} className="rounded bg-accent px-3 py-1 font-medium text-white hover:bg-accent-dim">Принять</button>
                  <button onClick={() => reject(item.id)} className="rounded border border-base-border px-3 py-1 hover:border-sev-critical hover:text-sev-critical">Отклонить</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <Panel title="Обработанные" subtitle="История принятых/отклонённых файлов">
        {items === null ? null : items.filter((i) => i.status === "ACCEPTED" || i.status === "REJECTED").length === 0 ? (
          <EmptyState text="Пока ничего не обработано." />
        ) : (
          <div className="space-y-1">
            {items.filter((i) => i.status === "ACCEPTED" || i.status === "REJECTED").map((item) => (
              <div key={item.id} className="flex items-center justify-between rounded border border-base-border bg-base-panel2 px-3 py-1.5 text-xs">
                <span>{item.filename}</span>
                <span className={item.status === "ACCEPTED" ? "text-sev-low" : "text-sev-critical"}>{item.status}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
