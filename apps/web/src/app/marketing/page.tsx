"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface Campaign {
  id: number; name: string; channel: string; status: string; budget: number; spent: number; leads_generated: number;
}

interface Lead {
  id: number; name: string; company: string; source: string; status: string;
}

interface ContentItem {
  id: number; title: string; channel: string; status: string; body: string;
}

const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Черновик", REVIEW: "На проверке", APPROVED: "Утверждено", PUBLISHED: "Опубликовано",
};
const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-base-border text-base-muted", REVIEW: "bg-sev-medium/15 text-sev-medium",
  APPROVED: "bg-accent/15 text-accent", PUBLISHED: "bg-sev-low/15 text-sev-low",
};

function ContentSection() {
  const [items, setItems] = useState<ContentItem[] | null>(null);
  const [title, setTitle] = useState("");
  const [channel, setChannel] = useState("сайт");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function load() {
    apiFetch<ContentItem[]>("/api/v1/marketing/content").then(setItems).catch(() => setItems([]));
  }
  useEffect(load, []);

  async function createDraft(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await apiFetch("/api/v1/marketing/content", { method: "POST", body: JSON.stringify({ title, channel }) });
    setTitle("");
    load();
  }

  async function proposePublish(item: ContentItem) {
    setBusyId(item.id);
    setMessage(null);
    try {
      await apiFetch(`/api/v1/marketing/content/${item.id}/propose-publish`, { method: "POST" });
      setMessage(`Публикация «${item.title}» предложена — ожидает утверждения в разделе Approvals.`);
      load();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Panel
      title="Контент"
      subtitle="§21 — публикация не выполняется автоматически: каждая публикация проходит через Approval Engine"
    >
      <form onSubmit={createDraft} className="mb-3 flex flex-wrap items-end gap-2">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Заголовок материала"
          className="flex-1 min-w-40 rounded border border-base-border bg-base-panel2 px-2 py-1 text-xs outline-none focus:border-accent" />
        <input value={channel} onChange={(e) => setChannel(e.target.value)} placeholder="Канал"
          className="w-32 rounded border border-base-border bg-base-panel2 px-2 py-1 text-xs outline-none focus:border-accent" />
        <button type="submit" className="rounded bg-accent px-3 py-1 text-xs font-medium text-white hover:bg-accent-dim">
          Создать черновик
        </button>
      </form>
      {message && <p className="mb-2 text-xs text-base-muted">{message}</p>}
      {items === null ? <p className="text-xs text-base-muted">Загрузка...</p> : items.length === 0 ? <EmptyState text="Материалов нет." /> : (
        <div className="space-y-1.5">
          {items.map((item) => (
            <div key={item.id} className="flex items-center justify-between rounded border border-base-border bg-base-panel2 p-2.5 text-xs">
              <div>
                <span className="font-medium">{item.title}</span>
                <span className="ml-2 text-base-muted">{item.channel}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`rounded px-1.5 py-0.5 text-[10px] ${STATUS_COLORS[item.status] || ""}`}>
                  {STATUS_LABELS[item.status] || item.status}
                </span>
                {item.status !== "PUBLISHED" && (
                  <button
                    disabled={busyId === item.id}
                    onClick={() => proposePublish(item)}
                    className="rounded border border-base-border px-2 py-0.5 text-[11px] hover:border-accent hover:text-accent disabled:opacity-50"
                  >
                    Предложить публикацию
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

export default function MarketingPage() {
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [leads, setLeads] = useState<Lead[] | null>(null);

  useEffect(() => {
    apiFetch<Campaign[]>("/api/v1/marketing/campaigns").then(setCampaigns).catch(() => setCampaigns([]));
    apiFetch<Lead[]>("/api/v1/marketing/leads").then(setLeads).catch(() => setLeads([]));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Marketing</h1>
      <Panel title="Кампании">
        {campaigns === null ? <p className="text-xs text-base-muted">Загрузка...</p> : campaigns.length === 0 ? <EmptyState text="Кампаний нет." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-base-border text-base-muted">
                  <th className="pb-2 font-normal">Название</th>
                  <th className="pb-2 font-normal">Канал</th>
                  <th className="pb-2 font-normal">Статус</th>
                  <th className="pb-2 font-normal">Бюджет</th>
                  <th className="pb-2 font-normal">Потрачено</th>
                  <th className="pb-2 font-normal">Лиды</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c) => (
                  <tr key={c.id} className="border-b border-base-border/50">
                    <td className="py-2">{c.name}</td>
                    <td className="py-2 text-base-muted">{c.channel}</td>
                    <td className="py-2">{c.status}</td>
                    <td className="py-2">{c.budget.toLocaleString("ru-RU")}</td>
                    <td className="py-2">{c.spent.toLocaleString("ru-RU")}</td>
                    <td className="py-2">{c.leads_generated}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <Panel title="Лиды" subtitle={leads ? `Всего: ${leads.length}` : undefined}>
        {leads === null ? <p className="text-xs text-base-muted">Загрузка...</p> : leads.length === 0 ? <EmptyState text="Лидов нет." /> : (
          <div className="space-y-1">
            {leads.slice(0, 20).map((l) => (
              <div key={l.id} className="flex items-center justify-between text-xs">
                <span>{l.name} <span className="text-base-muted">— {l.company}</span></span>
                <span className="text-base-muted">{l.source} · {l.status}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <ContentSection />
    </div>
  );
}
