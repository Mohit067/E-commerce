"use client";
import { create } from "zustand";
import { apiFetch } from "@/lib/api";
import { mergeGuestCart } from "@/stores/guest-cart";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthState {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, full_name: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  ready: false,
  login: async (email, password) => {
    const t = await apiFetch<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("nc_access", t.access_token);
    localStorage.setItem("nc_refresh", t.refresh_token);
    await mergeGuestCart().catch(() => {});
    const me = await apiFetch<User>("/auth/me", { auth: true });
    set({ user: me, ready: true });
  },
  signup: async (email, password, full_name) => {
    const t = await apiFetch<{ access_token: string; refresh_token: string }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    });
    localStorage.setItem("nc_access", t.access_token);
    localStorage.setItem("nc_refresh", t.refresh_token);
    await mergeGuestCart().catch(() => {});
    const me = await apiFetch<User>("/auth/me", { auth: true });
    set({ user: me, ready: true });
  },
  logout: () => {
    localStorage.removeItem("nc_access");
    localStorage.removeItem("nc_refresh");
    set({ user: null, ready: true });
  },
  refreshMe: async () => {
    if (!localStorage.getItem("nc_access")) {
      set({ ready: true });
      return;
    }
    try {
      const me = await apiFetch<User>("/auth/me", { auth: true });
      set({ user: me, ready: true });
    } catch {
      set({ user: null, ready: true });
    }
  },
}));

if (typeof window !== "undefined") {
  window.addEventListener("nc:logout", () => useAuth.getState().logout());
}
