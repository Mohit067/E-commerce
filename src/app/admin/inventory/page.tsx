"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { AdminShell } from "@/components/admin";
import { Badge, ErrorState, Skeleton } from "@/components/ui";

export default function AdminInventory() {
  const q = useQuery({
    queryKey: ["low-stock"],
    queryFn: () => apiFetch<{ product_id: string; product_name: string; variant_id: string | null; quantity: number }[]>("/inventory/low-stock", { auth: true }),
  });
  return (
    <AdminShell>
      <h1 className="text-xl font-bold">Inventory alerts</h1>
      <div className="mt-3">
        {q.isLoading ? <Skeleton className="h-40" /> :
          q.isError ? <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /> :
          q.data!.length === 0 ? <p className="text-sm text-zinc-500">No low-stock items. 🎉</p> : (
          <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 dark:bg-zinc-900 text-left text-xs text-zinc-500">
                <tr><th className="p-2">Product</th><th className="p-2">Qty</th><th className="p-2">State</th></tr>
              </thead>
              <tbody>
                {q.data!.map((r, i) => (
                  <tr key={i} className="border-t border-zinc-100 dark:border-zinc-800">
                    <td className="p-2">{r.product_name}</td>
                    <td className="p-2">{r.quantity}</td>
                    <td className="p-2"><Badge tone={r.quantity === 0 ? "red" : "amber"}>{r.quantity === 0 ? "Out of stock" : "Low"}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminShell>
  );
}
