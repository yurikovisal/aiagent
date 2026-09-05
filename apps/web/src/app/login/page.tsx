"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      router.push("/overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-base-bg px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded bg-accent text-base font-bold text-white">
            M
          </div>
          <h1 className="text-lg font-semibold tracking-tight">MEZA</h1>
          <p className="mt-1 text-xs text-base-muted">Внутренняя AI операционная система ATON+</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3 rounded border border-base-border bg-base-panel p-6">
          <div>
            <label className="mb-1 block text-xs text-base-muted">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded border border-base-border bg-base-panel2 px-3 py-2 text-sm outline-none focus:border-accent"
              placeholder="admin@atonplus.internal-demo.kz"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-base-muted">Пароль</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded border border-base-border bg-base-panel2 px-3 py-2 text-sm outline-none focus:border-accent"
            />
          </div>
          {error && <p className="text-xs text-sev-critical">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded bg-accent py-2 text-sm font-medium text-white transition hover:bg-accent-dim disabled:opacity-50"
          >
            {busy ? "Вход..." : "Войти"}
          </button>
        </form>
        <p className="mt-4 text-center text-[11px] text-base-muted">
          Внутренняя система ATON+. Доступ только для сотрудников.
        </p>
      </div>
    </div>
  );
}
