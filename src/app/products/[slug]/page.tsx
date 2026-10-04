"use client";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { inr, stars } from "@/lib/format";
import type { Product } from "@/types";
import { Badge, Button, Empty, ErrorState, Input, Skeleton } from "@/components/ui";
import { ProductCard } from "@/components/product";
import { useAuth } from "@/stores/auth";
import { useUI } from "@/stores/ui";
import Link from "next/link";

export default function ProductDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { user } = useAuth();
  const bumpCart = useUI((s) => s.bumpCart);
  const qc = useQueryClient();
  const router = useRouter();
  const [imgIdx, setImgIdx] = useState(0);
  const [variant, setVariant] = useState<string | null>(null);
  const [qty, setQty] = useState(1);

  const p = useQuery({
    queryKey: ["product", slug],
    queryFn: () => apiFetch<Product>(`/products/${slug}`),
  });
  const related = useQuery({
    queryKey: ["related", slug],
    queryFn: () => apiFetch<Product[]>(`/products/${slug}/related`),
    enabled: !!p.data,
  });
  const reviews = useQuery({
    queryKey: ["reviews", p.data?.id],
    queryFn: () => apiFetch<{ items: { id: string; user_name: string; rating: number; title: string; body: string; is_verified_purchase: boolean; created_at: string }[] }>(
      `/reviews/product/${p.data!.id}?page=1&page_size=10`),
    enabled: !!p.data,
  });

  const add = useMutation({
    mutationFn: () =>
      apiFetch("/cart/items", {
        method: "POST", auth: true,
        body: JSON.stringify({ product_id: p.data!.id, variant_id: variant, quantity: qty }),
      }),
    onSuccess: () => {
      bumpCart();
      qc.invalidateQueries({ queryKey: ["cart"] });
    },
  });

  const [rv, setRv] = useState({ rating: 5, title: "", body: "" });
  const submitReview = useMutation({
    mutationFn: () =>
      apiFetch(`/reviews/product/${p.data!.id}`, {
        method: "POST", auth: true, body: JSON.stringify(rv),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reviews"] });
      setRv({ rating: 5, title: "", body: "" });
    },
  });

  if (p.isLoading) {
    return (
      <div className="grid gap-6 py-6 md:grid-cols-2">
        <Skeleton className="aspect-square" />
        <div className="space-y-3">
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-24" />
        </div>
      </div>
    );
  }
  if (p.isError) return <div className="py-6"><ErrorState message={(p.error as Error).message} onRetry={() => p.refetch()} /></div>;
  if (!p.data) return <div className="py-6"><Empty title="Product unavailable" hint="It may have been removed." action={<Link href="/products"><Button>Browse products</Button></Link>} /></div>;

  const prod = p.data;
  const imgs = prod.images.length ? prod.images : [{ id: "ph", url: `https://picsum.photos/seed/${prod.id}/800/800`, alt: prod.name, position: 0 }];
  const out = prod.stock <= 0;

  return (
    <div className="py-6">
      <div className="grid gap-8 md:grid-cols-2">
        <div>
          <div className="aspect-square overflow-hidden rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-100">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={imgs[Math.min(imgIdx, imgs.length - 1)].url} alt={prod.name} className="h-full w-full object-cover" />
          </div>
          <div className="mt-2 flex gap-2">
            {imgs.map((im, i) => (
              <button key={im.id} onClick={() => setImgIdx(i)}
                className={`h-16 w-16 overflow-hidden rounded-lg border ${i === imgIdx ? "border-zinc-900 dark:border-white" : "border-zinc-200 dark:border-zinc-800"}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={im.url} alt={im.alt} className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-zinc-500">
            {prod.brand?.name} {prod.category ? `· ${prod.category.name}` : ""}
          </p>
          <h1 className="mt-1 text-2xl font-bold">{prod.name}</h1>
          <p className="mt-1 text-sm text-amber-500">{stars(prod.rating_avg)} <span className="text-zinc-500">{prod.rating_avg.toFixed(1)} · {prod.rating_count} reviews · {prod.sold_count} sold</span></p>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold">{inr(prod.price)}</span>
            {prod.compare_at_price > prod.price && (
              <>
                <span className="text-sm text-zinc-400 line-through">{inr(prod.compare_at_price)}</span>
                <Badge tone="green">{prod.discount_pct}% off</Badge>
              </>
            )}
          </div>
          <p className="mt-1 text-sm">{out ? <Badge tone="red">Out of stock</Badge> : prod.stock <= 5 ? <Badge tone="amber">Only {prod.stock} left in stock</Badge> : <Badge tone="green">In stock ({prod.stock})</Badge>}</p>

          {prod.variants.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium">Variant</p>
              <div className="mt-1.5 flex flex-wrap gap-2">
                <button onClick={() => setVariant(null)}
                  className={`rounded-lg border px-3 py-1.5 text-xs ${variant === null ? "border-zinc-900 dark:border-white font-bold" : "border-zinc-300 dark:border-zinc-700"}`}>
                  Default
                </button>
                {prod.variants.map((v) => (
                  <button key={v.id} onClick={() => setVariant(v.id)}
                    className={`rounded-lg border px-3 py-1.5 text-xs ${variant === v.id ? "border-zinc-900 dark:border-white font-bold" : "border-zinc-300 dark:border-zinc-700"}`}>
                    {v.name} {v.stock <= 0 ? "(out)" : ""}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 flex items-center gap-2">
            <div className="flex items-center rounded-lg border border-zinc-300 dark:border-zinc-700">
              <button onClick={() => setQty(Math.max(1, qty - 1))} className="px-3 py-1.5">−</button>
              <span className="w-8 text-center text-sm">{qty}</span>
              <button onClick={() => setQty(Math.min(9, qty + 1))} className="px-3 py-1.5">+</button>
            </div>
            <Button disabled={out || !user || add.isPending} onClick={() => add.mutate()} className="flex-1">
              {add.isPending ? "Adding…" : "Add to Cart"}
            </Button>
            <Button variant="outline" disabled={out || !user} onClick={() => { add.mutate(); router.push("/checkout"); }}>
              Buy Now
            </Button>
          </div>
          {!user && <p className="mt-1 text-xs text-zinc-500"><Link href="/login" className="underline">Log in</Link> to purchase.</p>}
          {add.isSuccess && <p className="mt-1 text-xs text-green-600">Added to cart ✓</p>}
          <p className="mt-3 text-xs text-zinc-500">Free delivery over ₹999 · 7-day replacement · GST invoice · Delivery in 3–5 days</p>

          <div className="mt-5">
            <p className="font-medium">Description</p>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{prod.description}</p>
          </div>
        </div>
      </div>

      {/* Reviews */}
      <div className="mt-10 grid gap-6 md:grid-cols-2">
        <div>
          <h2 className="font-bold">Ratings & reviews</h2>
          <div className="mt-2 space-y-3">
            {(reviews.data?.items ?? []).map((r) => (
              <div key={r.id} className="rounded-xl border border-zinc-200 dark:border-zinc-800 p-3">
                <p className="text-sm"><span className="text-amber-500">{stars(r.rating)}</span> <strong>{r.title}</strong></p>
                <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{r.body}</p>
                <p className="mt-1 text-xs text-zinc-500">— {r.user_name} {r.is_verified_purchase && <Badge tone="green">Verified purchase</Badge>}</p>
              </div>
            ))}
            {(reviews.data?.items.length ?? 0) === 0 && <p className="text-sm text-zinc-500">No reviews yet.</p>}
          </div>
        </div>
        <div>
          <h2 className="font-bold">Write a review</h2>
          {!user ? (
            <p className="mt-2 text-sm text-zinc-500"><Link href="/login" className="underline">Log in</Link> to review (verified on purchase).</p>
          ) : (
            <div className="mt-2 space-y-2">
              <select value={rv.rating} onChange={(e) => setRv({ ...rv, rating: Number(e.target.value) })}
                className="rounded-lg border border-zinc-300 dark:border-zinc-700 bg-transparent px-2 py-1.5 text-sm">
                {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} stars</option>)}
              </select>
              <Input placeholder="Title" value={rv.title} onChange={(e) => setRv({ ...rv, title: e.target.value })} />
              <textarea placeholder="Your review…" value={rv.body} onChange={(e) => setRv({ ...rv, body: e.target.value })}
                className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 bg-transparent px-3 py-2 text-sm" rows={4} />
              <Button disabled={submitReview.isPending} onClick={() => submitReview.mutate()}>
                {submitReview.isPending ? "Submitting…" : "Submit review"}
              </Button>
              {submitReview.isError && <p className="text-xs text-red-500">{(submitReview.error as Error).message}</p>}
              {submitReview.isSuccess && <p className="text-xs text-green-600">Thanks! Review posted.</p>}
            </div>
          )}
        </div>
      </div>

      {/* Related + frequently bought together */}
      <div className="mt-10">
        <h2 className="font-bold">Related products</h2>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {(related.data ?? []).map((r) => <ProductCard key={r.id} p={r} />)}
        </div>
      </div>
    </div>
  );
}
