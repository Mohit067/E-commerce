import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

type ApiOpts = RequestInit & { auth?: boolean; skipRefresh?: boolean };

function getTokens() {
  if (typeof window === "undefined") return { access: null, refresh: null };
  return {
    access: localStorage.getItem("nc_access"),
    refresh: localStorage.getItem("nc_refresh"),
  };
}

export async function apiFetch<T>(path: string, opts: ApiOpts = {}): Promise<T> {
  const { auth, skipRefresh, ...init } = opts;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };
  const { access, refresh } = getTokens();
  if (auth && access) headers["Authorization"] = `Bearer ${access}`;
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401 && auth && !skipRefresh && refresh) {
    // try refresh once
    const r = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (r.ok) {
      const t = await r.json();
      localStorage.setItem("nc_access", t.access_token);
      localStorage.setItem("nc_refresh", t.refresh_token);
      return apiFetch<T>(path, { ...opts, skipRefresh: true });
    }
    localStorage.removeItem("nc_access");
    localStorage.removeItem("nc_refresh");
    window.dispatchEvent(new Event("nc:logout"));
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      msg = j?.detail ?? j?.error?.message ?? msg;
    } catch { /* ignore */ }
    const e = new Error(msg) as Error & { status: number };
    e.status = res.status;
    throw e;
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function authHeaders(): Record<string, string> {
  const { access } = getTokens();
  return access ? { Authorization: `Bearer ${access}` } : {};
}

/** SSE streaming chat — calls onToken progressively, resolves products at end. */
export async function streamChat(
  message: string,
  conversationId: string | null,
  onToken: (t: string) => void,
  onProducts: (p: AgentProduct[]) => void,
): Promise<string> {
  const res = await fetch(`${API_URL}/agent/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  if (!res.ok || !res.body) {
    // fallback to non-streaming
    const j = await apiFetch<{ conversation_id: string; reply: string; products: AgentProduct[] }>(
      "/agent/chat",
      { method: "POST", body: JSON.stringify({ message, conversation_id: conversationId }) },
    );
    onToken(j.reply);
    onProducts(j.products);
    (streamChat as { _cid?: string })._cid = j.conversation_id;
    return j.conversation_id;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let cid = conversationId ?? "";
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      try {
        const evt = JSON.parse(line.slice(5));
        if (evt.type === "start" || evt.type === "done") cid = evt.conversation_id ?? cid;
        else if (evt.type === "token") {
          onToken(evt.token);
        } else if (evt.type === "products") onProducts(evt.products ?? []);
      } catch { /* ignore */ }
    }
  }
  return cid;
}

export interface AgentProduct {
  id: string;
  name: string;
  slug: string;
  price: number;
  rating_avg: number;
  image_url: string;
}
