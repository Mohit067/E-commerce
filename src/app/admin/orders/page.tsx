"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { inr } from "@/lib/format";
import { AdminShell } from "@/components/admin";
import { Badge, ErrorState, Skeleton } from "@/components/ui";
import type { Order } from "@/types";

const STATUSES = ["pending", "confirmed", "processing", "shipped", "out_for_delivery", "delivered", "cancelled", "returned", "refunded"];

export default function AdminOrders() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const q = useQuery({
    queryKey: ["admin-orders", page],
    queryFn: () => apiFetch<{ items: Order[]; total: number; total_pages: number }>(`/admin/orders?page=${page}&page_size=20`, { auth: true }),
  });
  const upd = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/admin/orders/${id}`, { method: "PATCH", auth: true, body: JSON.stringify({ status }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-orders"] }),
  });

  return (
    <AdminShell>
      <h1 className="text-xl font-bold">Orders</h1>
      <div className="mt-3">
        {q.isLoading ? <Skeleton className="h-60" /> :
          q.isError ? <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /> : (
          <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 dark:bg-zinc-900 text-left text-xs text-zinc-500">
                <tr><th className="p-2">Order</th><th className="p-2">Total</th><th className="p-2">Status</th><th className="p-2">Set status</th></tr>
              </thead>
              <tbody>
                {q.data!.items.map((o) => (
                  <tr key={o.id} className="border-t border-zinc-100 dark:border-zinc-800">
                    <td className="p-2 font-medium">{o.order_number}</td>
                    <td className="p-2">{inr(o.total)}</td>
                    <td className="p-2"><Badge>{o.status}</Badge></td>
                    <td className="p-2">
                      <select
                        defaultValue={o.status}
                        onChange={(e) => upd.mutate({ id: o.id, status: e.target.value })}
                        className="rounded-lg border border-zinc-300 dark:border-zinc-700 bg-transparent px-2 py-1 text-xs">
                        {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="mt-3 flex items-center gap-3 text-sm">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="rounded-lg border px-3 py-1.5 disabled:opacity-40">← Prev</button>
          <button onClick={() => setPage(page + 1)} className="rounded-lg border px-3 py-1.5">Next →</button>
        </div>
        {upd.isError && <p className="mt-1 text-xs text-red-500">{(upd.error as Error).message}</p>}
      </div>
    </AdminShell>
  );
}
