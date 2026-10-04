"use client";
import Link from "next/link";
import { Send, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { apiFetch, streamChat, type AgentProduct } from "@/lib/api";
import { inr } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import { useUI } from "@/stores/ui";
import { cn } from "@/lib/utils";

interface Msg {
  role: "user" | "assistant";
  text: string;
  products?: AgentProduct[];
}

function Rich({ text }: { text: string }) {
  // minimal markdown: **bold**, newlines, "- " bullets
  const lines = text.split("\n");
  return (
    <div className="space-y-1 text-sm leading-relaxed">
      {lines.map((ln, i) => {
        const parts = ln.split(/(\*\*[^*]+\*\*)/g).map((seg, j) =>
          seg.startsWith("**") && seg.endsWith("**") ? (
            <strong key={j}>{seg.slice(2, -2)}</strong>
          ) : (
            <span key={j}>{seg}</span>
          ),
        );
        return (
          <p key={i} className={cn(ln.startsWith("- ") && "pl-3")}>
            {parts}
          </p>
        );
      })}
    </div>
  );
}

function AgentProductCard({ p, onAdded }: { p: AgentProduct; onAdded: () => void }) {
  const { user } = useAuth();
  const [done, setDone] = useState(false);
  const add = async () => {
    if (!user) return;
    await apiFetch("/cart/items", {
      method: "POST", auth: true,
      body: JSON.stringify({ product_id: p.id, quantity: 1 }),
    });
    setDone(true);
    onAdded();
  };
  return (
    <div className="flex gap-2 rounded-lg border border-zinc-200 dark:border-zinc-700 p-2">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={p.image_url || `https://picsum.photos/seed/${p.id}/200/200`} alt={p.name}
        className="h-14 w-14 rounded-md object-cover bg-zinc-100" loading="lazy" />
      <div className="min-w-0 flex-1">
        <Link href={`/products/${p.slug}`} className="line-clamp-2 text-xs font-medium hover:underline">
          {p.name}
        </Link>
        <p className="text-xs font-bold">{inr(p.price)} <span className="font-normal text-zinc-500">★{p.rating_avg}</span></p>
        <div className="mt-1 flex gap-1.5">
          <Link href={`/products/${p.slug}`} className="rounded-md border border-zinc-300 dark:border-zinc-600 px-2 py-0.5 text-[11px]">
            View
          </Link>
          {user && (
            <button onClick={add} className="rounded-md bg-zinc-900 dark:bg-white px-2 py-0.5 text-[11px] font-medium text-white dark:text-zinc-900">
              {done ? "Added ✓" : "Add to Cart"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  "Show me laptops under ₹80,000",
  "Best rated headphones?",
  "Current discounts?",
  "Track my latest order",
];

export function ChatWidget() {
  const open = useUI((s) => s.chatOpen);
  const setOpen = useUI((s) => s.setChatOpen);
  const bumpCart = useUI((s) => s.bumpCart);
  const { user } = useAuth();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [cid, setCid] = useState<string | null>(null);
  const [history, setHistory] = useState<{ id: string; title: string }[]>([]);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, open]);

  useEffect(() => {
    if (open && user) {
      apiFetch<{ id: string; title: string }[]>("/agent/conversations", { auth: true })
        .then(setHistory)
        .catch(() => {});
    }
  }, [open, user]);

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text: message }]);
    setBusy(true);
    let acc = "";
    setMsgs((m) => [...m, { role: "assistant", text: "" }]);
    try {
      const newCid = await streamChat(
        message, cid,
        (tok) => {
          acc += tok;
          setMsgs((m) => {
            const c = [...m];
            c[c.length - 1] = { role: "assistant", text: acc, products: c[c.length - 1].products };
            return c;
          });
        },
        (products) => {
          setMsgs((m) => {
            const c = [...m];
            c[c.length - 1] = { ...c[c.length - 1], products };
            return c;
          });
        },
      );
      setCid(newCid);
    } catch (e) {
      setMsgs((m) => {
        const c = [...m];
        c[c.length - 1] = { role: "assistant", text: `Sorry — I couldn't reach the assistant. ${(e as Error).message}` };
        return c;
      });
    } finally {
      setBusy(false);
    }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 sm:inset-auto sm:bottom-4 sm:right-4 sm:w-[400px] sm:h-[620px] sm:max-h-[85vh] flex flex-col bg-white dark:bg-zinc-950 sm:rounded-2xl sm:border sm:border-zinc-200 sm:dark:border-zinc-800 sm:shadow-2xl overflow-hidden">
      <div className="flex items-center gap-2 border-b border-zinc-200 dark:border-zinc-800 px-4 py-3">
        <Sparkles className="h-4 w-4" />
        <div className="flex-1">
          <p className="text-sm font-semibold">AI Shopping Assistant</p>
          <p className="text-[11px] text-zinc-500">Live catalog · orders · cart</p>
        </div>
        <button onClick={() => { setMsgs([]); setCid(null); }} className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-white px-2">
          New chat
        </button>
        <button onClick={() => setOpen(false)} className="rounded-lg p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800" aria-label="Close">
          <X className="h-4 w-4" />
        </button>
      </div>
      {user && history.length > 0 && msgs.length === 0 && (
        <div className="border-b border-zinc-200 dark:border-zinc-800 px-4 py-2 text-xs">
          <p className="mb-1 text-zinc-500">Recent chats</p>
          <div className="flex gap-1.5 overflow-x-auto">
            {history.slice(0, 5).map((h) => (
              <button key={h.id} onClick={async () => {
                const m = await apiFetch<{ role: string; content: string }[]>(`/agent/conversations/${h.id}`, { auth: true });
                setCid(h.id);
                setMsgs(m.map((x) => ({ role: x.role as "user" | "assistant", text: x.content })));
              }} className="whitespace-nowrap rounded-full border border-zinc-300 dark:border-zinc-700 px-2.5 py-1">
                {h.title.slice(0, 28)}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {msgs.length === 0 && (
          <div>
            <p className="text-sm text-zinc-500">Ask me anything — I search the live catalog, check stock, track orders and manage your cart.</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)} className="rounded-full border border-zinc-300 dark:border-zinc-700 px-3 py-1.5 text-xs hover:bg-zinc-100 dark:hover:bg-zinc-800">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
            <div className={cn(
              "max-w-[90%] rounded-xl px-3 py-2",
              m.role === "user" ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900" : "bg-zinc-100 dark:bg-zinc-900",
            )}>
              {m.role === "user" ? <p className="text-sm">{m.text}</p> : <Rich text={m.text || "…"} />}
              {m.products && m.products.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  {m.products.map((p) => (
                    <AgentProductCard key={p.id} p={p} onAdded={bumpCart} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottom} />
      </div>
      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2 border-t border-zinc-200 dark:border-zinc-800 p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything…"
          className="flex-1 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-transparent px-3 py-2 text-sm outline-none"
        />
        <button type="submit" disabled={busy} className="rounded-lg bg-zinc-900 dark:bg-white p-2 text-white dark:text-zinc-900 disabled:opacity-50" aria-label="Send">
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}

export function ChatFab() {
  const open = useUI((s) => s.chatOpen);
  const setOpen = useUI((s) => s.setChatOpen);
  if (open) return null;
  return (
    <button
      onClick={() => setOpen(true)}
      className="fixed bottom-4 right-4 z-40 inline-flex items-center gap-2 rounded-full bg-zinc-900 dark:bg-white px-4 py-3 text-sm font-medium text-white dark:text-zinc-900 shadow-lg"
    >
      <Sparkles className="h-4 w-4" /> Ask AI
    </button>
  );
}
