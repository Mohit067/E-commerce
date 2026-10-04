"use client";
import Link from "next/link";
import { Heart } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { inr } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import { useUI } from "@/stores/ui";
import type { Product } from "@/types";

export function ProductCard({ p }: { p: Product }) {
  const img = p.images?.[0]?.url ?? `https://picsum.photos/seed/${p.id}/600/600`;
  const { user } = useAuth();
  const qc = useQueryClient();
  const bumpCart = useUI((s) => s.bumpCart);
  const add = useMutation({
    mutationFn: () => apiFetch("/cart/items", {
      method: "POST", auth: true,
      body: JSON.stringify({ product_id: p.id, quantity: 1 }),
    }),
    onSuccess: () => {
      bumpCart();
      qc.invalidateQueries({ queryKey: ["cart"] });
    },
  });
  return (
    <div className="group overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 transition-shadow hover:shadow-md">
      <Link href={`/products/${p.slug}`}>
        <div className="aspect-square overflow-hidden bg-zinc-100 dark:bg-zinc-800">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={img} alt={p.name} loading="lazy" className="h-full w-full object-cover transition-transform group-hover:scale-105" />
        </div>
      </Link>
      <div className="p-3">
        <p className="text-[11px] uppercase tracking-wide text-zinc-400">{p.brand?.name ?? p.category?.name}</p>
        <Link href={`/products/${p.slug}`} className="mt-0.5 line-clamp-2 text-sm font-medium leading-snug">
          {p.name}
        </Link>
        <p className="mt-1 text-xs text-zinc-500">
          <span className="text-amber-500">★</span> {p.rating_avg.toFixed(1)} ({p.rating_count})
          {p.stock <= 0 ? <span className="ml-2 text-red-500">Out of stock</span> : p.stock <= 5 ? <span className="ml-2 text-amber-600">Only {p.stock} left</span> : null}
        </p>
        <div className="mt-1.5 flex items-baseline gap-2">
          <span className="font-bold">{inr(p.price)}</span>
          {p.compare_at_price > p.price && (
            <>
              <span className="text-xs text-zinc-400 line-through">{inr(p.compare_at_price)}</span>
              <span className="text-xs font-medium text-green-600">{p.discount_pct}% off</span>
            </>
          )}
        </div>
        <div className="mt-2 flex gap-2">
          <button
            disabled={!user || p.stock <= 0 || add.isPending}
            onClick={() => add.mutate()}
            className="flex-1 rounded-lg bg-zinc-900 dark:bg-white px-3 py-1.5 text-xs font-medium text-white dark:text-zinc-900 disabled:opacity-40"
          >
            {p.stock <= 0 ? "Out of stock" : add.isPending ? "Adding…" : "Add to Cart"}
          </button>
          <Link href={`/products/${p.slug}`} className="rounded-lg border border-zinc-300 dark:border-zinc-700 px-3 py-1.5 text-xs">
            View
          </Link>
        </div>
        {!user && <p className="mt-1 text-[11px] text-zinc-400"><Link href="/login" className="underline">Log in</Link> to add to cart</p>}
      </div>
    </div>
  );
}

export function ProductGridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800">
          <div className="aspect-square animate-pulse bg-zinc-200 dark:bg-zinc-800" />
          <div className="space-y-2 p-3">
            <div className="h-3 animate-pulse rounded bg-zinc-200 dark:bg-zinc-800" />
            <div className="h-3 w-2/3 animate-pulse rounded bg-zinc-200 dark:bg-zinc-800" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function WishlistHeart({ productId }: { productId: string }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const toggle = useMutation({
    mutationFn: () => apiFetch(`/wishlist/${productId}`, { method: "POST", auth: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["wishlist"] }),
  });
  if (!user) return null;
  return (
    <button
      onClick={() => toggle.mutate()}
      className="rounded-lg border border-zinc-300 dark:border-zinc-700 p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800"
      aria-label="Add to wishlist"
    >
      <Heart className="h-4 w-4" />
    </button>
  );
}
