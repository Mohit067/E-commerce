"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Category, PageRes, Product } from "@/types";
import { ProductCard, ProductGridSkeleton } from "@/components/product";
import { Empty, ErrorState } from "@/components/ui";
import { useUI } from "@/stores/ui";

function Section({ title, href, children }: { title: string; href?: string; children: React.ReactNode }) {
  return (
    <section className="mt-10">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-bold tracking-tight">{title}</h2>
        {href && <Link href={href} className="text-sm text-zinc-500 hover:underline">View all →</Link>}
      </div>
      {children}
    </section>
  );
}

export default function Home() {
  const setChatOpen = useUI((s) => s.setChatOpen);

  const cats = useQuery({ queryKey: ["cats"], queryFn: () => apiFetch<Category[]>("/categories") });
  const trending = useQuery({
    queryKey: ["trending"],
    queryFn: () => apiFetch<PageRes<Product>>("/products?page=1&page_size=8&sort=popular"),
  });
  const deals = useQuery({
    queryKey: ["deals-home"],
    queryFn: () => apiFetch<Product[]>("/products/deals"),
  });
  const recommended = useQuery({
    queryKey: ["reco"],
    queryFn: () => apiFetch<PageRes<Product>>("/products?page=1&page_size=8&sort=rating"),
  });

  return (
    <div className="pb-8">
      {/* Hero */}
      <section className="mt-6 overflow-hidden rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 px-6 py-10 sm:px-10">
        <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">Festive sale · up to 40% off</p>
        <h1 className="mt-2 max-w-xl text-3xl font-bold tracking-tight sm:text-4xl">
          Everything you love, found by AI.
        </h1>
        <p className="mt-2 max-w-lg text-sm text-zinc-500">
          1,200+ real products across electronics, fashion, home and more — with an AI assistant
          that searches, compares and checks out with you.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href="/products" className="rounded-lg bg-zinc-900 dark:bg-white px-4 py-2 text-sm font-medium text-white dark:text-zinc-900">
            Shop all products
          </Link>
          <button onClick={() => setChatOpen(true)} className="rounded-lg border border-zinc-300 dark:border-zinc-700 px-4 py-2 text-sm font-medium">
            Ask the AI assistant
          </button>
        </div>
      </section>

      {/* Categories */}
      <Section title="Shop by category" href="/products">
        {cats.isLoading ? (
          <div className="flex gap-3 overflow-hidden">{Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-24 w-32 shrink-0 animate-pulse rounded-xl bg-zinc-200 dark:bg-zinc-800" />
          ))}</div>
        ) : cats.isError ? (
          <ErrorState message="Could not load categories." onRetry={() => cats.refetch()} />
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-1">
            {(cats.data ?? []).slice(0, 20).map((c) => (
              <Link key={c.id} href={`/categories/${c.slug}`}
                className="w-32 shrink-0 overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={c.image_url || `https://picsum.photos/seed/${c.slug}/300/200`} alt={c.name}
                  className="h-16 w-full object-cover" loading="lazy" />
                <p className="truncate px-2 py-1.5 text-xs font-medium">{c.name}</p>
              </Link>
            ))}
          </div>
        )}
      </Section>

      {/* Trending */}
      <Section title="Trending now" href="/products?sort=popular">
        {trending.isLoading ? <ProductGridSkeleton /> :
          trending.isError ? <ErrorState message="Could not load products." onRetry={() => trending.refetch()} /> :
          (trending.data?.items.length ?? 0) === 0 ? <Empty title="No products yet" /> : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {trending.data!.items.map((p) => <ProductCard key={p.id} p={p} />)}
          </div>
        )}
      </Section>

      {/* Deals */}
      <Section title="Deals of the day" href="/search?q=&sort=popular">
        {deals.isLoading ? <ProductGridSkeleton /> :
          deals.isError ? <ErrorState message="Could not load deals." onRetry={() => deals.refetch()} /> : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {(deals.data ?? []).slice(0, 8).map((p) => <ProductCard key={p.id} p={p} />)}
          </div>
        )}
      </Section>

      {/* Recommended */}
      <Section title="Top rated for you" href="/products?sort=rating">
        {recommended.isLoading ? <ProductGridSkeleton /> :
          recommended.isError ? <ErrorState message="Could not load recommendations." onRetry={() => recommended.refetch()} /> : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {(recommended.data?.items ?? []).map((p) => <ProductCard key={p.id} p={p} />)}
          </div>
        )}
      </Section>
    </div>
  );
}
