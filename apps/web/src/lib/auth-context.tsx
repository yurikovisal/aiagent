"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, setToken as persistToken, getToken } from "./api";
import type { UserInfo } from "./types";

interface AuthState {
  user: UserInfo | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasPermission: (perm: string) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await apiFetch<UserInfo>("/api/v1/auth/me");
        setUser(me);
      } catch {
        persistToken(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiFetch<{ access_token: string; user: UserInfo }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    persistToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    persistToken(null);
    setUser(null);
    window.location.href = "/login";
  }, []);

  const hasPermission = useCallback((perm: string) => !!user?.permissions?.includes(perm), [user]);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
