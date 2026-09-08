"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Panel, EmptyState } from "@/components/Panel";
import { apiFetch, ApiError } from "@/lib/api";

interface RiskRuleRow {
  id: number;
  rule_key: string;
  name: string;
  domain: string;
  enabled: boolean;
  params: Record<string, number | string>;
}

interface MemoryRow {
  id: number;
  key: string;
  content: string;
  category: string;
  confirmed: boolean;
  created_at: string;
}

function ChangePasswordSection() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      await apiFetch("/api/v1/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: current, new_password: next }) });
      setMessage({ text: "Пароль изменён.", ok: true });
      setCurrent("");
      setNext("");
    } catch (err) {
      setMessage({ text: err instanceof ApiError ? err.message : String(err), ok: false });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title="Сменить пароль">
      <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
        <label className="text-xs">
          <span className="mb-1 block text-base-muted">Текущий пароль</span>
          <input required type="password" value={current} onChange={(e) => setCurrent(e.target.value)}
            className="rounded border border-base-border bg-base-panel2 px-2 py-1.5 outline-none focus:border-accent" />
        </label>
        <label className="text-xs">
          <span className="mb-1 block text-base-muted">Новый пароль</span>
          <input required type="password" minLength={8} value={next} onChange={(e) => setNext(e.target.value)}
            className="rounded border border-base-border bg-base-panel2 px-2 py-1.5 outline-none focus:border-accent" />
        </label>
        <button type="submit" disabled={busy} className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-dim disabled:opacity-50">
          Сохранить
        </button>
      </form>
      {message && <p className={`mt-2 text-xs ${message.ok ? "text-sev-low" : "text-sev-critical"}`}>{message.text}</p>}
    </Panel>
  );
}

