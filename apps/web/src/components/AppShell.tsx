"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { CommandBar } from "./CommandBar";
import { GlobalSearch } from "./GlobalSearch";

const NAV = [
  { href: "/overview", label: "Overview" },
  { href: "/sales", label: "Sales" },
  { href: "/projects", label: "Projects" },
  { href: "/production", label: "Production" },
  { href: "/warehouse", label: "Warehouse" },
  { href: "/procurement", label: "Procurement" },
  { href: "/finance", label: "Finance" },
  { href: "/documents", label: "Documents" },
  { href: "/inbox", label: "Inbox" },
  { href: "/import", label: "Import" },
  { href: "/employees", label: "Employees" },
  { href: "/approvals", label: "Approvals" },
  { href: "/ai-operations", label: "AI Operations" },
  { href: "/users", label: "Users", permission: "manage:users" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout, hasPermission } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-xs text-base-muted">Загрузка...</div>;
  }
  if (!user) return null;

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-52 flex-col border-r border-base-border bg-base-panel">
        <div className="flex items-center gap-2 border-b border-base-border px-4 py-3.5">
          <div className="flex h-6 w-6 items-center justify-center rounded bg-accent text-xs font-bold text-white">M</div>
          <span className="text-sm font-semibold tracking-tight">MEZA</span>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
          {NAV.filter((item) => !item.permission || hasPermission(item.permission)).map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block rounded px-3 py-1.5 text-[13px] transition ${
                  active ? "bg-accent/15 text-accent" : "text-base-muted hover:bg-base-panel2 hover:text-base-text"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-base-border px-3 py-3">
          <p className="truncate text-xs font-medium">{user.full_name || user.email}</p>
          <p className="truncate text-[11px] text-base-muted">{user.role}</p>
          <button onClick={logout} className="mt-1.5 text-[11px] text-base-muted hover:text-sev-critical">
            Выйти
          </button>
        </div>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-base-border bg-base-bg px-6 py-2.5">
          <div className="flex-1">
            <CommandBar />
          </div>
          <GlobalSearch />
        </header>
        <main className="flex-1 overflow-y-auto px-6 py-6">{children}</main>
      </div>
    </div>
  );
}
