"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { inr } from "@/lib/format";
import { Button, Card, Empty, Input } from "@/components/ui";
import { useAuth } from "@/stores/auth";
import { useUI } from "@/stores/ui";

export default function CheckoutPage() {
  const { user } = useAuth();
  const bumpCart = useUI((s) => s.bumpCart);
  const router = useRouter();
  const [form, setForm] = useState({ line1: "221 MG Road", city: "Bengaluru", state: "Karnataka", postal_code: "560001", phone: "9876543210" });
  const [coupon, setCoupon] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [offers, setOffers] = useState<{ code: string; description: string }[]>([]);

  const cart = useQuery({
    queryKey: ["cart", "checkout"],
    queryFn: () => apiFetch<{ items: unknown[]; subtotal: number; discount: number; shipping: number; tax: number; total: number }>("/cart", { auth: true }),
    enabled: !!user,
  });

  useEffect(() => {
    apiFetch<{ code: string; description: string }[]>("/coupons").then(setOffers).catch(() => {});
  }, []);

  if (!user) return <div className="py-12"><Empty title="Checkout needs an account" action={<Link href="/login"><Button>Login</Button></Link>} /></div>;

  const place = async () => {
    setErr("");
    setBusy(true);
    try {
      const order = await apiFetch<{ id: string }>("/orders/checkout", {
        method: "POST", auth: true,
        body: JSON.stringify({ address: { ...form, full_name: user.full_name, country: "India" }, coupon_code: coupon, payment_provider: "mock" }),
      });
      bumpCart();
      router.push(`/orders/${order.id}`);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const c = cart.data;
  return (
    <div className="grid gap-6 py-6 lg:grid-cols-2">
      <Card className="h-fit p-4">
        <h2 className="font-bold">Shipping address</h2>
        <div className="mt-2 grid grid-cols-2 gap-2">
          {(["line1", "city", "state", "postal_code", "phone"] as const).map((k) => (
            <Input key={k} placeholder={k} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })}
              className={k === "line1" ? "col-span-2" : ""} />
          ))}
        </div>
        <h2 className="mt-4 font-bold">Payment</h2>
        <p className="text-sm text-zinc-500">Mock payments-ready gateway (provider: mock). Tokens never touch the client.</p>
        <div className="mt-2 rounded-lg border border-zinc-200 dark:border-zinc-800 p-3 text-sm">
          <label className="flex items-center gap-2"><input type="radio" defaultChecked /> UPI / Card (mock) — charged on delivery confirmation</label>
        </div>
        <h2 className="mt-4 font-bold">Coupon</h2>
        <div className="mt-1 flex gap-2">
          <Input placeholder="e.g. WELCOME10" value={coupon} onChange={(e) => setCoupon(e.target.value.toUpperCase())} />
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {offers.map((o) => (
            <button key={o.code} onClick={() => setCoupon(o.code)} title={o.description}
              className="rounded-full border border-zinc-300 dark:border-zinc-700 px-2.5 py-1 text-xs">
              {o.code}
            </button>
          ))}
        </div>
        {err && <p className="mt-2 text-xs text-red-500">{err}</p>}
        <Button onClick={place} disabled={busy || !c || c.items.length === 0} className="mt-4 w-full">
          {busy ? "Placing order…" : `Pay ${c ? inr(c.total) : ""} & place order`}
        </Button>
      </Card>
      <Card className="h-fit p-4">
        <h2 className="font-bold">Order summary</h2>
        {c ? (
          <dl className="mt-2 space-y-1 text-sm">
            <div className="flex justify-between"><dt>Items</dt><dd>{c.items.length}</dd></div>
            <div className="flex justify-between"><dt>Subtotal</dt><dd>{inr(c.subtotal)}</dd></div>
            <div className="flex justify-between"><dt>Shipping</dt><dd>{inr(c.shipping)}</dd></div>
            <div className="flex justify-between"><dt>Tax</dt><dd>{inr(c.tax)}</dd></div>
            <div className="flex justify-between border-t border-zinc-200 dark:border-zinc-800 pt-1 font-bold"><dt>Total</dt><dd>{inr(c.total)}</dd></div>
          </dl>
        ) : <p className="text-sm text-zinc-500">Loading…</p>}
      </Card>
    </div>
  );
}
