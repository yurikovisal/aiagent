"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiWsUrl } from "@/lib/api";
import { SeverityBadge } from "./SeverityBadge";
import type { OrchestrationResult } from "@/lib/types";

interface StatusEvent { type: string; message?: string }

export function CommandBar() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [statusLog, setStatusLog] = useState<string[]>([]);
  const [result, setResult] = useState<OrchestrationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [expandedRisk, setExpandedRisk] = useState<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  const ask = useCallback((message: string) => {
    if (!message.trim()) return;
    setBusy(true);
    setStatusLog([]);
    setResult(null);
    try {
      const ws = new WebSocket(apiWsUrl());
      wsRef.current = ws;
      ws.onopen = () => ws.send(JSON.stringify({ message }));
      ws.onmessage = (evt) => {
        const data: StatusEvent & Partial<OrchestrationResult> = JSON.parse(evt.data);
        if (data.type === "status" && data.message) {
          setStatusLog((log) => [...log, data.message as string]);
        } else if (data.type === "result") {
          setResult(data as unknown as OrchestrationResult);
          setBusy(false);
          ws.close();
        } else if (data.type === "error") {
          setStatusLog((log) => [...log, `Ошибка: ${data.message}`]);
          setBusy(false);
        }
      };
      ws.onerror = () => setBusy(false);
    } catch {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    function onAskEvent(e: Event) {
      const text = (e as CustomEvent<string>).detail || "";
      setOpen(true);
      setQuery(text);
      ask(text);
    }
    window.addEventListener("meza:ask", onAskEvent);
    return () => window.removeEventListener("meza:ask", onAskEvent);
  }, [ask]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    ask(query);
  }

  function close() {
    setOpen(false);
    wsRef.current?.close();
    setQuery("");
    setResult(null);
    setStatusLog([]);
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex w-full max-w-md items-center gap-2 rounded border border-base-border bg-base-panel2 px-3 py-1.5 text-left text-xs text-base-muted transition hover:border-accent/50"
      >
        <span className="text-sm">✦</span>
        <span>Ask MEZA...</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-[10vh]" onClick={close}>
          <div
            className="fade-in w-full max-w-2xl rounded border border-base-border bg-base-panel shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <form onSubmit={handleSubmit} className="flex items-center gap-2 border-b border-base-border px-4 py-3">
              <span className="text-accent">✦</span>
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Что сейчас требует моего внимания? Почему задерживается заказ 123?"
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-base-muted"
              />
              {busy && <span className="pulse-dot text-xs text-accent">●</span>}
            </form>

            <div className="max-h-[60vh] overflow-y-auto px-4 py-3">
              {!result && statusLog.length === 0 && (
                <div className="space-y-1 py-2 text-xs text-base-muted">
                  <p>Примеры:</p>
                  {["Что сейчас требует моего внимания?", "Что горит?", "Почему задерживается заказ AT-1001?", "Покажи склад", "Подготовь утренний отчёт"].map((ex) => (
                    <button
                      key={ex}
                      onClick={() => { setQuery(ex); ask(ex); }}
                      className="block w-full rounded px-2 py-1 text-left hover:bg-base-panel2"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              )}

              {statusLog.length > 0 && !result && (
                <div className="space-y-1 py-2">
                  {statusLog.map((s, i) => (
                    <p key={i} className="fade-in text-xs text-base-muted">
                      <span className="mr-1.5 text-accent">›</span>{s}
                    </p>
                  ))}
                </div>
              )}

              {result && (
                <div className="fade-in space-y-3 py-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm leading-relaxed">{result.summary}</p>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-base-muted">
                    <span>{result.confidence_label}</span>
                    <span>·</span>
                    <span>run {result.run_id.slice(0, 8)}</span>
                  </div>

                  {result.risks?.length > 0 && (
                    <div className="space-y-1.5 border-t border-base-border pt-2">
                      {result.risks.map((r) => (
                        <div key={r.id} className="rounded border border-base-border bg-base-panel2 p-2">
                          <button
                            className="flex w-full items-center justify-between gap-2 text-left"
                            onClick={() => setExpandedRisk(expandedRisk === r.id ? null : r.id)}
                          >
                            <span className="flex items-center gap-2">
                              <SeverityBadge severity={r.severity} />
                              <span className="text-xs">{r.title}</span>
                            </span>
                            <span className="text-[10px] text-base-muted">{expandedRisk === r.id ? "−" : "+"}</span>
                          </button>
                          {expandedRisk === r.id && (
                            <div className="mt-2 space-y-1 border-t border-base-border pt-2 text-[11px] text-base-muted">
                              <p><span className="text-base-text">Причина:</span> {r.cause}</p>
                              <p><span className="text-base-text">Влияние:</span> {r.impact}</p>
                              {r.recommendation && <p><span className="text-base-text">Рекомендация:</span> {r.recommendation}</p>}
                              {r.evidence?.length > 0 && (
                                <div className="mt-1">
                                  <p className="text-base-text">Доказательства:</p>
                                  <ul className="list-inside list-disc">
                                    {r.evidence.map((e, i) => (
                                      <li key={i}>{e.fact} <span className="opacity-60">({e.source})</span></li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {result.recommendations?.length > 0 && (
                    <div className="border-t border-base-border pt-2">
                      <p className="mb-1 text-[10px] uppercase tracking-wide text-base-muted">Рекомендовано</p>
                      <ul className="list-inside list-disc space-y-0.5 text-xs">
                        {result.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    </div>
                  )}

                  <button onClick={close} className="mt-1 text-[11px] text-base-muted hover:text-base-text">
                    Закрыть (Esc)
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