function RiskRulesSection() {
  const [rules, setRules] = useState<RiskRuleRow[] | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  function load() {
    apiFetch<RiskRuleRow[]>("/api/v1/risks/rules").then(setRules).catch(() => setRules([]));
  }
  useEffect(load, []);

  async function toggle(rule: RiskRuleRow) {
    setBusyKey(rule.rule_key);
    try {
      await apiFetch(`/api/v1/risks/rules/${rule.rule_key}`, { method: "PATCH", body: JSON.stringify({ enabled: !rule.enabled }) });
      load();
    } finally {
      setBusyKey(null);
    }
  }

  async function updateParam(rule: RiskRuleRow, key: string, value: string) {
    const num = Number(value);
    if (Number.isNaN(num)) return;
    setBusyKey(rule.rule_key);
    try {
      await apiFetch(`/api/v1/risks/rules/${rule.rule_key}`, { method: "PATCH", body: JSON.stringify({ params: { [key]: num } }) });
      load();
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <Panel title="Risk Engine — пороги правил" subtitle="Конфигурация, не код (§38) — меняются без деплоя">
      {rules === null ? <p className="text-xs text-base-muted">Загрузка...</p> : rules.length === 0 ? <EmptyState text="Правил нет." /> : (
        <div className="space-y-2">
          {rules.map((r) => (
            <div key={r.rule_key} className="rounded border border-base-border bg-base-panel2 p-2.5 text-xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium">{r.name}</span>
                  <span className="ml-2 text-base-muted">{r.domain}</span>
                </div>
                <button
                  disabled={busyKey === r.rule_key}
                  onClick={() => toggle(r)}
                  className={`rounded px-2 py-0.5 text-[11px] ${r.enabled ? "bg-sev-low/15 text-sev-low" : "bg-base-border text-base-muted"}`}
                >
                  {r.enabled ? "включено" : "выключено"}
                </button>
              </div>
              {Object.keys(r.params || {}).length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-3">
                  {Object.entries(r.params).map(([k, v]) => (
                    <label key={k} className="flex items-center gap-1.5 text-[11px] text-base-muted">
                      {k}
                      <input
                        type="number"
                        defaultValue={v as number}
                        onBlur={(e) => e.target.value !== String(v) && updateParam(r, k, e.target.value)}
                        className="w-20 rounded border border-base-border bg-base-panel px-1.5 py-0.5 text-base-text outline-none focus:border-accent"
                      />
                    </label>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function BusinessMemorySection() {
  const [rows, setRows] = useState<MemoryRow[] | null>(null);
  const [key, setKey] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("general");
  const [busy, setBusy] = useState(false);

  function load() {
    apiFetch<MemoryRow[]>("/api/v1/memory").then(setRows).catch(() => setRows([]));
  }
  useEffect(load, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!key.trim() || !content.trim()) return;
    setBusy(true);
    try {
      await apiFetch("/api/v1/memory", { method: "POST", body: JSON.stringify({ key, content, category }) });
      setKey("");
      setContent("");
      load();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    await apiFetch(`/api/v1/memory/${id}`, { method: "DELETE" });
    load();
  }

  return (
    <Panel title="Business Memory" subtitle="Подтверждённые знания о компании — агенты используют как контекст, никогда как источник цифр">
      <form onSubmit={add} className="mb-3 space-y-1.5 rounded border border-base-border bg-base-panel2 p-2.5">
        <div className="flex gap-1.5">
          <input value={key} onChange={(e) => setKey(e.target.value)} placeholder="Заголовок факта"
            className="flex-1 rounded border border-base-border bg-base-panel px-2 py-1 text-xs outline-none focus:border-accent" />
          <select value={category} onChange={(e) => setCategory(e.target.value)}
            className="rounded border border-base-border bg-base-panel px-2 py-1 text-xs outline-none focus:border-accent">
            <option value="general">general</option>
            <option value="customer">customer</option>
            <option value="supplier">supplier</option>
            <option value="policy">policy</option>
          </select>
        </div>
        <textarea value={content} onChange={(e) => setContent(e.target.value)} placeholder="Формулировка факта..." rows={2}
          className="w-full resize-none rounded border border-base-border bg-base-panel px-2 py-1 text-xs outline-none focus:border-accent" />
        <button type="submit" disabled={busy} className="rounded bg-accent px-3 py-1 text-xs font-medium text-white hover:bg-accent-dim disabled:opacity-50">
          Добавить (подтверждено сразу)
        </button>
      </form>
      {rows === null ? <p className="text-xs text-base-muted">Загрузка...</p> : rows.length === 0 ? <EmptyState text="База знаний пуста." /> : (
        <div className="space-y-1.5">
          {rows.map((m) => (
            <div key={m.id} className="rounded border border-base-border bg-base-panel2 p-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-medium">{m.key}</span>
                <span className="flex items-center gap-2">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] ${m.confirmed ? "bg-sev-low/15 text-sev-low" : "bg-sev-medium/15 text-sev-medium"}`}>
                    {m.confirmed ? "подтверждено" : "ожидает"}
                  </span>
                  <button onClick={() => remove(m.id)} className="text-base-muted hover:text-sev-critical">×</button>
                </span>
              </div>
              <p className="mt-1 text-base-muted">{m.content}</p>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

export default function SettingsPage() {
  const { user } = useAuth();
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
      <Panel title="Профиль">
        <div className="space-y-1 text-xs">
          <p><span className="text-base-muted">Имя: </span>{user?.full_name || "—"}</p>
          <p><span className="text-base-muted">Email: </span>{user?.email}</p>
          <p><span className="text-base-muted">Роль: </span>{user?.role}</p>
          <p><span className="text-base-muted">Подразделение: </span>{user?.department || "—"}</p>
        </div>
      </Panel>
      <Panel title="Права доступа">
        <div className="flex flex-wrap gap-1.5">
          {(user?.permissions || []).map((p) => (
            <span key={p} className="mono rounded border border-base-border bg-base-panel2 px-2 py-0.5 text-[10px] text-base-muted">{p}</span>
          ))}
        </div>
      </Panel>
      <ChangePasswordSection />
      <RiskRulesSection />
      <BusinessMemorySection />
      <Panel title="О системе">
        <p className="text-xs text-base-muted">
          MEZA — внутренняя AI операционная система ATON+. Работает локально, данные не покидают
          инфраструктуру компании. Не является SaaS-продуктом.
        </p>
      </Panel>
    </div>
  );
}
