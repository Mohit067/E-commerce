"use client";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { PageRes, Product } from "@/types";
import { ProductCard, ProductGridSkeleton } from "@/components/product";
import { Empty, ErrorState } from "@/components/ui";

export default function CategoryPage() {
  const { slug } = useParams<{ slug: string }>();
  const cat = useQuery({
    queryKey: ["cat", slug],
    queryFn: () => apiFetch<{ name: string; description: string }>(`/categories/${slug}`),
  });
  const prods = useQuery({
    queryKey: ["cat-prods", slug],
    queryFn: () => apiFetch<PageRes<Product>>(`/products?category=${slug}&page=1&page_size=24`),
  });
  return (
    <div className="py-6">
      <h1 className="text-xl font-bold">{cat.data?.name ?? slug}</h1>
      {cat.data?.description && <p className="text-sm text-zinc-500">{cat.data.description}</p>}
      <div className="mt-4">
        {prods.isLoading ? <ProductGridSkeleton /> :
          prods.isError ? <ErrorState message="Could not load products." onRetry={() => prods.refetch()} /> :
          prods.data!.items.length === 0 ? <Empty title="Nothing here yet" /> : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {prods.data!.items.map((p) => <ProductCard key={p.id} p={p} />)}
          </div>
        )}
      </div>
    </div>
  );
}
