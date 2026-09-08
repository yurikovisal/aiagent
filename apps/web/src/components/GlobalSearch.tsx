"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

interface SearchResult { type: string; id: number; label: string }

const TYPE_LABELS: Record<string, string> = {
  order: "Заказ", project: "Проект", customer: "Клиент", material: "Материал",
  employee: "Сотрудник", document: "Документ", supplier: "Поставщик",
};

const TYPE_ROUTES: Record<string, string> = {
  order: "/sales", project: "/projects", customer: "/sales", material: "/warehouse",
  employee: "/employees", document: "/documents", supplier: "/procurement",
};

export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const router = useRouter();

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
    else {
      setQuery("");
      setResults([]);
    }
  }, [open]);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const handle = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await apiFetch<{ results: SearchResult[] }>(`/api/v1/search?q=${encodeURIComponent(query)}`);
        setResults(res.results);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(handle);
  }, [query]);

  function goTo(r: SearchResult) {
    setOpen(false);
    router.push(TYPE_ROUTES[r.type] || "/overview");
  }

  function askMeza() {
    setOpen(false);
    window.dispatchEvent(new CustomEvent("meza:ask", { detail: query }));
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title="Глобальный поиск (⌘K)"
        className="flex items-center gap-1.5 rounded border border-base-border bg-base-panel2 px-2.5 py-1.5 text-xs text-base-muted transition hover:border-accent/50"
      >
        <span>🔍</span>
        <kbd className="rounded border border-base-border px-1 py-0.5 text-[10px]">⌘K</kbd>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-[10vh]" onClick={() => setOpen(false)}>
          <div className="fade-in w-full max-w-lg rounded border border-base-border bg-base-panel shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 border-b border-base-border px-4 py-3">
              <span className="text-base-muted">🔍</span>
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Найти заказ, проект, клиента, материала, сотрудника, документ, поставщика..."
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-base-muted"
              />
              {loading && <span className="pulse-dot text-xs text-accent">●</span>}
            </div>
            <div className="max-h-[50vh] overflow-y-auto px-2 py-2">
              {query.trim().length >= 2 && results.length === 0 && !loading && (
                <div className="px-2 py-3 text-center">
                  <p className="mb-2 text-xs text-base-muted">Ничего не найдено по названию.</p>
                  <button onClick={askMeza} className="text-xs text-accent hover:underline">
                    Спросить MEZA: «{query}»
                  </button>
                </div>
              )}
              {results.map((r) => (
                <button
                  key={`${r.type}-${r.id}`}
                  onClick={() => goTo(r)}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs hover:bg-base-panel2"
                >
                  <span className="w-16 shrink-0 text-[10px] uppercase tracking-wide text-base-muted">{TYPE_LABELS[r.type] || r.type}</span>
                  <span>{r.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
