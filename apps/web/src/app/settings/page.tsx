"use client";

import { useAuth } from "@/lib/auth-context";
import { Panel } from "@/components/Panel";

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
      <Panel title="О системе">
        <p className="text-xs text-base-muted">
          MEZA — внутренняя AI операционная система ATON+. Работает локально, данные не покидают
          инфраструктуру компании. Не является SaaS-продуктом.
        </p>
      </Panel>
    </div>
  );
}
