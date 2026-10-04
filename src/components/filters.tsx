"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Category } from "@/types";

export interface Filters {
  search: string;
  category: string;
  brand: string;
  min_price: string;
  max_price: string;
  rating: string;
  sort: string;
}

export const DEFAULT_FILTERS: Filters = {
  search: "", category: "", brand: "", min_price: "", max_price: "", rating: "", sort: "popular",
};

export function FilterBar({ f, set }: { f: Filters; set: (f: Filters) => void }) {
  const cats = useQuery({ queryKey: ["cats"], queryFn: () => apiFetch<Category[]>("/categories") });
  const brands = useQuery({
    queryKey: ["brands"],
    queryFn: () => apiFetch<{ slug: string; name: string }[]>("/brands"),
  });
  const sel = "rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2.5 py-1.5 text-sm";
  return (
    <div className="flex flex-wrap gap-2 rounded-xl border border-zinc-200 dark:border-zinc-800 p-3">
      <input
        value={f.search} onChange={(e) => set({ ...f, search: e.target.value })}
        placeholder="Keyword…" className={sel + " w-40"} />
      <select value={f.category} onChange={(e) => set({ ...f, category: e.target.value })} className={sel}>
        <option value="">All categories</option>
        {(cats.data ?? []).map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
      </select>
      <select value={f.brand} onChange={(e) => set({ ...f, brand: e.target.value })} className={sel}>
        <option value="">All brands</option>
        {(brands.data ?? []).map((b) => <option key={b.slug} value={b.slug}>{b.name}</option>)}
      </select>
      <input value={f.min_price} onChange={(e) => set({ ...f, min_price: e.target.value })}
        placeholder="Min ₹" inputMode="numeric" className={sel + " w-24"} />
      <input value={f.max_price} onChange={(e) => set({ ...f, max_price: e.target.value })}
        placeholder="Max ₹" inputMode="numeric" className={sel + " w-24"} />
      <select value={f.rating} onChange={(e) => set({ ...f, rating: e.target.value })} className={sel}>
        <option value="">Any rating</option>
        <option value="4.5">4.5★ & up</option>
        <option value="4">4★ & up</option>
        <option value="3">3★ & up</option>
      </select>
      <select value={f.sort} onChange={(e) => set({ ...f, sort: e.target.value })} className={sel}>
        <option value="popular">Most popular</option>
        <option value="rating">Top rated</option>
        <option value="newest">Newest</option>
        <option value="price_asc">Price: low → high</option>
        <option value="price_desc">Price: high → low</option>
      </select>
      <button onClick={() => set(DEFAULT_FILTERS)} className="text-xs text-zinc-500 hover:underline px-1">
        Reset
      </button>
    </div>
  );
}

export function buildQuery(f: Filters, page: number): string {
  const p = new URLSearchParams({ page: String(page), page_size: "24", sort: f.sort });
  if (f.search) p.set("search", f.search);
  if (f.category) p.set("category", f.category);
  if (f.brand) p.set("brand", f.brand);
  if (f.min_price) p.set("min_price", f.min_price);
  if (f.max_price) p.set("max_price", f.max_price);
  if (f.rating) p.set("rating", f.rating);
  return p.toString();
}
