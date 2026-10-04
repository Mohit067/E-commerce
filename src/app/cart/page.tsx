"use client";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { inr } from "@/lib/format";
import { Button, Card, Empty, ErrorState, Input, Skeleton } from "@/components/ui";
import { useAuth } from "@/stores/auth";
import { useUI } from "@/stores/ui";
import { useState } from "react";

interface CartItem {
  id: string;
  product: { id: string; name: string; slug: string; images: { url: string }[] };
  variant: { name: string } | null;
  quantity: number;
  unit_price: number;
  line_total: number;
}
interface Cart {
  id: string;
  items: CartItem[];
  subtotal: number;
  discount: number;
  shipping: number;
  tax: number;
  total: number;
  coupon_code: string;
}

export default function CartPage() {
  const { user } = useAuth();
  const bumpCart = useUI((s) => s.bumpCart);
  const qc = useQueryClient();
  const [coupon, setCoupon] = useState("");
  const [couponMsg, setCouponMsg] = useState("");

  const cart = useQuery({
    queryKey: ["cart", "page"],
    queryFn: () => apiFetch<Cart>("/cart", { auth: true }),
    enabled: !!user,
  });

  if (!user) {
    return <div className="py-12"><Empty title="Your cart lives here" hint="Log in to sync your backend-backed cart." action={<Link href="/login"><Button>Login</Button></Link>} /></div>;
  }
  if (cart.isLoading) return <div className="py-6 space-y-2"><Skeleton className="h-20" /><Skeleton className="h-20" /></div>;
  if (cart.isError) return <div className="py-6"><ErrorState message={(cart.error as Error).message} onRetry={() => cart.refetch()} /></div>;

  const c = cart.data!;
  return (
    <div className="grid gap-6 py-6 lg:grid-cols-3">
      <div className="lg:col-span-2 space-y-2">
        <h1 className="text-xl font-bold">Cart ({c.items.length})</h1>
        {c.items.length === 0 && <Empty title="Cart is empty" hint="Add products or ask the AI assistant." action={<Link href="/products"><Button>Shop now</Button></Link>} />}
        {c.items.map((i) => (
          <CartRow key={i.id} item={i} onChanged={() => { qc.invalidateQueries({ queryKey: ["cart"] }); bumpCart(); }} />
        ))}
      </div>
      <Card className="h-fit p-4">
        <h2 className="font-bold">Summary</h2>
        <dl className="mt-2 space-y-1 text-sm">
          <div className="flex justify-between"><dt>Subtotal</dt><dd>{inr(c.subtotal)}</dd></div>
          <div className="flex justify-between text-green-600"><dt>Discount</dt><dd>−{inr(c.discount)}</dd></div>
          <div className="flex justify-between"><dt>Shipping</dt><dd>{inr(c.shipping)}</dd></div>
          <div className="flex justify-between"><dt>Tax (18%)</dt><dd>{inr(c.tax)}</dd></div>
          <div className="flex justify-between border-t border-zinc-200 dark:border-zinc-800 pt-1 font-bold"><dt>Total</dt><dd>{inr(c.total)}</dd></div>
        </dl>
        <div className="mt-3 flex gap-2">
          <Input placeholder="Coupon code" value={coupon} onChange={(e) => setCoupon(e.target.value)} />
          <Button variant="outline" onClick={async () => {
            setCouponMsg("");
            try {
              await apiFetch("/cart/coupon", { method: "POST", auth: true, body: JSON.stringify({ code: coupon, subtotal: c.subtotal }) });
              cart.refetch();
              setCouponMsg("Coupon applied ✓");
            } catch (e) { setCouponMsg((e as Error).message); }
          }}>Apply</Button>
        </div>
        {couponMsg && <p className="mt-1 text-xs text-zinc-500">{couponMsg}</p>}
        {c.coupon_code && <p className="mt-1 text-xs text-green-600">Active: {c.coupon_code}</p>}
        <Link href="/checkout"><Button className="mt-3 w-full" disabled={c.items.length === 0}>Proceed to Checkout</Button></Link>
      </Card>
    </div>
  );
}

function CartRow({ item, onChanged }: { item: CartItem; onChanged: () => void }) {
  const setQty = async (q: number) => {
    await apiFetch("/cart", { auth: true }).catch(() => null);
    await apiFetch(`/cart/items/${item.id}`, { method: "PATCH", auth: true, body: JSON.stringify({ quantity: q }) });
    onChanged();
  };
  return (
    <div className="flex gap-3 rounded-xl border border-zinc-200 dark:border-zinc-800 p-3">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={item.product.images?.[0]?.url ?? `https://picsum.photos/seed/${item.product.id}/200/200`}
        alt={item.product.name} className="h-20 w-20 rounded-lg object-cover bg-zinc-100" />
      <div className="flex-1">
        <Link href={`/products/${item.product.slug}`} className="text-sm font-medium hover:underline">{item.product.name}</Link>
        {item.variant && <p className="text-xs text-zinc-500">{item.variant.name}</p>}
        <p className="text-sm font-bold">{inr(item.unit_price)}</p>
        <div className="mt-1 flex items-center gap-2">
          <div className="flex items-center rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm">
            <button onClick={() => setQty(item.quantity - 1)} className="px-2.5 py-1">−</button>
            <span className="w-6 text-center">{item.quantity}</span>
            <button onClick={() => setQty(item.quantity + 1)} className="px-2.5 py-1">+</button>
          </div>
          <button onClick={() => setQty(0)} className="text-xs text-red-500 hover:underline">Remove</button>
        </div>
      </div>
      <p className="text-sm font-bold">{inr(item.line_total)}</p>
    </div>
  );
}
