"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Panel, EmptyState } from "@/components/Panel";

interface UserRow {
  id: number;
  email: string;
  full_name: string;
  role: string;
  department?: string | null;
  is_active: boolean;
  last_login_at?: string | null;
}

const ROLES = ["ADMIN", "DIRECTOR", "DEPARTMENT_HEAD", "MANAGER", "EMPLOYEE", "VIEWER"];

export default function UsersPage() {
  const { user: me, hasPermission } = useAuth();
  const [users, setUsers] = useState<UserRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ email: "", full_name: "", password: "", role: "VIEWER", department: "" });
  const [busy, setBusy] = useState(false);

  function load() {
    apiFetch<UserRow[]>("/api/v1/users").then(setUsers).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }
  useEffect(load, []);

  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/api/v1/users", { method: "POST", body: JSON.stringify(form) });
      setForm({ email: "", full_name: "", password: "", role: "VIEWER", department: "" });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(u: UserRow, role: string) {
    await apiFetch(`/api/v1/users/${u.id}`, { method: "PATCH", body: JSON.stringify({ role }) });
    load();
  }

  async function toggleActive(u: UserRow) {
    await apiFetch(`/api/v1/users/${u.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !u.is_active }) });
    load();
  }

  if (!hasPermission("manage:users")) {
    return (
      <div className="mx-auto max-w-md pt-20 text-center text-sm text-base-muted">
        Недостаточно прав для управления пользователями.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Users</h1>

      <Panel title="Создать пользователя">
        <form onSubmit={createUser} className="grid grid-cols-1 gap-2 sm:grid-cols-5 sm:items-end">
          <div className="sm:col-span-1">
            <label className="mb-1 block text-[11px] text-base-muted">Email</label>
            <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full rounded border border-base-border bg-base-panel2 px-2 py-1.5 text-xs outline-none focus:border-accent" />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-base-muted">Имя</label>
            <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              className="w-full rounded border border-base-border bg-base-panel2 px-2 py-1.5 text-xs outline-none focus:border-accent" />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-base-muted">Пароль</label>
            <input required type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full rounded border border-base-border bg-base-panel2 px-2 py-1.5 text-xs outline-none focus:border-accent" />
          </div>
          <div>
            <label className="mb-1 block text-[11px] text-base-muted">Роль</label>
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-full rounded border border-base-border bg-base-panel2 px-2 py-1.5 text-xs outline-none focus:border-accent">
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <button type="submit" disabled={busy} className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-dim disabled:opacity-50">
            Создать
          </button>
        </form>
        {error && <p className="mt-2 text-xs text-sev-critical">{error}</p>}
      </Panel>

      <Panel title="Пользователи">
        {users === null ? <p className="text-xs text-base-muted">Загрузка...</p> : users.length === 0 ? <EmptyState text="Пользователей нет." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-base-border text-base-muted">
                  <th className="pb-2 font-normal">Email</th>
                  <th className="pb-2 font-normal">Имя</th>
                  <th className="pb-2 font-normal">Роль</th>
                  <th className="pb-2 font-normal">Подразделение</th>
                  <th className="pb-2 font-normal">Статус</th>
                  <th className="pb-2 font-normal">Последний вход</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-base-border/50">
                    <td className="py-1.5">{u.email}</td>
                    <td className="py-1.5">{u.full_name || "—"}</td>
                    <td className="py-1.5">
                      <select
                        value={u.role}
                        disabled={u.id === me?.id}
                        onChange={(e) => changeRole(u, e.target.value)}
                        className="rounded border border-base-border bg-base-panel2 px-1.5 py-0.5 text-[11px] outline-none focus:border-accent disabled:opacity-50"
                      >
                        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </td>
                    <td className="py-1.5 text-base-muted">{u.department || "—"}</td>
                    <td className="py-1.5">
                      <button
                        disabled={u.id === me?.id}
                        onClick={() => toggleActive(u)}
                        className={`rounded px-1.5 py-0.5 text-[10px] disabled:opacity-50 ${u.is_active ? "bg-sev-low/15 text-sev-low" : "bg-base-border text-base-muted"}`}
                      >
                        {u.is_active ? "активен" : "отключён"}
                      </button>
                    </td>
                    <td className="py-1.5 text-base-muted">{u.last_login_at ? new Date(u.last_login_at).toLocaleString("ru-RU") : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
