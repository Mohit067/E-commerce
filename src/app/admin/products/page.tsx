"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { inr } from "@/lib/format";
import { AdminShell } from "@/components/admin";
import { Button, Card, ErrorState, Input, Skeleton } from "@/components/ui";
import type { PageRes, Product } from "@/types";

export default function AdminProducts() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const q = useQuery({
    queryKey: ["admin-products", page],
    queryFn: () => apiFetch<PageRes<Product>>(`/products?page=${page}&page_size=20`, ),
  });
  const del = useMutation({
    mutationFn: (id: string) => apiFetch(`/products/${id}`, { method: "DELETE", auth: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-products"] }),
  });
  const [form, setForm] = useState({ name: "", price: "", description: "" });
  const create = useMutation({
    mutationFn: () => apiFetch("/products", {
      method: "POST", auth: true,
      body: JSON.stringify({ name: form.name, price: Number(form.price), description: form.description }),
    }),
    onSuccess: () => {
      setForm({ name: "", price: "", description: "" });
      qc.invalidateQueries({ queryKey: ["admin-products"] });
    },
  });

  return (
    <AdminShell>
      <h1 className="text-xl font-bold">Products</h1>
      <Card className="mt-3 p-3">
        <p className="text-sm font-medium">Quick create</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="max-w-xs" />
          <Input placeholder="Price" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="w-28" />
          <Input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="max-w-xs" />
          <Button onClick={() => create.mutate()} disabled={create.isPending || !form.name || !form.price}>
            {create.isPending ? "Creating…" : "Create"}
          </Button>
        </div>
      </Card>
      <div className="mt-3">
        {q.isLoading ? <Skeleton className="h-60" /> :
          q.isError ? <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /> : (
          <>
            <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50 dark:bg-zinc-900 text-left text-xs text-zinc-500">
                  <tr><th className="p-2">Product</th><th className="p-2">Price</th><th className="p-2">★</th><th className="p-2">Stock</th><th className="p-2"></th></tr>
                </thead>
                <tbody>
                  {q.data!.items.map((p) => (
                    <tr key={p.id} className="border-t border-zinc-100 dark:border-zinc-800">
                      <td className="max-w-xs truncate p-2">{p.name}</td>
                      <td className="p-2">{inr(p.price)}</td>
                      <td className="p-2">{p.rating_avg.toFixed(1)}</td>
                      <td className="p-2">{p.stock}</td>
                      <td className="p-2"><button onClick={() => del.mutate(p.id)} className="text-xs text-red-500 hover:underline">Delete</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex items-center gap-3 text-sm">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="rounded-lg border px-3 py-1.5 disabled:opacity-40">← Prev</button>
              <span>Page {q.data!.page} of {q.data!.total_pages} ({q.data!.total})</span>
              <button disabled={page >= q.data!.total_pages} onClick={() => setPage(page + 1)} className="rounded-lg border px-3 py-1.5 disabled:opacity-40">Next →</button>
            </div>
          </>
        )}
      </div>
    </AdminShell>
  );
}
