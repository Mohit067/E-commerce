"use client";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { inr } from "@/lib/format";
import { AdminShell, Bars } from "@/components/admin";
import { Card, ErrorState, Skeleton } from "@/components/ui";

export default function AdminAnalytics() {
  const q = useQuery({
    queryKey: ["analytics"],
    queryFn: () => apiFetch<{
      revenue: number; orders: number; customers: number; avg_order_value: number;
      revenue_series: { date: string; revenue: number; orders: number }[];
      top_products: { name: string; qty: number; revenue: number }[];
    }>("/analytics/overview", { auth: true }),
  });
  return (
    <AdminShell>
      <h1 className="text-xl font-bold">Analytics</h1>
      {q.isLoading ? <Skeleton className="mt-3 h-60" /> :
        q.isError ? <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} /> : (
        <>
          <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[["Revenue", inr(q.data!.revenue)], ["Orders", String(q.data!.orders)],
               ["Customers", String(q.data!.customers)], ["AOV", inr(q.data!.avg_order_value)]].map(([k, v]) => (
              <Card key={k} className="p-3"><p className="text-xs text-zinc-500">{k}</p><p className="text-xl font-bold">{v}</p></Card>
            ))}
          </div>
          <Card className="mt-3 p-4">
            <p className="text-sm font-medium">Revenue trend (14 days)</p>
            <Bars data={q.data!.revenue_series} />
          </Card>
          <Card className="mt-3 p-4">
            <p className="text-sm font-medium">Top products by revenue</p>
            <ul className="mt-2 space-y-1 text-sm">
              {q.data!.top_products.map((t) => (
                <li key={t.name} className="flex justify-between gap-2">
                  <span className="truncate">{t.name}</span>
                  <span className="text-zinc-500">{t.qty} × · {inr(t.revenue)}</span>
                </li>
              ))}
            </ul>
          </Card>
        </>
      )}
    </AdminShell>
  );
}
