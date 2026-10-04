"use client";
import { Suspense, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { PageRes, Product } from "@/types";
import { ProductCard, ProductGridSkeleton } from "@/components/product";
import { Empty, ErrorState } from "@/components/ui";
import { DEFAULT_FILTERS, FilterBar, type Filters } from "@/components/filters";

function SearchInner({ initial }: { initial: string }) {
  const [f, setF] = useState<Filters>({ ...DEFAULT_FILTERS, search: initial });
  const [page, setPage] = useState(1);

  // debounce keyword
  const [kw, setKw] = useState(initial);
  useEffect(() => {
    const t = setTimeout(() => { setF((o) => ({ ...o, search: kw })); setPage(1); }, 350);
    return () => clearTimeout(t);
  }, [kw]);

  const params = new URLSearchParams({ q: f.search, page: String(page), page_size: "24", sort: f.sort });
  if (f.category) params.set("category", f.category);
  if (f.brand) params.set("brand", f.brand);
  if (f.min_price) params.set("min_price", f.min_price);
  if (f.max_price) params.set("max_price", f.max_price);
  if (f.rating) params.set("rating", f.rating);
  const qs = params.toString();

  const q = useQuery({
    queryKey: ["search", qs],
    queryFn: () => apiFetch<PageRes<Product> & { suggestions: string[] }>(`/search?${qs}`),
  });

  return (
    <div className="py-6">
      <h1 className="text-xl font-bold">Search{q.data ? <span className="text-zinc-500 font-normal"> · {q.data.total} results for “{f.search}”</span> : null}</h1>
      <div className="mt-3">
        <FilterBar f={{ ...f, search: kw }} set={(nf) => { setKw(nf.search); setF(nf); setPage(1); }} />
      </div>
      {q.data?.suggestions?.length ? (
        <p className="mt-2 text-xs text-zinc-500">
          Suggestions: {q.data!.suggestions.map((s, i) => (
            <button key={i} onClick={() => setKw(s)} className="mr-2 underline">{s}</button>
          ))}
        </p>
      ) : null}
      <div className="mt-4">
        {q.isLoading ? <ProductGridSkeleton /> :
          q.isError ? <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /> :
          q.data!.items.length === 0 ? <Empty title={`No results for “${f.search}”`} hint="Check spelling or try a broader term." /> : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {q.data!.items.map((p) => <ProductCard key={p.id} p={p} />)}
            </div>
            <div className="mt-6 flex items-center justify-center gap-3 text-sm">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)}
                className="rounded-lg border border-zinc-300 dark:border-zinc-700 px-3 py-1.5 disabled:opacity-40">← Prev</button>
              <span>Page {q.data!.page} of {q.data!.total_pages}</span>
              <button disabled={page >= q.data!.total_pages} onClick={() => setPage(page + 1)}
                className="rounded-lg border border-zinc-300 dark:border-zinc-700 px-3 py-1.5 disabled:opacity-40">Next →</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function SearchPageInner() {
  const sp = useSearchParams();
  const q = sp.get("q") ?? "";
  return <SearchInner key={q} initial={q} />;
}

export default function SearchPage() {
  return (
    <Suspense fallback={<ProductGridSkeleton />}>
      <SearchPageInner />
    </Suspense>
  );
}
