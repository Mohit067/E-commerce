"use client";
import { Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { PageRes, Product } from "@/types";
import { ProductCard, ProductGridSkeleton } from "@/components/product";
import { Empty, ErrorState } from "@/components/ui";
import { DEFAULT_FILTERS, FilterBar, buildQuery, type Filters } from "@/components/filters";

function ProductsInner() {
  const sp = useSearchParams();
  const [f, setF] = useState<Filters>({
    ...DEFAULT_FILTERS,
    sort: sp.get("sort") ?? "popular",
    search: sp.get("q") ?? "",
  });
  const [page, setPage] = useState(1);

  const qs = buildQuery(f, page);
  const q = useQuery({
    queryKey: ["products", qs],
    queryFn: () => apiFetch<PageRes<Product>>(`/products?${qs}`),
  });

  return (
    <div className="py-6">
      <h1 className="text-xl font-bold">All products</h1>
      <p className="text-sm text-zinc-500">{q.data ? `${q.data.total.toLocaleString()} items` : "…"}</p>
      <div className="mt-3">
        <FilterBar f={f} set={(nf) => { setF(nf); setPage(1); }} />
      </div>
      <div className="mt-4">
        {q.isLoading ? <ProductGridSkeleton /> :
          q.isError ? <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /> :
          q.data!.items.length === 0 ? <Empty title="No products match" hint="Try widening price or clearing filters." /> : (
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

export default function ProductsPage() {
  return (
    <Suspense fallback={<ProductGridSkeleton />}>
      <ProductsInner />
    </Suspense>
  );
}
